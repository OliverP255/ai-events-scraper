from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from psycopg import Connection

from ai_events.filters import should_keep_seed_url
from ai_events.models import RawEvent, raw_from_parsed
from ai_events.schema_ld import best_event_dict
from ai_events.storage import upsert_event


# Programme / multi-city index pages — not a single in-person event; drop from curated seeds + DB.
CURATED_SEED_HUB_URLS: tuple[str, ...] = (
    "https://www.oracle.com/ai-world-tour/",
    "https://www.servicenow.com/events/ai-summits.html",
    "https://londontechweek.com/",
)


def load_seed_urls(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("http://") or line.startswith("https://"):
            out.append(line)
    return out


def load_manual_seed_rows(seed_file: Path) -> list[dict[str, Any]]:
    """
    Optional ``{seed_stem}.manual.json`` next to the seed list: hand-authored rows for URLs
    that block scrapers or fail ``should_keep_seed_url`` on thin markup. Each object needs
    ``url`` and ``title``; other fields mirror RawEvent (ISO datetimes for starts_at/ends_at).
    """
    p = seed_file.parent / f"{seed_file.stem}.manual.json"
    if not p.is_file():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("events"), list):
        raw = raw["events"]
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict) and (x.get("url") or "").strip()]


def _parse_manual_dt(val: Any) -> datetime | None:
    if val is None or val == "":
        return None
    if not isinstance(val, str):
        return None
    return datetime.fromisoformat(val.replace("Z", "+00:00"))


def raw_event_from_manual_row(row: dict[str, Any], *, seed_file: str) -> RawEvent:
    url = str(row["url"]).strip()
    title = (row.get("title") or "").strip() or url
    desc = row.get("description")
    if desc is not None:
        desc = str(desc).strip() or None
    extra = {"seed_file": seed_file, "manual": True}
    if isinstance(row.get("extra"), dict):
        extra.update(row["extra"])
    return RawEvent(
        source="seed",
        url=url,
        title=title,
        description=desc,
        starts_at=_parse_manual_dt(row.get("starts_at")),
        ends_at=_parse_manual_dt(row.get("ends_at")),
        venue=row.get("venue"),
        city=row.get("city") or "London",
        country=row.get("country") or "GB",
        is_in_person=bool(row.get("is_in_person", True)),
        attendance_mode_uri=row.get("attendance_mode_uri"),
        extra=extra,
    )


def run_seeds(client: httpx.Client, conn: Connection, seed_file: Path) -> tuple[int, int, int]:
    kept = 0
    fetched = 0
    for u in load_seed_urls(seed_file):
        try:
            r = client.get(u)
            r.raise_for_status()
        except httpx.HTTPError:
            continue
        fetched += 1
        parsed = best_event_dict(r.text, str(r.url))
        if not parsed:
            continue
        ev = raw_from_parsed("seed", parsed, extra={"seed_file": seed_file.name})
        if should_keep_seed_url(ev):
            upsert_event(conn, ev)
            kept += 1

    manual_n = 0
    for row in load_manual_seed_rows(seed_file):
        ev = raw_event_from_manual_row(row, seed_file=seed_file.name)
        upsert_event(conn, ev)
        manual_n += 1

    return fetched, kept, manual_n


def refresh_seed_metadata(
    client: httpx.Client,
    conn: Connection,
    seed_file: Path,
) -> tuple[int, int]:
    """
    Re-fetch every URL in the seed list and upsert from parsed markup **without**
    ``should_keep_seed_url`` so titles, dates, and descriptions track official pages.
    """
    ok = 0
    failed = 0
    for u in load_seed_urls(seed_file):
        try:
            r = client.get(u)
            r.raise_for_status()
        except httpx.HTTPError:
            failed += 1
            continue
        parsed = best_event_dict(r.text, str(r.url))
        if not parsed:
            failed += 1
            continue
        ev = raw_from_parsed(
            "seed",
            parsed,
            extra={"seed_file": seed_file.name, "refreshed": True},
        )
        upsert_event(conn, ev)
        ok += 1
    return ok, failed
