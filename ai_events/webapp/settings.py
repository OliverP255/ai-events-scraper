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


def semantic_search_enabled() -> bool:
    """
    When true (default), ``/api/events?q=`` uses vector similarity if rows have ``embedding``
    and the embed API works; otherwise falls back to Postgres full-text search.
    Set ``SEMANTIC_SEARCH=0`` to always use full-text search.
    """
    load_env()
    raw = os.environ.get("SEMANTIC_SEARCH", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def embeddings_base_url() -> str:
    """Ollama host, e.g. ``http://127.0.0.1:11434`` (no path)."""
    load_env()
    return (os.environ.get("EMBEDDING_OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")


def embeddings_api_url() -> str:
    return f"{embeddings_base_url()}/api/embeddings"


def embedding_model() -> str:
    load_env()
    return (os.environ.get("EMBEDDING_MODEL") or "nomic-embed-text").strip()


def embedding_dimensions() -> int:
    load_env()
    try:
        return int(os.environ.get("EMBEDDING_DIM", "768"))
    except ValueError:
        return 768


def embedding_http_timeout_s() -> float:
    load_env()
    try:
        return float(os.environ.get("EMBEDDING_HTTP_TIMEOUT", "90"))
    except ValueError:
        return 90.0


def serper_api_key() -> str | None:
    """Serper API key for google_search source (serper.dev)."""
    load_env()
    return os.environ.get("SERPER_API_KEY", "").strip() or None
