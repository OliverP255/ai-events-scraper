from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

import httpx
from psycopg import Connection

from ai_events.enterprise_llm import filter_enterprise_events
from ai_events.filters import should_keep
from ai_events.models import RawEvent, raw_from_parsed
from ai_events.schema_ld import first_event_dict
from ai_events.storage import upsert_event

EB_URL_RE = re.compile(
    r"https://www\.eventbrite\.(?:com|co\.uk)/e/[^\s\"'<>?]+(?:\?[^\s\"'<>]*)?",
    re.I,
)

LISTINGS = [
    "https://www.eventbrite.com/d/united-kingdom--london/ai/",
    "https://www.eventbrite.com/d/united-kingdom--london/enterprise-ai/",
    "https://www.eventbrite.com/d/united-kingdom--london/machine-learning/",
    "https://www.eventbrite.com/d/united-kingdom--london/artificial-intelligence--events/",
    "https://www.eventbrite.com/d/united-kingdom--london/data-science--events/",
    "https://www.eventbrite.com/d/united-kingdom--london/technology--events/",
]


def _strip_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def discover_event_urls(client: httpx.Client, max_pages: int = 4) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for base in LISTINGS:
        for page in range(1, max_pages + 1):
            url = f"{base}?page={page}" if page > 1 else base
            try:
                r = client.get(url)
                r.raise_for_status()
            except httpx.HTTPError:
                break
            found = EB_URL_RE.findall(r.text)
            if not found:
                break
            new_batch = False
            for u in found:
                nu = _strip_query(u)
                if nu not in seen:
                    seen.add(nu)
                    out.append(nu)
                    new_batch = True
            if not new_batch and page > 1:
                break
    return out


def run_eventbrite(client: httpx.Client, conn: Connection) -> tuple[int, int]:
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
        ev = raw_from_parsed("eventbrite", parsed, extra={"listing": "discover"})
        if should_keep(ev):
            candidates.append(ev)
    for ev in filter_enterprise_events(client, candidates):
        upsert_event(conn, ev)
        kept += 1
    return fetched, kept
