from __future__ import annotations

import pytest

from ai_events.webapp.settings import database_url, load_env


@pytest.fixture
def pg_conn():
    """Postgres connection; requires DATABASE_URL and applied schema. Truncates `events` around each test."""
    load_env()
    if not database_url():
        pytest.skip("DATABASE_URL not set — Postgres required for storage integration tests")

    from ai_events.pg_connect import connect_psycopg

    conn = connect_psycopg()
    try:
        conn.execute("TRUNCATE events")
        conn.commit()
        yield conn
    finally:
        conn.execute("TRUNCATE events")
        conn.commit()
        conn.close()
