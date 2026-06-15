"""FotMob 비공식 어댑터 — xG 등 상세 지표 보강용.

⚠️ 공식 지원 API가 아니다. 엔드포인트가 예고 없이 바뀌거나 차단될 수 있으므로
실패해도 핵심 파이프라인이 죽지 않도록 항상 graceful하게 None을 반환한다.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ..config import FOTMOB_BASE, settings

log = logging.getLogger(__name__)


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
    try:
        # FotMob 구조는 자주 바뀌므로 키가 없으면 조용히 None.
        for group in stats.get("Periods", {}).get("All", {}).get("stats", []):
            for item in group.get("stats", []):
                if item.get("title", "").lower() in {"expected goals (xg)", "xg"}:
                    return float(item["stats"][side])
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return None
