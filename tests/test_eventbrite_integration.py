"""Eventbrite: discover dedupes URLs; run keeps only London in-person AI rows."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import httpx
from psycopg import Connection

from ai_events.sources import eventbrite as eb
from ai_events.storage import iter_events_rows
from tests.fixtures_html import (
    EVENT_PAGE_EB_MANCHESTER_OFFLINE_AI,
    EVENT_PAGE_LONDON_OFFLINE_AI,
    listing_eventbrite_two_urls,
)


def _transport_eventbrite_listing_and_details() -> httpx.MockTransport:
    listing_url = "https://www.eventbrite.com/d/test-only/london/"

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if u.startswith(listing_url.rstrip("/")) or u.startswith(listing_url):
            if "page=" in u and u != listing_url and "page=1" not in u:
                return httpx.Response(200, text="<html></html>")
            return httpx.Response(200, text=listing_eventbrite_two_urls())
        if "tickets-111" in u:
            return httpx.Response(200, text=EVENT_PAGE_LONDON_OFFLINE_AI)
        if "tickets-222" in u:
            return httpx.Response(200, text=EVENT_PAGE_EB_MANCHESTER_OFFLINE_AI)
        return httpx.Response(404, text=f"unexpected {u}")

    return httpx.MockTransport(handler)


def test_discover_returns_two_unique_normalized_urls() -> None:
    transport = _transport_eventbrite_listing_and_details()
    with httpx.Client(transport=transport) as client, patch.object(
        eb, "LISTINGS", ["https://www.eventbrite.com/d/test-only/london/"]
    ):
        urls = eb.discover_event_urls(client, max_pages=2)
    assert len(urls) == 2
    assert any("111" in u for u in urls)
    assert any("222" in u for u in urls)


def test_run_eventbrite_keeps_only_london_row(pg_conn: Connection) -> None:
    transport = _transport_eventbrite_listing_and_details()
    with httpx.Client(transport=transport) as client, patch.object(
        eb, "LISTINGS", ["https://www.eventbrite.com/d/test-only/london/"]
    ):
        fetched, kept = eb.run_eventbrite(client, pg_conn)
    assert fetched == 2
    assert kept == 1
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 1
    assert rows[0]["source"] == "eventbrite"
    assert "London" in (rows[0]["venue"] or "") or rows[0]["city"] == "London"
    assert datetime.fromisoformat(rows[0]["starts_at"]) == datetime.fromisoformat(
        "2026-06-01T09:00:00+01:00"
    )
    assert datetime.fromisoformat(rows[0]["ends_at"]) == datetime.fromisoformat(
        "2026-06-01T17:00:00+01:00"
    )
