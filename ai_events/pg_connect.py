from __future__ import annotations

import psycopg
from psycopg import Connection

from ai_events.webapp.settings import database_ssl, database_url, load_env


def connect_psycopg() -> Connection:
    """Sync Postgres connection (scraper, export, schema apply)."""
    load_env()
    dsn = database_url()
    if not dsn:
        raise SystemExit("DATABASE_URL is not set. Copy .env.example to .env.")
    ssl_on = database_ssl()
    return psycopg.connect(dsn, sslmode="require" if ssl_on else "disable")
