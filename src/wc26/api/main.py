"""FastAPI 서빙 — GET /api/tonight + 정적 프론트."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import KST
from ..db import get_conn

app = FastAPI(title="wc26-alarm", version="0.1.0")

_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/tonight")
def tonight(hours: int = Query(24, ge=1, le=168)) -> dict:
    """지금(KST)부터 향후 `hours`시간 내 경기를 점수순으로 반환."""
    now = datetime.now(tz=KST)
    until = now + timedelta(hours=hours)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT match_id, kst_kickoff, stage, group_name, status,
                   home_team, away_team, home_score, away_score, score, label
            FROM tonight_view
            WHERE utc_kickoff >= %s AND utc_kickoff < %s
            ORDER BY COALESCE(score, 0) DESC, utc_kickoff ASC
            """,
            (now, until),
        )
        rows = cur.fetchall()
    return {"from": now.isoformat(), "until": until.isoformat(), "matches": rows}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


# 정적 자산
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
