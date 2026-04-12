from __future__ import annotations

from ai_events.schema_ld import (
    best_event_dict,
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


def test_best_event_dict_og_fallback() -> None:
    html = """<!DOCTYPE html><html><head>
<meta property="og:title" content="London AI Executive Breakfast" />
<meta property="og:description" content="Join founders and VPs for applied AI in the enterprise." />
<meta property="event:start_time" content="2026-06-15T08:00:00+01:00" />
</head><body></body></html>"""
    d = best_event_dict(html, "https://example.com/promo/1")
    assert d is not None
    assert "Executive" in d["title"]
    assert d["starts_at"] is not None
    assert "founders and VPs" in (d.get("description") or "")


def test_best_event_dict_merges_main_content_with_json_ld() -> None:
    html = """
<!DOCTYPE html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"AI Summit",
"description":"Short meta from JSON-LD.",
"url":"https://example.com/e/1",
"startDate":"2026-06-01T10:00:00+01:00",
"eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
"location":{"@type":"Place","name":"Venue",
"address":{"@type":"PostalAddress","addressLocality":"London","addressCountry":"GB"}}}
</script>
</head><body>
<header>Site chrome</header>
<main>
<p>This paragraph only appears in the page body and mentions Shoreditch and CIO roundtable.</p>
</main>
</body></html>
"""
    d = best_event_dict(html, "https://example.com/e/1")
    assert d is not None
    desc = d.get("description") or ""
    assert "Short meta from JSON-LD." in desc
    assert "Shoreditch" in desc
    assert "CIO roundtable" in desc
    assert "Site chrome" not in desc


def test_event_from_schema_virtual_location() -> None:
    node = {
        "@type": "Event",
        "name": "X",
        "startDate": "2026-01-01T10:00:00+00:00",
        "location": {"@type": "VirtualLocation", "url": "https://zoom.example/j"},
    }
    d = event_from_schema(node, "https://example.com")
    assert d["is_in_person"] is False
