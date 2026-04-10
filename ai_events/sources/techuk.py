from __future__ import annotations

import calendar
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from psycopg import Connection

from ai_events.filters import should_keep_techuk_ai
from ai_events.models import raw_from_parsed
from ai_events.schema_ld import first_event_dict
from ai_events.storage import upsert_event

CALENDAR_URL = "https://www.techuk.org/what-we-deliver/events.html"


def _month_num(name: str) -> int | None:
    n = name.strip().lower()
    for i in range(1, 13):
        if calendar.month_name[i].lower() == n or calendar.month_abbr[i].lower() == n:
            return i
    return None


def _parse_techuk_date_span(text: str) -> datetime | None:
    """Parse UK-style dates from techUK event headers, e.g. '14 April 2026' or '14 – 16 April 2026'."""
    s = text.replace("\u2013", "-").replace("–", "-").strip()
    # Range, same month: 14 - 16 April 2026
    m = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", s)
    if m:
        day = int(m.group(1))
        mon = _month_num(m.group(3))
        year = int(m.group(4))
        if mon is None:
            return None
        try:
            return datetime(year, mon, day)
        except ValueError:
            return None
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", s)
    if m:
        day = int(m.group(1))
        mon = _month_num(m.group(2))
        year = int(m.group(3))
        if mon is None:
            return None
        try:
            return datetime(year, mon, day)
        except ValueError:
            return None
    return None


def parse_techuk_event_html(html: str, page_url: str) -> dict[str, Any] | None:
    """
    techUK event pages often omit JSON-LD; parse the public event-header + detail markup.
    """
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1", class_=lambda c: bool(c) and "event-title" in c.split())
    if not title_el:
        og = soup.find("meta", attrs={"property": "og:title"})
        title = (og.get("content") or "").strip() if og else ""
    else:
        title = title_el.get_text(strip=True)
    if not title:
        return None

    starts_at: datetime | None = None
    hdr = soup.find("div", class_=lambda c: bool(c) and "event-header" in c.split())
    if hdr:
        date_sp = hdr.find("span", class_=lambda c: bool(c) and "event-date" in c.split())
        if date_sp:
            starts_at = _parse_techuk_date_span(date_sp.get_text(" ", strip=True))
    if starts_at is None:
        sp = soup.find("span", class_=lambda c: bool(c) and "event-date" in c.split())
        if sp:
            starts_at = _parse_techuk_date_span(sp.get_text(" ", strip=True))

    desc: str | None = None
    detail = soup.find("section", class_=lambda c: bool(c) and "event-detail-entry" in c.split())
    if detail:
        p = detail.find("p")
        if p:
            desc = (p.get_text(" ", strip=True) or "").replace("\xa0", " ").strip() or None

    venue: str | None = None
    city: str | None = None
    loc_blob = ""
    if hdr:
        loc_blob = hdr.get_text(" ", strip=True)
        # Lines after the title often list city / venue (e.g. "London", "Excel, London")
        lines = [ln.strip() for ln in loc_blob.splitlines() if ln.strip()]
        for ln in lines:
            if re.search(r"\bLondon\b", ln, re.I):
                city = "London"
            if ln.lower() not in ("free", "partner event") and not re.match(
                r"^\d{1,2}(\s*-\s*\d{1,2})?\s+[A-Za-z]+\s+\d{4}$", ln.replace("–", "-").strip()
            ):
                if len(ln) > 2 and not ln.lower().startswith("http"):
                    if re.search(r"london|online|excel|hybrid|manchester|birmingham", ln, re.I):
                        venue = ln if venue is None else f"{venue}; {ln}"
    if city is None and loc_blob and re.search(r"\bLondon\b", loc_blob, re.I):
        city = "London"

    in_person: bool | None = None
    blob_l = (loc_blob + " " + (desc or "")).lower()
    if "online" in blob_l and "london" not in blob_l.replace("london tech", ""):
        # Purely online webinars (no London venue)
        if "london" not in blob_l:
            in_person = False
    elif "london" in blob_l or city == "London":
        in_person = True

    return {
        "title": title,
        "description": desc,
        "starts_at": starts_at,
        "ends_at": None,
        "venue": venue,
        "city": city,
        "country": "GB" if city or venue else None,
        "is_in_person": in_person,
        "attendance_mode_uri": None,
        "url": page_url,
    }


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
        full = urljoin(CALENDAR_URL, href)
        if full.rstrip("/").endswith("/events.html"):
            continue
        if "/what-we-deliver/events/" in href and href.endswith(".html"):
            if full not in seen:
                seen.add(full)
                out.append(full)
        elif "/what-we-deliver/flagship-and-sponsored-events/" in href and href.endswith(".html"):
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
        text = r.text
        page_url = str(r.url)
        parsed = first_event_dict(text, page_url) or parse_techuk_event_html(text, page_url)
        if not parsed:
            continue
        ev = raw_from_parsed("techuk", parsed)
        if should_keep_techuk_ai(ev, require_london=False):
            upsert_event(conn, ev)
            kept += 1
    return fetched, kept
