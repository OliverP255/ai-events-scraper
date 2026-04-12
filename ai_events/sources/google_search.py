"""Discover event pages via HTML search (Google + DuckDuckGo fallback); no API keys."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from psycopg import Connection

from ai_events.sources.search_discovery import preview_search_discovered, run_search_discovered


def _year() -> int:
    return datetime.now().year


def _queries() -> list[str]:
    y = _year()
    return [
        f"London enterprise AI summit in-person {y}",
        f"London generative AI conference B2B {y}",
        f"UK corporate AI roundtable London executives {y}",
        f"London AI leadership summit founders investors {y}",
        f"Canary Wharf AI event enterprise {y}",
    ]


def run_google_search(client: httpx.Client, conn: Connection) -> tuple[int, int]:
    return run_search_discovered(
        client,
        conn,
        source="google_search",
        queries=_queries(),
    )


def preview_google_search(
    client: httpx.Client,
    *,
    max_urls_per_query: int = 14,
    max_fetch_total: int = 72,
    search_pause_s: float = 1.2,
) -> dict[str, Any]:
    """Dry-run google_search discovery (no database writes)."""
    return preview_search_discovered(
        client,
        source="google_search",
        queries=_queries(),
        max_urls_per_query=max_urls_per_query,
        max_fetch_total=max_fetch_total,
        search_pause_s=search_pause_s,
    )
