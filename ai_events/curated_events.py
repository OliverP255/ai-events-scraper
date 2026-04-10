from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from psycopg import Connection

from ai_events.models import RawEvent
from ai_events.storage import event_key, upsert_pinned_catalog_event

_DATA = Path(__file__).resolve().parent / "data" / "pinned_events.json"
_FALLBACK_BASE = "https://pinned.catalog/ai-events"


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
    url = (item.get("url") or "").strip() or f"{_FALLBACK_BASE}/{slug}"
    return RawEvent(
        source="pinned",
        url=url,
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


def allowed_pinned_catalog_ids() -> set[str]:
    """Stable ``events.id`` values for the current ``pinned_events.json`` catalog."""
    out: set[str] = set()
    for item in load_pinned_event_dicts():
        if not isinstance(item, dict) or not item.get("slug") or not item.get("title"):
            continue
        ev = _item_to_raw(item)
        out.add(event_key(ev))
    return out


def prune_stale_catalog_rows(conn: Connection) -> dict[str, Any]:
    """
    Remove legacy placeholder catalog rows (mock URLs) and ``source='pinned'`` rows whose id
    is not in the current JSON catalog (e.g. after URL migration).
    """
    removed_mock_url: list[str] = []
    removed_stale_pinned: list[str] = []
    allowed = allowed_pinned_catalog_ids()

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM events WHERE url LIKE %s RETURNING id",
            ("%pinned.catalog%",),
        )
        for row in cur.fetchall() or []:
            removed_mock_url.append(str(row[0]))

        cur.execute(
            "DELETE FROM events WHERE url IN (%s, %s) RETURNING id",
            (
                "https://example.com/pinned-protect-test",
                "https://example.com/x",
            ),
        )
        for row in cur.fetchall() or []:
            removed_mock_url.append(str(row[0]))

        if allowed:
            placeholders = ",".join(["%s"] * len(allowed))
            cur.execute(
                f"""
                DELETE FROM events
                WHERE source = %s AND id NOT IN ({placeholders})
                RETURNING id
                """,
                ("pinned", *sorted(allowed)),
            )
            for row in cur.fetchall() or []:
                removed_stale_pinned.append(str(row[0]))

    conn.commit()
    return {
        "removed_mock_url": removed_mock_url,
        "removed_stale_pinned_source": removed_stale_pinned,
        "total_removed": len(removed_mock_url) + len(removed_stale_pinned),
    }


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
