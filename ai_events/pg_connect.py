from __future__ import annotations

import psycopg
from psycopg import Connection

from ai_events.webapp.settings import database_url, load_env, sslmode_for_dsn


def connect_psycopg(dsn: str | None = None) -> Connection:
    """Sync Postgres connection (scraper, export, schema apply). Pass ``dsn`` for tests only."""
    load_env()
    resolved = (dsn or "").strip() or (database_url() or "").strip()
    if not resolved:
        raise SystemExit("DATABASE_URL is not set. Copy .env.example to .env.")
    return psycopg.connect(resolved, sslmode=sslmode_for_dsn(resolved))
