"""PostgreSQL 연결 헬퍼. psycopg(3) 사용."""

from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import settings


@contextmanager
def get_conn():
    """자동 커밋/롤백되는 연결 컨텍스트."""
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
