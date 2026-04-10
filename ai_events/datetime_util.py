"""Parse event start/end instants from strings (schema.org, meta tags)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup


def parse_iso_datetime(value: Any) -> datetime | None:
    """Parse ISO-8601-like timestamps used in JSON-LD and meta tags.

    Handles: trailing Z, space instead of T, numeric offsets without colon (+0100),
    date-only (YYYY-MM-DD) as local midnight (naive), and fractional seconds.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None

    if s.endswith("Z") and "+" not in s[:-1]:
        s = s[:-1] + "+00:00"

    # Offset forms like +0100 / +0000 at end (not +01:00)
    m = re.search(r"([+-])(\d{2})(\d{2})$", s)
    if m and ":" not in s[-6:]:
        s = s[: m.start()] + f"{m.group(1)}{m.group(2)}:{m.group(3)}"

    # "YYYY-MM-DD HH:MM:SS" → T separator for fromisoformat
    if re.match(r"^\d{4}-\d{2}-\d{2} ", s) and "T" not in s[:19]:
        s = s.replace(" ", "T", 1)

    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass

    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and len(s) == 10:
        try:
            return datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def extract_meta_event_datetimes(html: str) -> dict[str, datetime | None]:
    """Fallback times from Open Graph / Facebook-style event meta tags."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, datetime | None] = {"starts_at": None, "ends_at": None}

    def set_from_meta(prop: str, key: str) -> None:
        tag = soup.find("meta", attrs={"property": prop})
        if tag is None:
            tag = soup.find("meta", property=prop)
        if tag is None:
            return
        c = tag.get("content")
        dt = parse_iso_datetime(c)
        if dt and out[key] is None:
            out[key] = dt

    for prop, key in (
        ("event:start_time", "starts_at"),
        ("og:event:start_time", "starts_at"),
        ("event:end_time", "ends_at"),
        ("og:event:end_time", "ends_at"),
    ):
        set_from_meta(prop, key)

    for tag in soup.find_all(attrs={"itemprop": "startDate"}):
        if tag.name == "meta" and tag.get("content"):
            out["starts_at"] = out["starts_at"] or parse_iso_datetime(tag["content"])
        elif tag.name == "time" and tag.get("datetime"):
            out["starts_at"] = out["starts_at"] or parse_iso_datetime(tag["datetime"])

    for tag in soup.find_all(attrs={"itemprop": "endDate"}):
        if tag.name == "meta" and tag.get("content"):
            out["ends_at"] = out["ends_at"] or parse_iso_datetime(tag["content"])
        elif tag.name == "time" and tag.get("datetime"):
            out["ends_at"] = out["ends_at"] or parse_iso_datetime(tag["datetime"])

    return out
