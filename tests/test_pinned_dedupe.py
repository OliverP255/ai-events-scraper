"""Pinned catalog vs scraper deduplication."""

from __future__ import annotations

from datetime import datetime, timezone

from ai_events.models import RawEvent
from ai_events.pinned_dedupe import is_scraper_duplicate_of_pinned


def _scraper(
    *,
    title: str,
    url: str = "https://www.eventbrite.co.uk/e/techex-tickets",
    source: str = "eventbrite",
    starts_at: datetime | None = None,
) -> RawEvent:
    if starts_at is None:
        starts_at = datetime(2026, 2, 4, 10, 0, tzinfo=timezone.utc)
    return RawEvent(
        source=source,
        url=url,
        title=title,
        description="Enterprise AI in London",
        starts_at=starts_at,
        ends_at=None,
        venue="Olympia",
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
        pinned=False,
    )


def test_rejects_eventbrite_techex_near_pinned_catalog() -> None:
    ev = _scraper(title="TechEx Global — AI & Big Data Expo")
    assert is_scraper_duplicate_of_pinned(ev) is True


def test_rejects_when_title_close_and_dates_align() -> None:
    ev = _scraper(
        title="TechEx Global | AI and Big Data Expo 2026",
        starts_at=datetime(2026, 2, 5, 9, 0, tzinfo=timezone.utc),
    )
    assert is_scraper_duplicate_of_pinned(ev) is True


def test_does_not_reject_pinned_source() -> None:
    ev = _scraper(
        source="pinned",
        url="https://www.ai-expo.net/global/#2026-london",
        title="TechEx Global — AI & Big Data Expo Global (co-located tracks)",
    )
    assert is_scraper_duplicate_of_pinned(ev) is False


def test_allows_unrelated_event() -> None:
    ev = _scraper(
        title="Private LLM meetup for founders",
        starts_at=datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc),
    )
    assert is_scraper_duplicate_of_pinned(ev) is False
