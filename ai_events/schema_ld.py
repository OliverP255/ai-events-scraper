from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from ai_events.datetime_util import extract_meta_event_datetimes, parse_iso_datetime

EVENT_TYPES = frozenset(
    {
        "Event",
        "BusinessEvent",
        "EducationEvent",
        "SocialEvent",
        "Festival",
        "SaleEvent",
        "ExhibitionEvent",
    }
)

OFFLINE = "https://schema.org/OfflineEventAttendanceMode"
ONLINE = "https://schema.org/OnlineEventAttendanceMode"
MIXED = "https://schema.org/MixedEventAttendanceMode"


def _flatten_graph(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and "@graph" in data:
        g = data["@graph"]
        return g if isinstance(g, list) else []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def extract_json_ld_events(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _flatten_graph(data):
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(x in EVENT_TYPES for x in types if isinstance(x, str)):
                out.append(node)
    return out


def _location_text(loc: Any) -> str:
    if loc is None:
        return ""
    if isinstance(loc, str):
        return loc
    if not isinstance(loc, dict):
        return ""
    parts: list[str] = []
    name = loc.get("name")
    if isinstance(name, str):
        parts.append(name)
    addr = loc.get("address")
    if isinstance(addr, str):
        parts.append(addr)
    elif isinstance(addr, dict):
        for k in (
            "streetAddress",
            "addressLocality",
            "addressRegion",
            "postalCode",
            "addressCountry",
        ):
            v = addr.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
    return ", ".join(parts)


def _start_end_from_node(node: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    """Resolve start/end from Event node, including schema.org subEvent."""
    s = parse_iso_datetime(node.get("startDate"))
    e = parse_iso_datetime(node.get("endDate"))
    if s is not None and e is not None:
        return s, e
    sub = node.get("subEvent")
    items: list[dict[str, Any]] = []
    if isinstance(sub, dict):
        items = [sub]
    elif isinstance(sub, list):
        items = [x for x in sub if isinstance(x, dict)]
    for it in items:
        if s is None:
            s = parse_iso_datetime(it.get("startDate"))
        if e is None:
            e = parse_iso_datetime(it.get("endDate"))
        if s is not None and e is not None:
            break
    return s, e


def event_from_schema(node: dict[str, Any], page_url: str) -> dict[str, Any]:
    """Map schema.org Event node to a dict usable for RawEvent."""
    mode = node.get("eventAttendanceMode")
    loc = node.get("location")
    is_online_loc = isinstance(loc, dict) and loc.get("@type") == "VirtualLocation"
    in_person: bool | None
    if mode == OFFLINE:
        in_person = True
    elif mode == ONLINE:
        in_person = False
    elif mode == MIXED:
        in_person = None
    elif is_online_loc:
        in_person = False
    else:
        in_person = True if loc else None

    addr_locality = None
    country = None
    if isinstance(loc, dict):
        addr = loc.get("address")
        if isinstance(addr, dict):
            addr_locality = addr.get("addressLocality")
            country = addr.get("addressCountry")

    title = node.get("name") or ""
    desc = node.get("description")
    if not isinstance(title, str):
        title = str(title)
    if isinstance(desc, str):
        description = desc
    else:
        description = None

    starts_at, ends_at = _start_end_from_node(node)
    return {
        "title": title.strip(),
        "description": description,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "venue": _location_text(loc) or None,
        "city": addr_locality if isinstance(addr_locality, str) else None,
        "country": country if isinstance(country, str) else None,
        "is_in_person": in_person,
        "attendance_mode_uri": mode if isinstance(mode, str) else None,
        "url": node.get("url") if isinstance(node.get("url"), str) else page_url,
    }


def first_event_dict(html: str, page_url: str) -> dict[str, Any] | None:
    nodes = extract_json_ld_events(html)
    if not nodes:
        return None
    dated = [n for n in nodes if n.get("startDate")]
    node = dated[0] if dated else nodes[0]
    parsed = event_from_schema(node, page_url)
    meta = extract_meta_event_datetimes(html)
    if parsed.get("starts_at") is None and meta.get("starts_at"):
        parsed["starts_at"] = meta["starts_at"]
    if parsed.get("ends_at") is None and meta.get("ends_at"):
        parsed["ends_at"] = meta["ends_at"]
    return parsed
