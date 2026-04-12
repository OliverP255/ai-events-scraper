from __future__ import annotations

import re
from typing import Any

import httpx
from psycopg import Connection

from ai_events.enterprise_llm import filter_enterprise_events
from ai_events.filters import should_keep
from ai_events.models import RawEvent, raw_from_parsed
from ai_events.schema_ld import first_event_dict
from ai_events.storage import upsert_event

MEETUP_EVENT_RE = re.compile(
    r"https://www\.meetup\.com/[^/\s\"'<>]+/events/\d+/?",
    re.I,
)

MEETUP_GQL_URL = "https://www.meetup.com/gql2"

# Same semantics as Meetup find: keywords + London + 25 mi via gql2 (London lat/lon).
MEETUP_KEYWORD_QUERIES = [
    "enterprise AI",
    "machine learning",
    "LLMs",
    "AI agent",
]

_LONDON_LAT = 51.5074
_LONDON_LON = -0.1278
_RADIUS_MI = 25.0

_EVENT_SEARCH_QUERY = """
query MeetupEventSearch($filter: EventSearchFilter!, $sort: KeywordSort, $first: Int!, $after: String) {
  eventSearch(filter: $filter, sort: $sort, first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        eventUrl
      }
    }
  }
}
"""

_MAX_EVENT_URLS = 2000
_GQL_PAGE_SIZE = 100


def _event_search_variables(keyword_query: str, after: str | None) -> dict[str, Any]:
    return {
        "filter": {
            "lat": _LONDON_LAT,
            "lon": _LONDON_LON,
            "country": "gb",
            "radius": _RADIUS_MI,
            "query": keyword_query,
            "doConsolidateEvents": True,
        },
        "sort": {"sortField": "RELEVANCE"},
        "first": _GQL_PAGE_SIZE,
        "after": after,
    }


def _discover_event_urls_for_query(
    client: httpx.Client, keyword_query: str, seen: set[str], out: list[str]
) -> None:
    after: str | None = None
    while len(out) < _MAX_EVENT_URLS:
        body = {
            "query": _EVENT_SEARCH_QUERY,
            "variables": _event_search_variables(keyword_query, after),
        }
        try:
            r = client.post(MEETUP_GQL_URL, json=body)
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError):
            break
        if data.get("errors"):
            break
        es = (data.get("data") or {}).get("eventSearch")
        if not isinstance(es, dict):
            break
        for edge in es.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            node = edge.get("node")
            if not isinstance(node, dict):
                continue
            url = node.get("eventUrl")
            if not isinstance(url, str):
                continue
            m = MEETUP_EVENT_RE.match(url.strip())
            if not m:
                continue
            u = m.group(0).rstrip("/") + "/"
            if u not in seen:
                seen.add(u)
                out.append(u)
        page = es.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        nxt = page.get("endCursor")
        if not isinstance(nxt, str) or nxt == after:
            break
        after = nxt


def discover_event_urls(client: httpx.Client) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in MEETUP_KEYWORD_QUERIES:
        if len(out) >= _MAX_EVENT_URLS:
            break
        _discover_event_urls_for_query(client, q, seen, out)
    return out


def run_meetup(client: httpx.Client, conn: Connection) -> tuple[int, int]:
    kept = 0
    fetched = 0
    candidates: list[RawEvent] = []
    for u in discover_event_urls(client):
        try:
            r = client.get(u)
            r.raise_for_status()
        except httpx.HTTPError:
            continue
        fetched += 1
        parsed = first_event_dict(r.text, str(r.url))
        if not parsed:
            continue
        ev = raw_from_parsed("meetup", parsed)
        if should_keep(ev, require_london=False):
            candidates.append(ev)
    for ev in filter_enterprise_events(client, candidates):
        upsert_event(conn, ev)
        kept += 1
    return fetched, kept
