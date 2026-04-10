from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ai_events.webapp import db


def _row_to_dict(r: Any) -> dict[str, Any]:
    extra = r["extra_json"]
    if isinstance(extra, (bytes, str)):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    elif extra is None:
        extra = {}
    return {
        "id": r["id"],
        "source": r["source"],
        "url": r["url"],
        "title": r["title"],
        "description": r["description"],
        "starts_at": _iso(r["starts_at"]),
        "ends_at": _iso(r["ends_at"]),
        "venue": r["venue"],
        "city": r["city"],
        "country": r["country"],
        "is_in_person": r["is_in_person"],
        "attendance_mode_uri": r["attendance_mode_uri"],
        "extra_json": extra,
        "fetched_at": _iso(r["fetched_at"]),
    }


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


async def search_events(
    *,
    q: str | None,
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Full-text + filters. Returns (rows, total_count)."""
    pool = await db.get_pool()
    if pool is None:
        return [], 0

    q = (q or "").strip()
    has_q = bool(q)

    wh: list[str] = []
    args: list[Any] = []
    i = 1

    if has_q:
        wh.append(f"search_tsv @@ plainto_tsquery('english', ${i})")
        args.append(q)
        i += 1

    if source:
        wh.append(f"source = ${i}")
        args.append(source)
        i += 1

    if date_from is not None:
        wh.append(f"starts_at >= ${i}")
        args.append(date_from)
        i += 1

    if date_to is not None:
        wh.append(f"starts_at <= ${i}")
        args.append(date_to)
        i += 1

    where_sql = (" WHERE " + " AND ".join(wh)) if wh else ""

    count_sql = f"SELECT count(*)::bigint FROM events{where_sql}"
    total = await db.fetch_val(count_sql, *args)
    if total is None:
        total = 0

    lim_i = i
    off_i = i + 1
    list_args = [*args, limit, offset]
    list_sql = f"""
        SELECT id, source, url, title, description,
               starts_at, ends_at, venue, city, country,
               is_in_person, attendance_mode_uri, extra_json, fetched_at
        FROM events
        {where_sql}
        ORDER BY (starts_at IS NULL), starts_at ASC, title ASC
        LIMIT ${lim_i} OFFSET ${off_i}
    """

    rows = await db.fetch_all(list_sql, *list_args)
    return [_row_to_dict(r) for r in rows], int(total)


async def list_sources() -> list[str]:
    pool = await db.get_pool()
    if pool is None:
        return []
    rows = await db.fetch_all("SELECT DISTINCT source FROM events ORDER BY source")
    return [r["source"] for r in rows]
