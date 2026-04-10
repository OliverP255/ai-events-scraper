"""Unit tests for parse_iso_datetime and meta extraction."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ai_events.datetime_util import extract_meta_event_datetimes, parse_iso_datetime


@pytest.mark.parametrize(
    "raw,expect_iso",
    [
        ("2026-03-15T14:00:00+01:00", "2026-03-15T14:00:00+01:00"),
        ("2026-03-15T14:00:00Z", "2026-03-15T14:00:00+00:00"),
        ("2026-03-15T14:00:00.500+01:00", "2026-03-15T14:00:00.500000+01:00"),
        ("2026-03-15T14:00:00+0100", "2026-03-15T14:00:00+01:00"),
        ("2026-03-15T14:00:00-0500", "2026-03-15T14:00:00-05:00"),
        ("2026-12-01", "2026-12-01T00:00:00"),
        ("2026-06-01 09:00:00+01:00", "2026-06-01T09:00:00+01:00"),
    ],
)
def test_parse_iso_datetime_variants(raw: str, expect_iso: str) -> None:
    got = parse_iso_datetime(raw)
    assert got is not None
    exp = datetime.fromisoformat(expect_iso.replace("Z", "+00:00"))
    if got.tzinfo is None and exp.tzinfo is None:
        assert got.replace(microsecond=0) == exp.replace(microsecond=0)
    elif got.tzinfo and exp.tzinfo:
        assert got.astimezone(timezone.utc) == exp.astimezone(timezone.utc)
    else:
        assert got == exp


def test_parse_iso_datetime_none_and_empty() -> None:
    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime("not-a-date") is None


def test_extract_meta_reads_event_start_end() -> None:
    html = """
    <html><head>
    <meta property="event:start_time" content="2027-01-02T10:15:00+00:00" />
    <meta property="event:end_time" content="2027-01-02T11:45:00+00:00" />
    </head></html>
    """
    m = extract_meta_event_datetimes(html)
    assert m["starts_at"] == datetime.fromisoformat("2027-01-02T10:15:00+00:00")
    assert m["ends_at"] == datetime.fromisoformat("2027-01-02T11:45:00+00:00")


def test_extract_meta_itemprop_start_date() -> None:
    html = """
    <html><head>
    <meta itemprop="startDate" content="2028-06-06T18:00:00+01:00" />
    </head></html>
    """
    m = extract_meta_event_datetimes(html)
    assert m["starts_at"] is not None
    assert m["starts_at"].hour == 18
