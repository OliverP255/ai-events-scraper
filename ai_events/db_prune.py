"""Remove rows that fail current keyword filters and near-duplicate scraper rows (non-pinned only)."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from ai_events.filters import (
    _AI_TECH,
    passes_beginner_audience,
    passes_consumer_ai_hustle,
    passes_founders_executives_tech_leaders,
    passes_hustle_pitch,
    passes_ic_hackathon_research_audience,
    passes_london,
    should_keep,
    should_keep_techuk_ai,
)
from ai_events.models import RawEvent
from ai_events.pinned_dedupe import is_scraper_duplicate_of_pinned


def _norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"[\u2014\u2013\-–—|]+", " ", t)
    t = re.sub(r"[^\w\s&]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _title_ratio(a: str, b: str) -> float:
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _day_key(st: Any) -> date | None:
    if st is None:
        return None
    if isinstance(st, datetime):
        return st.date()
    return None


SOURCE_RANK = {
    "pinned": 0,
    "seed": 1,
    "eventbrite": 2,
    "meetup": 3,
    "techuk": 4,
    "google_search": 5,
}


def _rank_source(src: str) -> int:
    return SOURCE_RANK.get(src or "", 99)


def row_dict_to_raw(row: dict[str, Any]) -> RawEvent:
    extra = row.get("extra_json")
    if isinstance(extra, (bytes, str)):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    elif extra is None:
        extra = {}
    return RawEvent(
        source=row["source"] or "",
        url=row["url"] or "",
        title=row.get("title") or "",
        description=row.get("description"),
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        venue=row.get("venue"),
        city=row.get("city"),
        country=row.get("country"),
        is_in_person=row.get("is_in_person"),
        attendance_mode_uri=row.get("attendance_mode_uri"),
        extra=extra if isinstance(extra, dict) else {},
        pinned=bool(row.get("pinned")),
    )


def filter_failure_reason(ev: RawEvent) -> str | None:
    """If row should be removed for not matching enterprise-AI filters, return a short reason."""
    if ev.pinned:
        return None
    if is_scraper_duplicate_of_pinned(ev):
        return "matches pinned catalog event (title/date); scraper mirror"
    if ev.source == "techuk":
        if should_keep_techuk_ai(ev, require_london=True):
            return None
        from ai_events.filters import _keyword_blob

        t = _keyword_blob(ev)
        if len(t.strip()) < 3:
            return "techuk: too little text"
        if not _AI_TECH.search(t):
            return "techuk: no AI/ML keyword signal"
        if not passes_london(ev):
            return "techuk: not London/geo signal"
        return "techuk: failed should_keep_techuk_ai"
    if should_keep(ev, require_london=True):
        return None
    from ai_events.filters import _keyword_blob

    t = _keyword_blob(ev)
    if len(t.strip()) < 3:
        return "too little title/description"
    if passes_hustle_pitch(ev):
        return "income/hustle pitch pattern"
    if passes_consumer_ai_hustle(ev):
        return "consumer/beginner SaaS hustle pattern"
    if passes_beginner_audience(ev):
        return "beginner/no-experience audience"
    if not _AI_TECH.search(t):
        return "no AI/ML tech keyword"
    if passes_ic_hackathon_research_audience(ev):
        return "IC dev/hackathon/research audience (excluded)"
    if not passes_founders_executives_tech_leaders(ev):
        return "missing founder/exec/investor/GTM audience signal"
    if not passes_london(ev):
        return "no London/geo signal"
    return "failed should_keep (other)"


def _choose_keeper(cluster: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        cluster,
        key=lambda r: (
            _rank_source(r["source"]),
            -len((r.get("description") or "")),
            r.get("id") or "",
        ),
    )


def _same_day_title_duplicate_deletions(active: list[dict[str, Any]]) -> dict[str, str]:
    """
    Same calendar day (or both dates null) + title similarity thresholds as ``prune_quality``.
    Returns ids to remove mapped to a short reason (keeper chosen via ``_choose_keeper``).
    """
    to_delete: dict[str, str] = {}
    n = len(active)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pi] = pj

    for i in range(n):
        for j in range(i + 1, n):
            a, b = active[i], active[j]
            da, db = _day_key(a.get("starts_at")), _day_key(b.get("starts_at"))
            if da != db:
                continue
            ta = a.get("title") or ""
            tb = b.get("title") or ""
            ratio = _title_ratio(ta, tb)
            if da is None and db is None:
                if ratio < 0.92:
                    continue
            else:
                if ratio < 0.82:
                    continue
            union(i, j)

    groups: dict[int, list[dict[str, Any]]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(active[i])
    for group in groups.values():
        if len(group) < 2:
            continue
        keeper = _choose_keeper(group)
        ktitle = (keeper.get("title") or "")[:80]
        for r in group:
            rid = str(r["id"])
            if rid == str(keeper["id"]):
                continue
            to_delete[rid] = (
                f"duplicate: same day + title similarity; kept id={keeper['id']} "
                f"source={keeper.get('source')} title={ktitle!r}"
            )
    return to_delete


def prune_quality(conn: Connection, *, dry_run: bool = False) -> dict[str, Any]:
    """
    Delete non-pinned events that fail current filters, then delete same-day near-duplicate scraper rows.
    Pinned rows are never deleted.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, source, url, title, description, starts_at, ends_at, venue, city, country,
                   is_in_person, attendance_mode_uri, extra_json, pinned
            FROM events
            ORDER BY starts_at NULLS LAST, title
            """
        )
        rows = list(cur.fetchall())

    to_delete: dict[str, str] = {}

    for r in rows:
        if r.get("pinned"):
            continue
        ev = row_dict_to_raw(r)
        reason = filter_failure_reason(ev)
        if reason:
            to_delete[str(r["id"])] = f"not_enterprise_ai: {reason}"

    active = [r for r in rows if str(r["id"]) not in to_delete and not r.get("pinned")]
    to_delete.update(_same_day_title_duplicate_deletions(active))

    removed_list = [{"id": i, "reason": to_delete[i]} for i in sorted(to_delete.keys())]

    if not dry_run and to_delete:
        with conn.cursor() as cur:
            for eid in to_delete:
                cur.execute(
                    "DELETE FROM events WHERE id = %s AND COALESCE(pinned, false) = false",
                    (eid,),
                )
        conn.commit()

    return {
        "dry_run": dry_run,
        "removed_count": len(to_delete),
        "removed": removed_list,
    }


def dedupe_scraper_duplicates(conn: Connection) -> dict[str, Any]:
    """
    Remove duplicate non-pinned rows: (1) same normalized URL (keeps pinned, then newest
    ``fetched_at``, then smallest id), (2) same calendar day + high title similarity
    (same rule as ``prune_quality``).
    """
    from ai_events.storage import dedupe_events_by_normalized_url

    n_url = dedupe_events_by_normalized_url(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, source, url, title, description, starts_at, ends_at, venue, city, country,
                   is_in_person, attendance_mode_uri, extra_json, pinned
            FROM events
            ORDER BY starts_at NULLS LAST, title
            """
        )
        rows = list(cur.fetchall())
    active = [r for r in rows if not r.get("pinned")]
    dup = _same_day_title_duplicate_deletions(active)
    removed_title: list[dict[str, str]] = []
    if dup:
        with conn.cursor() as cur:
            for eid in dup:
                cur.execute(
                    "DELETE FROM events WHERE id = %s AND COALESCE(pinned, false) = false",
                    (eid,),
                )
        conn.commit()
        removed_title = [{"id": i, "reason": dup[i]} for i in sorted(dup.keys())]
    return {
        "normalized_url_removed": n_url,
        "same_day_title_removed_count": len(dup),
        "same_day_title_removed": removed_title,
    }
