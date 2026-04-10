from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from psycopg import Connection

from ai_events.models import RawEvent

_DATA = Path(__file__).resolve().parent / "data" / "pinned_events.json"


def _parse_iso(s: str | None) -> datetime | None:
    if s is None or not str(s).strip():
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"[\u2014\u2013\-–—|]+", " ", t)
    t = re.sub(r"[^\w\s&]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


@lru_cache(maxsize=1)
def _pinned_rows() -> tuple[tuple[str, datetime | None, datetime | None], ...]:
    if not _DATA.is_file():
        return ()
    raw: list[dict[str, Any]] = json.loads(_DATA.read_text(encoding="utf-8"))
    out: list[tuple[str, datetime | None, datetime | None]] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        out.append(
            (
                item["title"],
                _parse_iso(item.get("starts_at")),
                _parse_iso(item.get("ends_at")),
            )
        )
    return tuple(out)


def _title_ratio(a: str, b: str) -> float:
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _dates_overlap_scraper_vs_pinned(
    ev_start: datetime | None,
    ev_end: datetime | None,
    p_start: datetime | None,
    p_end: datetime | None,
) -> bool:
    """True if scraper event dates fall in the pinned window (± a few days)."""
    if p_start is None and p_end is None:
        return False
    if ev_start is None:
        return True
    ev_d = ev_start.date()
    lo = (p_start or p_end).date()
    hi = (p_end or p_start).date()
    pad = timedelta(days=5)
    return (lo - pad) <= ev_d <= (hi + pad)


def is_scraper_duplicate_of_pinned(ev: RawEvent) -> bool:
    """
    True if this scraped row is the same real-world event as a pinned catalog entry
    (e.g. Eventbrite listing for TechEx while we already store the official ai-expo row).
    """
    if ev.source == "pinned":
        return False
    title = ev.title or ""
    if len(_norm_title(title)) < 8:
        return False

    for p_title, p_start, p_end in _pinned_rows():
        r = _title_ratio(title, p_title)
        nt, npt = _norm_title(title), _norm_title(p_title)
        if "techex" in nt and "techex" in npt and "big" in nt and "data" in nt and "big" in npt and "data" in npt:
            r = max(r, 0.92)
        if "gartner" in nt and "gartner" in npt and "cio" in nt and "cio" in npt:
            r = max(r, 0.88)
        if r < 0.78:
            continue
        # Strong title match: drop without requiring dates (listing mirrors catalog).
        if r >= 0.92:
            return True
        if r >= 0.78 and _dates_overlap_scraper_vs_pinned(ev.starts_at, ev.ends_at, p_start, p_end):
            return True
    return False


def delete_scraper_rows_duplicating_pinned_catalog(conn: Connection) -> list[str]:
    """Remove non-pinned rows that match pinned catalog titles/dates. Returns deleted ids."""
    deleted: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, starts_at, ends_at, source, pinned
            FROM events
            WHERE COALESCE(pinned, false) = false
              AND (source IS DISTINCT FROM 'pinned')
            """
        )
        rows = cur.fetchall()
    for row in rows:
        rid, title, st, en, src, _pin = row
        ev = RawEvent(
            source=src or "unknown",
            url="https://dedupe.local/ignore",
            title=title or "",
            description=None,
            starts_at=st,
            ends_at=en,
            venue=None,
            city=None,
            country=None,
            is_in_person=None,
            attendance_mode_uri=None,
            extra={},
            pinned=False,
        )
        if is_scraper_duplicate_of_pinned(ev):
            with conn.cursor() as cur:
                cur.execute("DELETE FROM events WHERE id = %s", (rid,))
            deleted.append(str(rid))
    conn.commit()
    return deleted
