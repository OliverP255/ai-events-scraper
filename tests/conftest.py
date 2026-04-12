from __future__ import annotations

import pytest

from ai_events.webapp.settings import database_url, load_env, test_database_url


@pytest.fixture
def pg_conn():
    """
    Postgres for integration tests only. Uses ``TEST_DATABASE_URL`` (never ``DATABASE_URL``).

    Truncates ``events`` around each test — must point at a dedicated database or Neon branch.
    """
    load_env()
    test_dsn = test_database_url()
    if not test_dsn:
        pytest.skip(
            "Set TEST_DATABASE_URL in .env to a dedicated Postgres (Neon branch or local DB). "
            "Integration tests run TRUNCATE events — do not use production DATABASE_URL."
        )
    prod = database_url()
    if prod and test_dsn.strip() == prod.strip():
        pytest.fail(
            "TEST_DATABASE_URL must differ from DATABASE_URL. "
            "Create a separate Neon branch or database for tests."
        )

    from ai_events.pg_connect import connect_psycopg

    conn = connect_psycopg(dsn=test_dsn)
    try:
        conn.execute("TRUNCATE events")
        conn.commit()
        yield conn
    finally:
        conn.execute("TRUNCATE events")
        conn.commit()
        conn.close()
