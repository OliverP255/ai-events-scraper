"""techUK: calendar links discovered; London AI event stored."""

from __future__ import annotations

from unittest.mock import patch

import httpx
from psycopg import Connection

from ai_events.sources import techuk as tu
from ai_events.storage import iter_events_rows
from tests.fixtures_html import EVENT_PAGE_TECHUK_LONDON, techuk_calendar_two_links


def _transport_techuk() -> httpx.MockTransport:
    cal = "https://www.techuk.org/what-we-deliver/events.html"
    one = "https://www.techuk.org/what-we-deliver/events/one.html"
    two = "https://www.techuk.org/what-we-deliver/flagship-and-sponsored-events/two.html"

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if u == cal:
            return httpx.Response(200, text=techuk_calendar_two_links())
        if u == one:
            return httpx.Response(200, text=EVENT_PAGE_TECHUK_LONDON)
        if u == two:
            # Same country but not London — must not pass passes_london
            return httpx.Response(
                200,
                text="""
                <html><head><script type="application/ld+json">
                {"@context":"https://schema.org","@type":"Event","name":"Fibre trade show",
                "description":"Cabling and ducts.",
                "startDate":"2026-09-01T09:00:00","endDate":"2026-09-02T17:00:00",
                "location":{"@type":"Place","name":"Manchester Central",
                "address":{"@type":"PostalAddress","addressLocality":"Manchester"}}}
                </script></head><body></body></html>
                """,
            )
        return httpx.Response(404, text=u)

    return httpx.MockTransport(handler)


def test_discover_two_event_links() -> None:
    transport = _transport_techuk()
    with httpx.Client(transport=transport) as client, patch.object(
        tu, "CALENDAR_URL", "https://www.techuk.org/what-we-deliver/events.html"
    ):
        urls = tu.discover_event_urls(client)
    assert len(urls) == 2


def test_run_techuk_keeps_only_london_event(pg_conn: Connection) -> None:
    transport = _transport_techuk()
    with httpx.Client(transport=transport) as client, patch.object(
        tu, "CALENDAR_URL", "https://www.techuk.org/what-we-deliver/events.html"
    ):
        fetched, kept = tu.run_techuk(client, pg_conn)
    assert fetched == 2
    assert kept == 1
    rows = list(iter_events_rows(pg_conn))
    assert rows[0]["title"].startswith("Enterprise AI Assurance")
    assert rows[0]["starts_at"].startswith("2026-07-01T10:00:00")
    assert rows[0]["ends_at"].startswith("2026-07-01T12:00:00")
