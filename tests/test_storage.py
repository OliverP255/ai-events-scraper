from __future__ import annotations

from datetime import datetime, timezone

from psycopg import Connection

from ai_events.curated_events import (
    ensure_pinned_events,
    load_pinned_event_dicts,
    prune_stale_catalog_rows,
)
from ai_events.models import RawEvent
from ai_events.storage import (
    event_key,
    iter_events_rows,
    upsert_event,
    upsert_pinned_catalog_event,
)


def _ev(url: str, when: datetime | None) -> RawEvent:
    return RawEvent(
        source="t",
        url=url,
        title="T",
        description=None,
        starts_at=when,
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
    )


def test_event_key_stable_and_unique_per_url_time() -> None:
    a = _ev("https://example.com/a", datetime(2026, 1, 1, 10, 0, 0))
    b = _ev("https://example.com/b", datetime(2026, 1, 1, 10, 0, 0))
    assert event_key(a) != event_key(b)
    c = _ev("https://example.com/a", datetime(2026, 1, 2, 10, 0, 0))
    assert event_key(a) != event_key(c)


def test_upsert_idempotent(pg_conn: Connection) -> None:
    ev = _ev("https://example.com/x", datetime(2026, 3, 1, 12, 0, 0))
    upsert_event(pg_conn, ev)
    upsert_event(pg_conn, ev)
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 1


def test_pinned_catalog_json_count() -> None:
    assert len(load_pinned_event_dicts()) == 20


def test_upsert_event_does_not_overwrite_pinned_row(pg_conn: Connection) -> None:
    """Scraper upsert must not update a row flagged ``pinned`` in the DB (same event_key)."""
    dt = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    ev = RawEvent(
        source="meetup",
        url="https://example.com/pinned-protect-test",
        title="Original Title",
        description="x",
        starts_at=dt,
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
        pinned=False,
    )
    upsert_event(pg_conn, ev)
    eid = event_key(ev)
    with pg_conn.cursor() as cur:
        cur.execute("UPDATE events SET pinned = true WHERE id = %s", (eid,))
    pg_conn.commit()
    attacker = RawEvent(
        source="meetup",
        url="https://example.com/pinned-protect-test",
        title="Replaced By Scraper",
        description="y",
        starts_at=dt,
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
        pinned=False,
    )
    upsert_event(pg_conn, attacker)
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 1
    assert rows[0]["title"] == "Original Title"
    assert rows[0]["pinned"] is True


def test_ensure_pinned_events_loads_full_catalog(pg_conn: Connection) -> None:
    n = ensure_pinned_events(pg_conn)
    assert n == 20
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 20
    assert sum(1 for r in rows if r.get("pinned")) == 20


def test_event_key_pinned_catalog_stable_when_dates_change() -> None:
    u = "https://example.org/events/official-page#test-slug"
    a = RawEvent(
        source="pinned",
        url=u,
        title="A",
        description=None,
        starts_at=datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
        pinned=True,
    )
    b = RawEvent(
        source="pinned",
        url=u,
        title="B",
        description=None,
        starts_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
        pinned=True,
    )
    assert event_key(a) == event_key(b)


def test_prune_stale_catalog_removes_legacy_pinned_catalog_urls(pg_conn: Connection) -> None:
    legacy = RawEvent(
        source="pinned",
        url="https://pinned.catalog/ai-events/legacy-slug",
        title="Legacy mock catalog row",
        description="x",
        starts_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
        pinned=True,
    )
    upsert_pinned_catalog_event(pg_conn, legacy)
    assert len(list(iter_events_rows(pg_conn))) == 1
    r = prune_stale_catalog_rows(pg_conn)
    assert r["total_removed"] >= 1
    assert len(list(iter_events_rows(pg_conn))) == 0
