"""Airflow DAG: ingest → transform → enrich → publish.

wc26 패키지의 파이프라인 단계를 PythonOperator로 호출한다.
패키지는 이미지에 설치되거나 PYTHONPATH(/opt/wc26/src)로 노출되어 있어야 한다.
"""

from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.decorators import dag, task


@dag(
    schedule="0 * * * *",  # 매시간 (대회 기간엔 충분; 라이브 갱신 필요시 단축)
    start_date=pendulum.datetime(2026, 6, 1, tz="Asia/Seoul"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["wc26"],
)
def wc26_pipeline():
    @task
    def ingest() -> int:
        from wc26.pipeline import ingest_football_data

        return ingest_football_data()

    @task
    def transform(_ingested: int) -> int:
        from wc26.pipeline import transform_scores

        return transform_scores()

    @task
    def enrich(_scored: int) -> int:
        from wc26.pipeline import enrich_metrics

        return enrich_metrics()

    @task
    def publish_step(_enriched: int) -> int:
        from wc26.pipeline import publish

        return publish()

    publish_step(enrich(transform(ingest())))


wc26_pipeline()
