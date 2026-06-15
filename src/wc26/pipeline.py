"""파이프라인 단계: ingest → transform → publish.

Airflow DAG와 K8s Job이 공통으로 호출하는 진입점.
각 함수는 독립 실행 가능하며 DB를 통해 상태를 주고받는다.
"""

from __future__ import annotations

import logging

from .db import get_conn
from .sources import fotmob, football_data
from .transform.score import score_match

log = logging.getLogger(__name__)

# xG가 의미 있는 상태(시작했거나 끝난 경기)만 보강 대상으로 삼는다.
_ENRICHABLE_STATUSES = ("IN_PLAY", "PAUSED", "FINISHED")


def ingest_football_data() -> int:
    """football-data.org에서 경기를 받아 raw_matches에 upsert."""
    matches = football_data.fetch_matches()
    with get_conn() as conn, conn.cursor() as cur:
        for m in matches:
            cur.execute(
                """
                INSERT INTO raw_matches (
                    match_id, utc_kickoff, stage, group_name, status,
                    home_team, away_team, home_score, away_score
                ) VALUES (
                    %(match_id)s, %(utc_kickoff)s, %(stage)s, %(group_name)s, %(status)s,
                    %(home_team)s, %(away_team)s, %(home_score)s, %(away_score)s
                )
                ON CONFLICT (match_id) DO UPDATE SET
                    utc_kickoff = EXCLUDED.utc_kickoff,
                    stage       = EXCLUDED.stage,
                    group_name  = EXCLUDED.group_name,
                    status      = EXCLUDED.status,
                    home_team   = EXCLUDED.home_team,
                    away_team   = EXCLUDED.away_team,
                    home_score  = EXCLUDED.home_score,
                    away_score  = EXCLUDED.away_score
                """,
                m,
            )
    log.info("ingest_football_data: %d경기 upsert", len(matches))
    return len(matches)


def transform_scores() -> int:
    """raw_matches를 읽어 점수를 계산하고 scored_matches에 저장."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.match_id, r.home_team, r.away_team, r.stage,
                   m.home_xg, m.away_xg
            FROM raw_matches r
            LEFT JOIN match_metrics m USING (match_id)
            """
        )
        rows = cur.fetchall()
        for r in rows:
            sm = score_match(
                r["home_team"], r["away_team"], r["stage"], r["home_xg"], r["away_xg"]
            )
            cur.execute(
                """
                INSERT INTO scored_matches (match_id, score, label, computed_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (match_id) DO UPDATE SET
                    score = EXCLUDED.score,
                    label = EXCLUDED.label,
                    computed_at = EXCLUDED.computed_at
                """,
                (r["match_id"], sm.score, sm.label),
            )
    log.info("transform_scores: %d경기 채점", len(rows))
    return len(rows)


def enrich_metrics() -> int:
    """진행/종료된 경기를 FotMob과 매칭해 xG를 match_metrics에 적재.

    FotMob은 비공식이라 실패해도 핵심 파이프라인이 멈추지 않도록 경기별로 흡수한다.
    날짜별로 후보 목록을 한 번만 받아 호출 수를 줄인다.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT match_id, utc_kickoff, home_team, away_team
            FROM raw_matches
            WHERE status = ANY(%s)
            ORDER BY utc_kickoff
            """,
            (list(_ENRICHABLE_STATUSES),),
        )
        rows = cur.fetchall()

        candidates_by_date: dict[str, list] = {}
        enriched = 0
        for r in rows:
            day_key = r["utc_kickoff"].strftime("%Y%m%d")
            if day_key not in candidates_by_date:
                candidates_by_date[day_key] = fotmob.fetch_match_candidates(day_key)

            fm_id = fotmob.select_match_id(
                candidates_by_date[day_key], r["home_team"], r["away_team"]
            )
            if fm_id is None:
                continue
            metrics = fotmob.fetch_match_detail(fm_id)
            if not metrics or (metrics["home_xg"] is None and metrics["away_xg"] is None):
                continue

            cur.execute(
                """
                INSERT INTO match_metrics (match_id, home_xg, away_xg, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (match_id) DO UPDATE SET
                    home_xg = EXCLUDED.home_xg,
                    away_xg = EXCLUDED.away_xg,
                    updated_at = EXCLUDED.updated_at
                """,
                (r["match_id"], metrics["home_xg"], metrics["away_xg"]),
            )
            enriched += 1

    log.info("enrich_metrics: %d/%d경기 xG 보강", enriched, len(rows))
    return enriched


def publish() -> int:
    """serving용 뷰를 리프레시. (현재는 일반 뷰라 no-op이지만 머티리얼라이즈드 뷰 전환 대비.)"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM tonight_view")
        n = cur.fetchone()["n"]
    log.info("publish: tonight_view %d행", n)
    return n
