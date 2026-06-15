"""FotMob 비공식 어댑터 — xG 등 상세 지표 보강용.

⚠️ 공식 지원 API가 아니다. 엔드포인트가 예고 없이 바뀌거나 차단될 수 있으므로
실패해도 핵심 파이프라인이 죽지 않도록 항상 graceful하게 None을 반환한다.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

import requests

from ..config import FOTMOB_BASE, settings

log = logging.getLogger(__name__)

# football-data.org 와 FotMob 의 팀명 표기 차이를 흡수하는 별칭 맵.
# 키/값 모두 normalize_team 을 거친 형태로 비교한다.
_TEAM_ALIASES = {
    "korea republic": "south korea",
    "ir iran": "iran",
    "republic of ireland": "ireland",
    "usa": "united states",
    "united states of america": "united states",
    "cote d ivoire": "ivory coast",
}


def normalize_team(name: str | None) -> str:
    """비교용 정규화: 발음기호 제거, 소문자, 구두점 제거, 공백 단일화, 별칭 적용."""
    if not name:
        return ""
    # 발음기호 분리 후 결합문자 제거 (Côte -> Cote)
    folded = "".join(
        ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch)
    )
    cleaned = re.sub(r"[^a-z0-9 ]", " ", folded.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _TEAM_ALIASES.get(cleaned, cleaned)


def select_match_id(
    candidates: list[dict[str, Any]], home: str | None, away: str | None
) -> int | None:
    """후보 경기 목록에서 home/away 팀이 일치하는 FotMob 경기 id를 찾는다.

    홈/원정 순서가 뒤바뀐 경우도 매칭한다(데이터 소스마다 기준이 다를 수 있음).
    candidates: [{"id": int, "home": str, "away": str}, ...]
    """
    want = {normalize_team(home), normalize_team(away)}
    if "" in want:
        return None
    for c in candidates:
        got = {normalize_team(c.get("home")), normalize_team(c.get("away"))}
        if got == want:
            return c.get("id")
    return None


def fetch_match_candidates(yyyymmdd: str) -> list[dict[str, Any]]:
    """특정 날짜의 경기 목록(id/home/away)을 best-effort로 가져온다. 실패 시 빈 리스트."""
    try:
        resp = requests.get(
            f"{FOTMOB_BASE}/matches",
            params={"date": yyyymmdd},
            timeout=settings.request_timeout,
            headers={"User-Agent": "wc26-alarm/0.1 (personal project)"},
        )
        resp.raise_for_status()
        return _extract_candidates(resp.json())
    except Exception as exc:  # noqa: BLE001 — 보강용이므로 모든 예외를 흡수
        log.warning("FotMob 후보 조회 실패 (date=%s): %s", yyyymmdd, exc)
        return []


def _extract_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """matches-by-date 응답에서 (id, home, away)만 평탄화. 구조 변경에 방어적."""
    out: list[dict[str, Any]] = []
    for league in payload.get("leagues", []) or []:
        for m in league.get("matches", []) or []:
            try:
                out.append(
                    {
                        "id": m["id"],
                        "home": (m.get("home") or {}).get("name"),
                        "away": (m.get("away") or {}).get("name"),
                    }
                )
            except (KeyError, TypeError):
                continue
    return out


def fetch_match_detail(fotmob_match_id: int) -> dict[str, Any] | None:
    """경기 상세(xG 등)를 best-effort로 가져온다. 실패 시 None."""
    url = f"{FOTMOB_BASE}/matchDetails"
    try:
        resp = requests.get(
            url,
            params={"matchId": fotmob_match_id},
            timeout=settings.request_timeout,
            headers={"User-Agent": "wc26-alarm/0.1 (personal project)"},
        )
        resp.raise_for_status()
        return _extract_metrics(resp.json())
    except Exception as exc:  # noqa: BLE001 — 보강용이므로 모든 예외를 흡수
        log.warning("FotMob 보강 실패 (match=%s): %s", fotmob_match_id, exc)
        return None


def _extract_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """관심 지표만 추출. FotMob 응답 구조 변경에 대비해 방어적으로 접근."""
    content = payload.get("content") or {}
    stats = content.get("stats") or {}
    return {
        "home_xg": _safe_xg(stats, 0),
        "away_xg": _safe_xg(stats, 1),
    }


def _safe_xg(stats: dict[str, Any], side: int) -> float | None:
    """content.stats.Periods.All.stats[].stats[] 에서 xG 값을 찾는다.

    xG 항목 형태: {"key": "expected_goals", "type": "text", "stats": ["1.05", "1.05"]}.
    같은 key로 type=="title"(값 [null, null])인 항목도 섞여 있으므로 스칼라 값만 받는다.
    """
    try:
        for group in stats.get("Periods", {}).get("All", {}).get("stats", []):
            for item in group.get("stats", []):
                if not isinstance(item, dict) or item.get("key") != "expected_goals":
                    continue
                value = item.get("stats", [])[side]
                if isinstance(value, (str, int, float)):
                    return float(value)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return None
