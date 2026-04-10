from __future__ import annotations

from datetime import datetime, timezone

from psycopg import Connection

from ai_events.curated_events import ensure_pinned_events, load_pinned_event_dicts
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
    assert len(load_pinned_event_dicts()) == 22


def test_upsert_event_does_not_overwrite_pinned_row(pg_conn: Connection) -> None:
    # Use a non-catalog URL so event_key matches the attacker's (url|time); pinned.catalog URLs use url-only keys.
    dt = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    pinned_ev = RawEvent(
        source="pinned",
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
        pinned=True,
    )
    upsert_pinned_catalog_event(pg_conn, pinned_ev)
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
    assert rows[0]["source"] == "pinned"
    assert rows[0]["pinned"] is True


def test_ensure_pinned_events_loads_full_catalog(pg_conn: Connection) -> None:
    n = ensure_pinned_events(pg_conn)
    assert n == 22
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 22
    assert sum(1 for r in rows if r.get("pinned")) == 22


def test_event_key_pinned_catalog_stable_when_dates_change() -> None:
    u = "https://pinned.catalog/ai-events/test-slug"
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
