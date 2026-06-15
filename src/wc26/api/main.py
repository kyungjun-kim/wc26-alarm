"""FastAPI 서빙 — 경기 조회 API + 정적 프론트."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import KST
from ..db import get_conn

app = FastAPI(title="wc26-alarm", version="0.1.0")

_STATIC_DIR = Path(__file__).parent / "static"

# 모든 경기 조회가 공유하는 컬럼 + 정렬 (점수 높은 순, 동점이면 킥오프 빠른 순)
_SELECT_COLS = """
    match_id, kst_kickoff, stage, group_name, status,
    home_team, away_team, home_score, away_score, score, label,
    home_xg, away_xg
"""
_ORDER_BY = "ORDER BY COALESCE(score, 0) DESC, utc_kickoff ASC"


@app.get("/api/tonight")
def tonight(
    hours: int = Query(24, ge=1, le=168),
    min_score: int = Query(0, ge=0, le=100),
) -> dict:
    """지금(KST)부터 향후 `hours`시간 내 경기를 점수순으로 반환.

    `min_score` 로 추천도 하한을 걸어 볼 만한 경기만 추릴 수 있다.
    """
    now = datetime.now(tz=KST)
    until = now + timedelta(hours=hours)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM tonight_view
            WHERE utc_kickoff >= %s AND utc_kickoff < %s
              AND COALESCE(score, 0) >= %s
            {_ORDER_BY}
            """,
            (now, until, min_score),
        )
        rows = cur.fetchall()
    return {
        "from": now.isoformat(),
        "until": until.isoformat(),
        "min_score": min_score,
        "matches": rows,
    }


@app.get("/api/day/{kst_date}")
def day(kst_date: date, min_score: int = Query(0, ge=0, le=100)) -> dict:
    """특정 KST 날짜(YYYY-MM-DD)의 모든 경기를 점수순으로 반환."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM tonight_view
            WHERE kst_kickoff::date = %s
              AND COALESCE(score, 0) >= %s
            {_ORDER_BY}
            """,
            (kst_date, min_score),
        )
        rows = cur.fetchall()
    return {"date": kst_date.isoformat(), "min_score": min_score, "matches": rows}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


# 정적 자산
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
