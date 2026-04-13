"""Meetup: GQL discovery + event pages; London text filter skipped (search is London-scoped)."""

from __future__ import annotations

from datetime import datetime

import httpx
from psycopg import Connection

from ai_events.sources import meetup as mp
from ai_events.storage import iter_events_rows
from tests.fixtures_html import (
    EVENT_PAGE_MEETUP_LONDON_OFFLINE_AI,
    EVENT_PAGE_ONLINE_AI,
)

_GQL_BODY = {
    "data": {
        "eventSearch": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "edges": [
                {
                    "node": {
                        "eventUrl": "https://www.meetup.com/my-group/events/314159265/",
                    }
                }
            ],
        }
    }
}


def _transport_meetup_gql_then_event(body: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if request.method == "POST" and "gql2" in u:
            return httpx.Response(200, json=_GQL_BODY)
        if "my-group/events/314159265" in u:
            return httpx.Response(200, text=body)
        return httpx.Response(404, text=u)

    return httpx.MockTransport(handler)


def test_meetup_gql_search_matches_product_semantics() -> None:
    v = mp._event_search_variables(mp.MEETUP_KEYWORD_QUERIES[0], None)
    assert v["filter"]["query"] == "enterprise AI"
    assert set(mp.MEETUP_KEYWORD_QUERIES) >= {
        "enterprise AI",
        "machine learning",
        "LLMs",
        "AI agent",
        "generative AI",
    }
    assert v["filter"]["radius"] == 25.0
    assert v["filter"]["country"] == "gb"


def test_discover_finds_meetup_event_url() -> None:
    transport = _transport_meetup_gql_then_event(EVENT_PAGE_ONLINE_AI)
    with httpx.Client(transport=transport) as client:
        urls = mp.discover_event_urls(client)
    assert urls == ["https://www.meetup.com/my-group/events/314159265/"]


def test_run_meetup_online_persisted_without_london_gate(pg_conn: Connection) -> None:
    transport = _transport_meetup_gql_then_event(EVENT_PAGE_ONLINE_AI)
    with httpx.Client(transport=transport) as client:
        fetched, kept = mp.run_meetup(client, pg_conn)
    assert fetched == 1
    assert kept == 1
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 1


def test_run_meetup_offline_london_persisted(pg_conn: Connection) -> None:
    transport = _transport_meetup_gql_then_event(EVENT_PAGE_MEETUP_LONDON_OFFLINE_AI)
    with httpx.Client(transport=transport) as client:
        fetched, kept = mp.run_meetup(client, pg_conn)
    assert fetched == 1
    assert kept == 1
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 1
    assert rows[0]["city"] == "London"
    assert datetime.fromisoformat(rows[0]["starts_at"]) == datetime.fromisoformat(
        "2026-06-10T18:00:00+01:00"
    )
    assert datetime.fromisoformat(rows[0]["ends_at"]) == datetime.fromisoformat(
        "2026-06-10T20:00:00+01:00"
    )
