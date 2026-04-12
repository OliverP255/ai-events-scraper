from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from ai_events.webapp import db
from ai_events.webapp.embeddings import (
    any_embedding_in_db,
    embed_text_async,
    vector_to_pg_literal,
)
from ai_events.webapp.settings import semantic_search_enabled


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
        "pinned": bool(r.get("pinned")),
    }


def _row_to_csv_dict(r: Any) -> dict[str, Any]:
    """Flat dict suitable for CSV (extra_json as JSON string)."""
    d = _row_to_dict(r)
    ex = d.get("extra_json")
    if isinstance(ex, dict):
        d["extra_json"] = json.dumps(ex, ensure_ascii=False)
    elif ex is not None and not isinstance(ex, str):
        d["extra_json"] = json.dumps(ex, ensure_ascii=False)
    return d


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _filter_only_where(
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[str, list[Any]]:
    """WHERE clause for source + date filters only (no text search)."""
    wh: list[str] = []
    args: list[Any] = []
    i = 1

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
    return where_sql, args


def _fts_where(
    q: str,
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[str, list[Any]]:
    """Full-text + filters (legacy keyword search)."""
    wh: list[str] = []
    args: list[Any] = []
    i = 1

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

    where_sql = " WHERE " + " AND ".join(wh)
    return where_sql, args


_SELECT_LIST = """
        SELECT id, source, url, title, description,
               starts_at, ends_at, venue, city, country,
               is_in_person, attendance_mode_uri, extra_json, fetched_at, pinned FROM events
"""


async def _search_semantic(
    *,
    q: str,
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int] | None:
    vec = await embed_text_async(q)
    if vec is None:
        return None

    vec_lit = vector_to_pg_literal(vec)
    where_sql, filter_args = _filter_only_where(source, date_from, date_to)

    count_sql = f"SELECT count(*)::bigint FROM events{where_sql}"
    total = await db.fetch_val(count_sql, *filter_args)
    if total is None:
        total = 0

    n = len(filter_args)
    vec_i = n + 1
    lim_i = n + 2
    off_i = n + 3
    list_args = [*filter_args, vec_lit, limit, offset]
    list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY (embedding IS NULL) ASC,
                 embedding <=> ${vec_i}::vector NULLS LAST,
                 starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i} OFFSET ${off_i}
    """

    try:
        rows = await db.fetch_all(list_sql, *list_args)
    except Exception:
        return None
    return [_row_to_dict(r) for r in rows], int(total)


async def _search_fts(
    *,
    q: str,
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    where_sql, args = _fts_where(q, source, date_from, date_to)

    count_sql = f"SELECT count(*)::bigint FROM events{where_sql}"
    total = await db.fetch_val(count_sql, *args)
    if total is None:
        total = 0

    n = len(args)
    lim_i = n + 1
    off_i = n + 2
    list_args = [*args, limit, offset]
    list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i} OFFSET ${off_i}
    """

    rows = await db.fetch_all(list_sql, *list_args)
    return [_row_to_dict(r) for r in rows], int(total)


async def search_events(
    *,
    q: str | None,
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Semantic (pgvector) or full-text search when ``q`` is set; filters only when unset."""
    pool = await db.get_pool()
    if pool is None:
        return [], 0

    q_clean = (q or "").strip()
    if not q_clean:
        where_sql, args = _filter_only_where(source, date_from, date_to)
        count_sql = f"SELECT count(*)::bigint FROM events{where_sql}"
        total = await db.fetch_val(count_sql, *args)
        if total is None:
            total = 0
        n = len(args)
        lim_i = n + 1
        off_i = n + 2
        list_args = [*args, limit, offset]
        list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i} OFFSET ${off_i}
        """
        rows = await db.fetch_all(list_sql, *list_args)
        return [_row_to_dict(r) for r in rows], int(total)

    if semantic_search_enabled():
        has_vec = await any_embedding_in_db()
        if has_vec:
            sem = await _search_semantic(
                q=q_clean,
                source=source,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset,
            )
            if sem is not None:
                return sem

    return await _search_fts(
        q=q_clean,
        source=source,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


async def search_events_csv(
    *,
    q: str | None,
    source: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    max_rows: int = 50_000,
) -> str:
    """Same filters as search; CSV up to max_rows."""
    pool = await db.get_pool()
    if pool is None:
        return ""

    q_clean = (q or "").strip()
    if not q_clean:
        where_sql, args = _filter_only_where(source, date_from, date_to)
        n = len(args)
        lim_i = n + 1
        list_args = [*args, max_rows]
        list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i}
        """
    elif semantic_search_enabled() and await any_embedding_in_db():
        vec = await embed_text_async(q_clean)
        if vec is not None:
            vec_lit = vector_to_pg_literal(vec)
            where_sql, filter_args = _filter_only_where(source, date_from, date_to)
            n = len(filter_args)
            vec_i = n + 1
            lim_i = n + 2
            list_args = [*filter_args, vec_lit, max_rows]
            list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY (embedding IS NULL) ASC,
                 embedding <=> ${vec_i}::vector NULLS LAST,
                 starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i}
        """
        else:
            where_sql, args = _fts_where(q_clean, source, date_from, date_to)
            n = len(args)
            lim_i = n + 1
            list_args = [*args, max_rows]
            list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i}
        """
    else:
        where_sql, args = _fts_where(q_clean, source, date_from, date_to)
        n = len(args)
        lim_i = n + 1
        list_args = [*args, max_rows]
        list_sql = f"""
{_SELECT_LIST}
        {where_sql}
        ORDER BY starts_at ASC NULLS LAST, title ASC
        LIMIT ${lim_i}
        """

    rows = await db.fetch_all(list_sql, *list_args)
    dicts = [_row_to_csv_dict(r) for r in rows]

    buf = io.StringIO()
    if not dicts:
        return ""
    fieldnames = list(dicts[0].keys())
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in dicts:
        w.writerow(row)
    return buf.getvalue()


async def list_sources() -> list[str]:
    pool = await db.get_pool()
    if pool is None:
        return []
    rows = await db.fetch_all("SELECT DISTINCT source FROM events ORDER BY source")
    return [r["source"] for r in rows]
