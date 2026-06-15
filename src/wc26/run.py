"""CLI 진입점: 파이프라인 단계를 커맨드라인/Job에서 실행.

사용:
    python -m wc26.run initdb       # 스키마 적용
    python -m wc26.run ingest
    python -m wc26.run transform
    python -m wc26.run enrich        # FotMob xG 보강 (선택, 비공식)
    python -m wc26.run publish
    python -m wc26.run all          # ingest -> enrich -> transform -> publish
    python -m wc26.run notify --lead-minutes 60 --min-score 80  # 킥오프 전 알림
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .db import get_conn
from .notify import notify_upcoming
from .pipeline import enrich_metrics, ingest_football_data, publish, transform_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_SCHEMA = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def initdb() -> None:
    sql = _SCHEMA.read_text(encoding="utf-8")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
    logging.info("initdb: 스키마 적용 완료")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wc26.run")
    parser.add_argument(
        "step",
        choices=["initdb", "ingest", "transform", "enrich", "publish", "notify", "all"],
    )
    parser.add_argument("--lead-minutes", type=int, default=60, help="notify: 킥오프 N분 전")
    parser.add_argument("--min-score", type=int, default=80, help="notify: 알림 점수 하한")
    args = parser.parse_args(argv)

    steps = {
        "initdb": initdb,
        "ingest": ingest_football_data,
        "transform": transform_scores,
        "enrich": enrich_metrics,
        "publish": publish,
    }
    if args.step == "all":
        ingest_football_data()
        enrich_metrics()
        transform_scores()
        publish()
    elif args.step == "notify":
        notify_upcoming(lead_minutes=args.lead_minutes, min_score=args.min_score)
    else:
        steps[args.step]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
