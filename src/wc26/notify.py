"""킥오프 전 알림 — 곧 시작하는 고득점 경기를 웹훅으로 통지.

WEBHOOK_URL(Slack/Discord 호환)이 설정돼 있을 때만 동작하며, 미설정이면 no-op.
`notifications` 테이블로 멱등성을 보장해 같은 경기를 두 번 알리지 않는다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests

from .config import KST, settings
from .db import get_conn

log = logging.getLogger(__name__)


def _format_message(m: dict) -> str:
    kst = m["kst_kickoff"].strftime("%H:%M")
    return (
        f"⏰ {kst} KST · {m['home_team']} vs {m['away_team']}\n"
        f"{m['label']} (점수 {m['score']})"
    )


def _send(message: str) -> bool:
    """웹훅으로 전송. Slack(text)·Discord(content) 양쪽 키를 함께 보낸다."""
    try:
        resp = requests.post(
            settings.webhook_url,
            json={"text": message, "content": message},
            timeout=settings.request_timeout,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("웹훅 전송 실패: %s", exc)
        return False


def notify_upcoming(lead_minutes: int = 60, min_score: int = 80) -> int:
    """앞으로 `lead_minutes`분 내 시작하고 점수 >= `min_score`인 미통지 경기를 알린다."""
    if not settings.webhook_url:
        log.info("notify: WEBHOOK_URL 미설정 — 건너뜀")
        return 0

    now = datetime.now(tz=KST)
    until = now + timedelta(minutes=lead_minutes)
    sent = 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT v.match_id, v.kst_kickoff, v.home_team, v.away_team, v.score, v.label
            FROM tonight_view v
            LEFT JOIN notifications n USING (match_id)
            WHERE n.match_id IS NULL
              AND v.score >= %s
              AND v.utc_kickoff >= %s AND v.utc_kickoff < %s
            ORDER BY v.utc_kickoff
            """,
            (min_score, now, until),
        )
        for m in cur.fetchall():
            if _send(_format_message(m)):
                cur.execute(
                    "INSERT INTO notifications (match_id) VALUES (%s) "
                    "ON CONFLICT (match_id) DO NOTHING",
                    (m["match_id"],),
                )
                sent += 1

    log.info("notify: %d경기 알림 전송 (lead=%d분, min_score=%d)", sent, lead_minutes, min_score)
    return sent
