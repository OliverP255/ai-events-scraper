"""Upsert events from seeds/curated_events_search_lines_*.json into Postgres (source=seed)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_events.models import RawEvent
from ai_events.pg_connect import connect_psycopg
from ai_events.storage import dedupe_events_by_normalized_url, upsert_event

# Prefer explicit 1-32 file; fall back to any seeds/curated_events_search_lines_*.json
_CANDIDATES = [
    ROOT / "seeds" / "curated_events_search_lines_1-32.json",
    *sorted(ROOT.glob("seeds/curated_events_search_lines_*.json"), reverse=True),
]


def _parse_dt(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _venue(d: dict) -> str | None:
    parts = [p for p in (d.get("venue_name"), d.get("venue_address")) if p]
    return ", ".join(parts) if parts else None


def _extra(d: dict, batch: str) -> dict:
    out: dict = {"curated_research": True, "batch": batch}
    for k in ("time_source", "start_date", "end_date", "timezone"):
        v = d.get(k)
        if v:
            out[k] = v
    return out


def _item_to_raw(item: dict, batch: str) -> RawEvent:
    return RawEvent(
        source="seed",
        url=item["url"],
        title=item.get("title") or "",
        description=item.get("description"),
        starts_at=_parse_dt(item.get("starts_at")),
        ends_at=_parse_dt(item.get("ends_at")),
        venue=_venue(item),
        city=item.get("venue_locality") or "London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra=_extra(item, batch),
    )


def _pick_json_path() -> Path:
    seen: set[Path] = set()
    for p in _CANDIDATES:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        if rp.is_file():
            return rp
    raise SystemExit("No seeds/curated_events_search_lines_*.json found.")


def main() -> None:
    path = _pick_json_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    events_in = data.get("events") or []
    if not events_in:
        raise SystemExit(f"No events in {path}")
    meta = data.get("meta") or {}
    batch = f"curated_json:{path.stem}"

    raw_events = [_item_to_raw(e, batch) for e in events_in]
    conn = connect_psycopg()
    try:
        for ev in raw_events:
            upsert_event(conn, ev)
        removed = dedupe_events_by_normalized_url(conn)
        print(
            f"Upserted {len(raw_events)} seed rows from {path.name} "
            f"(meta record_count={meta.get('record_count', '?')}); "
            f"dedupe removed {removed} duplicate row(s) by URL."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
