"""football-data.org 어댑터 — 일정/단계/조편성/스코어 (안정적 기반).

무료 티어: 10 req/분. 인증은 X-Auth-Token 헤더.
"""

from __future__ import annotations

from typing import Any

import requests

from ..config import FOOTBALL_DATA_BASE, FOOTBALL_DATA_COMPETITION, settings


def _headers() -> dict[str, str]:
    if not settings.football_data_token:
        raise RuntimeError(
            "FOOTBALL_DATA_TOKEN 미설정. football-data.org에서 무료 키를 발급받아 "
            "환경변수로 넣어주세요."
        )
    return {"X-Auth-Token": settings.football_data_token}


def fetch_matches() -> list[dict[str, Any]]:
    """월드컵 전체 경기를 정규화해 반환한다."""
    url = f"{FOOTBALL_DATA_BASE}/competitions/{FOOTBALL_DATA_COMPETITION}/matches"
    resp = requests.get(url, headers=_headers(), timeout=settings.request_timeout)
    resp.raise_for_status()
    payload = resp.json()
    return [_normalize(m) for m in payload.get("matches", [])]


def _normalize(m: dict[str, Any]) -> dict[str, Any]:
    home = m.get("homeTeam") or {}
    away = m.get("awayTeam") or {}
    score = (m.get("score") or {}).get("fullTime") or {}
    return {
        "match_id": m["id"],
        "utc_kickoff": m["utcDate"],          # ISO8601 UTC, 예: 2026-06-11T19:00:00Z
        "stage": m.get("stage"),              # GROUP_STAGE / LAST_16 / ... / FINAL
        "group_name": m.get("group"),         # GROUP_A 등 (녹아웃은 None)
        "status": m.get("status"),            # SCHEDULED / IN_PLAY / FINISHED ...
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "home_score": score.get("home"),
        "away_score": score.get("away"),
    }
