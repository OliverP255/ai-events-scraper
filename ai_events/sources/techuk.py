from __future__ import annotations

from urllib.parse import urljoin

import httpx
from psycopg import Connection
from bs4 import BeautifulSoup

from ai_events.filters import should_keep
from ai_events.models import raw_from_parsed
from ai_events.schema_ld import first_event_dict
from ai_events.storage import upsert_event

CALENDAR_URL = "https://www.techuk.org/what-we-deliver/events.html"


def discover_event_urls(client: httpx.Client) -> list[str]:
    try:
        r = client.get(CALENDAR_URL)
        r.raise_for_status()
    except httpx.HTTPError:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    seen: set[str] = set()
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/what-we-deliver/events/" in href and href.endswith(".html"):
            full = urljoin(CALENDAR_URL, href)
            if full not in seen:
                seen.add(full)
                out.append(full)
        if "/what-we-deliver/flagship-and-sponsored-events/" in href and href.endswith(".html"):
            full = urljoin(CALENDAR_URL, href)
            if full not in seen:
                seen.add(full)
                out.append(full)
    return out


def run_techuk(client: httpx.Client, conn: Connection) -> tuple[int, int]:
    kept = 0
    fetched = 0
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
        ev = raw_from_parsed("techuk", parsed)
        if should_keep(ev):
            upsert_event(conn, ev)
            kept += 1
    return fetched, kept
