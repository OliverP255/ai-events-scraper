from __future__ import annotations

import os
from pathlib import Path

# Project root (parent of package `ai_events`).
ROOT = Path(__file__).resolve().parent.parent.parent


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")


def database_url() -> str | None:
    u = os.environ.get("DATABASE_URL", "").strip()
    return u or None


def test_database_url() -> str | None:
    """Postgres URL used only by pytest integration tests (``TRUNCATE events``). Keep separate from production."""
    u = os.environ.get("TEST_DATABASE_URL", "").strip()
    return u or None


def sslmode_for_dsn(dsn: str) -> str:
    """``require`` for Neon/remote, ``disable`` for local Docker; respects ``DATABASE_SSL`` override."""
    raw = os.environ.get("DATABASE_SSL", "").strip().lower()
    if raw in ("1", "true", "yes", "require"):
        return "require"
    if raw in ("0", "false", "no"):
        return "disable"
    if "localhost" in dsn or "127.0.0.1" in dsn:
        return "disable"
    return "require"


def database_ssl() -> bool:
    """asyncpg ssl=True for Neon / remote; false for local Docker."""
    u = database_url() or ""
    return sslmode_for_dsn(u) == "require"
