from __future__ import annotations

import json
import re
from typing import Any

import httpx
from psycopg import Connection

from ai_events.datetime_util import parse_iso_datetime
from ai_events.filters import should_keep
from ai_events.models import raw_from_parsed
from ai_events.storage import upsert_event

LUMA_PAGES = [
    "https://luma.com/london"
]

# Backwards-compatible name for tests / imports
LONDON_PAGE = LUMA_PAGES[-1]


def _parse_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def luma_item_to_parsed(item: dict[str, Any]) -> dict[str, Any] | None:
    ev = item.get("event") or {}
    if ev.get("location_type") != "offline":
        return None
    slug = ev.get("url")
    if not isinstance(slug, str) or not slug.strip():
        return None
    page_url = f"https://luma.com/{slug.strip()}"
    geo = ev.get("geo_address_info") or {}
    city = geo.get("city") if isinstance(geo.get("city"), str) else None
    city_state = geo.get("city_state") if isinstance(geo.get("city_state"), str) else None
    venue_bits = [city_state or "", city or ""]
    venue = ", ".join([x for x in venue_bits if x]) or None
    name = ev.get("name")
    title = name.strip() if isinstance(name, str) else ""
    cal = item.get("calendar") or {}
    desc = cal.get("description_short") if isinstance(cal.get("description_short"), str) else None
    starts = parse_iso_datetime(ev.get("start_at"))
    ends = parse_iso_datetime(ev.get("end_at"))
    return {
        "title": title,
        "description": desc,
        "starts_at": starts,
        "ends_at": ends,
        "venue": venue,
        "city": city,
        "country": "GB",
        "is_in_person": True,
        "attendance_mode_uri": "https://schema.org/OfflineEventAttendanceMode",
        "url": page_url,
    }


def run_luma(client: httpx.Client, conn: Connection) -> tuple[int, int]:
    kept = 0
    total = 0
    seen_api: set[str] = set()
    for page_url in LUMA_PAGES:
        try:
            r = client.get(page_url)
            r.raise_for_status()
        except httpx.HTTPError:
            continue
        data = _parse_next_data(r.text)
        if not data:
            continue
        try:
            block = data["props"]["pageProps"]["initialData"]["data"]
            events = block.get("events") or []
        except (KeyError, TypeError):
            continue
        for item in events:
            if not isinstance(item, dict):
                continue
            api_id = item.get("api_id")
            ev_inner = item.get("event") or {}
            slug = ev_inner.get("url") if isinstance(ev_inner.get("url"), str) else ""
            dedupe_key = str(api_id) if api_id is not None else (f"url:{slug}" if slug else None)
            if dedupe_key is None or dedupe_key in seen_api:
                continue
            seen_api.add(dedupe_key)
            total += 1
            parsed = luma_item_to_parsed(item)
            if not parsed:
                continue
            inner_ev = item.get("event") or {}
            tz = inner_ev.get("timezone") if isinstance(inner_ev.get("timezone"), str) else None
            ev = raw_from_parsed(
                "luma",
                parsed,
                extra={"api_id": item.get("api_id"), "event_timezone": tz},
            )
            if should_keep(ev):
                upsert_event(conn, ev)
                kept += 1
    return total, kept
