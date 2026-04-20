"""Discover event pages via Serper API (Google Search results)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from psycopg import Connection

from ai_events.sources.serper_search import preview_serper, run_serper


def _year() -> int:
    return datetime.now().year


def _queries() -> list[str]:
    y = _year()
    y1 = y + 1
    return [
        f"London enterprise AI summit in-person {y}",
        f"London generative AI conference B2B {y}",
        f"UK corporate AI roundtable London executives {y}",
        f"London AI leadership summit founders investors {y}",
        f"Canary Wharf AI event enterprise {y}",
        f"City of London AI forum CIO {y}",
        f"London AI expo trade show business {y}",
        f"UK AI regulation governance conference London {y}",
        f"London MLOps enterprise workshop {y}",
        f"Shoreditch AI startup founder event {y}",
        f"London agentic AI summit enterprise {y}",
        f"UK financial services AI conference London {y}",
        f"London RAG LLM enterprise meetup {y}",
        f"Westminster AI policy business briefing {y}",
        f"London AI transformation executive dinner {y}",
        f"UK retail AI innovation London {y}",
        f"London data AI leaders breakfast {y}",
        f"Thames Valley enterprise AI event {y}",
        f"London AI security risk executives {y}",
        f"UK healthcare AI conference London {y}",
        f"London AI product leadership summit {y}",
        f"Docklands tech AI networking executives {y}",
        f"London AI ethics responsible enterprise {y}",
        f"UK legal AI in-house counsel London {y}",
        f"London scale-up AI fundraising founders {y}",
        f"enterprise AI summit London {y1}",
        f"London generative AI conference {y1} tickets",
        f"UK AI week London business {y}",
    ]


def run_google_search(client: httpx.Client, conn: Connection) -> tuple[int, int]:
    return run_serper(
        client,
        conn,
        source="google_search",
        queries=_queries(),
        max_urls_per_query=10,
        max_fetch_total=100,
    )


def preview_google_search(
    client: httpx.Client,
    *,
    max_urls_per_query: int = 10,
    max_fetch_total: int = 100,
) -> dict[str, Any]:
    """Dry-run google_search discovery via Serper API (no database writes)."""
    return preview_serper(
        client,
        source="google_search",
        queries=_queries(),
        max_urls_per_query=max_urls_per_query,
        max_fetch_total=max_fetch_total,
    )