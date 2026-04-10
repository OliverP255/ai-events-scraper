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


def database_ssl() -> bool:
    """asyncpg ssl=True for Neon / remote; false for local Docker."""
    raw = os.environ.get("DATABASE_SSL", "").strip().lower()
    if raw in ("1", "true", "yes", "require"):
        return True
    if raw in ("0", "false", "no"):
        return False
    url = database_url() or ""
    if "localhost" in url or "127.0.0.1" in url:
        return False
    return True
