from __future__ import annotations

from datetime import datetime, timezone

from ai_events.sources.luma import luma_item_to_parsed
from tests.fixtures_html import luma_offline_ai_item, luma_online_item


def test_luma_offline_parsed_has_london_and_offline_mode() -> None:
    item = luma_offline_ai_item()
    d = luma_item_to_parsed(item)
    assert d is not None
    assert d["url"].startswith("https://luma.com/")
    assert d["city"] == "London"
    assert d["is_in_person"] is True
    assert "London" in (d["venue"] or "")
    assert d["starts_at"] == datetime(2026, 8, 1, 8, 0, 0, tzinfo=timezone.utc)
    assert d["ends_at"] == datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)


def test_luma_online_skipped_at_parse_stage() -> None:
    assert luma_item_to_parsed(luma_online_item()) is None
