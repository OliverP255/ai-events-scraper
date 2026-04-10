from __future__ import annotations

from ai_events.schema_ld import (
    event_from_schema,
    extract_json_ld_events,
    first_event_dict,
)
from tests.fixtures_html import (
    EVENT_PAGE_LONDON_OFFLINE_AI,
    EVENT_PAGE_ONLINE_AI,
)


def test_extract_prefers_event_nodes() -> None:
    nodes = extract_json_ld_events(EVENT_PAGE_LONDON_OFFLINE_AI)
    types = {n.get("@type") for n in nodes}
    assert "EducationEvent" in types


def test_first_event_dict_offline_london() -> None:
    d = first_event_dict(
        EVENT_PAGE_LONDON_OFFLINE_AI,
        "https://www.eventbrite.com/e/enterprise-ai-governance-summit-tickets-111",
    )
    assert d is not None
    assert d["is_in_person"] is True
    assert d["city"] == "London"
    assert "Shoreditch" in (d["venue"] or "")


def test_online_event_marked_not_in_person() -> None:
    d = first_event_dict(
        EVENT_PAGE_ONLINE_AI,
        "https://www.meetup.com/g/events/1/",
    )
    assert d is not None
    assert d["is_in_person"] is False


def test_event_from_schema_virtual_location() -> None:
    node = {
        "@type": "Event",
        "name": "X",
        "startDate": "2026-01-01T10:00:00+00:00",
        "location": {"@type": "VirtualLocation", "url": "https://zoom.example/j"},
    }
    d = event_from_schema(node, "https://example.com")
    assert d["is_in_person"] is False
