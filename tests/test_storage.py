from __future__ import annotations

from datetime import datetime

from psycopg import Connection

from ai_events.models import RawEvent
from ai_events.storage import event_key, iter_events_rows, upsert_event


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
