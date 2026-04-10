from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime, timezone
from typing import Any, Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json

from ai_events.models import RawEvent


def _norm_url(url: str) -> str:
    u = url.strip()
    if "?" in u:
        base, q = u.split("?", 1)
        drop = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "aff"}
        parts = []
        for pair in q.split("&"):
            if "=" in pair:
                k, _ = pair.split("=", 1)
                if k.lower() in drop:
                    continue
            parts.append(pair)
        if parts:
            return base + "?" + "&".join(parts)
    return u


def event_key(ev: RawEvent) -> str:
    nu = _norm_url(ev.url)
    # Pinned rows: stable id from canonical URL only (dates/titles can change without orphan rows).
    if ev.pinned:
        h = hashlib.sha256(nu.encode("utf-8")).hexdigest()
        return h[:32]
    when = ev.starts_at.isoformat() if ev.starts_at else ""
    h = hashlib.sha256(f"{nu}|{when}".encode("utf-8")).hexdigest()
    return h[:32]


def upsert_event(conn: Connection, ev: RawEvent) -> None:
    """Insert or update from scrapers. Does not overwrite rows marked ``pinned``."""
    eid = event_key(ev)
    fetched_at = datetime.now(timezone.utc)
    pin = bool(ev.pinned)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (
                id, source, url, title, description,
                starts_at, ends_at, venue, city, country,
                is_in_person, attendance_mode_uri, extra_json, fetched_at, pinned
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                starts_at = EXCLUDED.starts_at,
                ends_at = EXCLUDED.ends_at,
                venue = EXCLUDED.venue,
                city = EXCLUDED.city,
                country = EXCLUDED.country,
                is_in_person = EXCLUDED.is_in_person,
                attendance_mode_uri = EXCLUDED.attendance_mode_uri,
                extra_json = EXCLUDED.extra_json,
                fetched_at = EXCLUDED.fetched_at,
                pinned = EXCLUDED.pinned
            WHERE NOT COALESCE(events.pinned, false)
            """,
            (
                eid,
                ev.source,
                _norm_url(ev.url),
                ev.title,
                ev.description,
                ev.starts_at,
                ev.ends_at,
                ev.venue,
                ev.city,
                ev.country,
                ev.is_in_person,
                ev.attendance_mode_uri,
                Json(ev.extra),
                fetched_at,
                pin,
            ),
        )
    conn.commit()


def upsert_pinned_catalog_event(conn: Connection, ev: RawEvent) -> None:
    """Upsert canonical catalog rows; always refreshes from source data and keeps ``pinned`` true."""
    if not ev.pinned:
        raise ValueError("upsert_pinned_catalog_event requires ev.pinned True")
    eid = event_key(ev)
    fetched_at = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (
                id, source, url, title, description,
                starts_at, ends_at, venue, city, country,
                is_in_person, attendance_mode_uri, extra_json, fetched_at, pinned
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, true
            )
            ON CONFLICT (id) DO UPDATE SET
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                starts_at = EXCLUDED.starts_at,
                ends_at = EXCLUDED.ends_at,
                venue = EXCLUDED.venue,
                city = EXCLUDED.city,
                country = EXCLUDED.country,
                is_in_person = EXCLUDED.is_in_person,
                attendance_mode_uri = EXCLUDED.attendance_mode_uri,
                extra_json = EXCLUDED.extra_json,
                fetched_at = EXCLUDED.fetched_at,
                pinned = true
            """,
            (
                eid,
                ev.source,
                _norm_url(ev.url),
                ev.title,
                ev.description,
                ev.starts_at,
                ev.ends_at,
                ev.venue,
                ev.city,
                ev.country,
                ev.is_in_person,
                ev.attendance_mode_uri,
                Json(ev.extra),
                fetched_at,
            ),
        )
    conn.commit()


def _serialize_cell(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return val


def iter_events_rows(conn: Connection) -> Iterator[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, source, url, title, description,
                   starts_at, ends_at, venue, city, country,
                   is_in_person, attendance_mode_uri, extra_json, fetched_at, pinned
            FROM events
            ORDER BY (starts_at IS NULL), starts_at, title
            """
        )
        for row in cur:
            d = dict(row)
            for k in (
                "starts_at",
                "ends_at",
                "fetched_at",
            ):
                if k in d:
                    d[k] = _serialize_cell(d[k])
            if "extra_json" in d:
                ex = d["extra_json"]
                if isinstance(ex, dict):
                    d["extra_json"] = json.dumps(ex, ensure_ascii=False)
                elif ex is not None and not isinstance(ex, str):
                    d["extra_json"] = json.dumps(ex, ensure_ascii=False)
            yield d


def export_csv(conn: Connection) -> str:
    buf = io.StringIO()
    rows = list(iter_events_rows(conn))
    if not rows:
        return ""
    fieldnames = list(rows[0].keys())
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def export_json_lines(conn: Connection) -> str:
    lines: list[str] = []
    for row in iter_events_rows(conn):
        lines.append(json.dumps(row, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")
