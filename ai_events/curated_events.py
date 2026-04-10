from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from psycopg import Connection

from ai_events.models import RawEvent
from ai_events.storage import upsert_pinned_catalog_event

_DATA = Path(__file__).resolve().parent / "data" / "pinned_events.json"
_BASE_URL = "https://pinned.catalog/ai-events"


def _parse_dt(s: str | None) -> datetime | None:
    if s is None or not str(s).strip():
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _item_to_raw(item: dict[str, Any]) -> RawEvent:
    slug = item["slug"]
    focus = item.get("focus") or ""
    audience = item.get("audience") or ""
    desc_lines = [f"Focus: {focus}", f"Audience: {audience}"]
    if item.get("date_note"):
        desc_lines.append(str(item["date_note"]))
    description = "\n".join(desc_lines)
    extra: dict[str, Any] = {
        "curated": True,
        "focus": focus,
        "audience": audience,
    }
    if item.get("date_note"):
        extra["date_note"] = item["date_note"]
    return RawEvent(
        source="pinned",
        url=f"{_BASE_URL}/{slug}",
        title=item["title"],
        description=description,
        starts_at=_parse_dt(item.get("starts_at")),
        ends_at=_parse_dt(item.get("ends_at")),
        venue=item.get("venue"),
        city=item.get("city"),
        country=item.get("country"),
        is_in_person=True,
        attendance_mode_uri=None,
        extra=extra,
        pinned=True,
    )


def load_pinned_event_dicts() -> list[dict[str, Any]]:
    if not _DATA.is_file():
        return []
    return json.loads(_DATA.read_text(encoding="utf-8"))


def ensure_pinned_events(conn: Connection) -> int:
    """Load pinned catalog into Postgres; refreshes titles/dates from JSON each run."""
    items = load_pinned_event_dicts()
    n = 0
    for item in items:
        if not isinstance(item, dict) or not item.get("slug") or not item.get("title"):
            continue
        ev = _item_to_raw(item)
        upsert_pinned_catalog_event(conn, ev)
        n += 1
    return n
