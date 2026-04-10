"""JSON-LD + HTML: dates/times resolve correctly (including subEvent + meta fallbacks)."""

from __future__ import annotations

from ai_events.schema_ld import event_from_schema, first_event_dict


def test_event_from_schema_date_only_start() -> None:
    d = event_from_schema(
        {
            "@type": "Event",
            "name": "All-day policy forum",
            "startDate": "2026-12-01",
            "endDate": "2026-12-01",
            "location": {"@type": "Place", "name": "London"},
        },
        "https://example.com/e/1",
    )
    assert d["starts_at"] is not None
    assert d["starts_at"].date().isoformat() == "2026-12-01"


def test_event_from_schema_sub_event_fills_missing() -> None:
    d = event_from_schema(
        {
            "@type": "Event",
            "name": "Recurring series",
            "location": {"@type": "Place", "name": "London"},
            "subEvent": {
                "@type": "Event",
                "startDate": "2026-05-01T19:00:00+01:00",
                "endDate": "2026-05-01T21:00:00+01:00",
            },
        },
        "https://example.com/e/2",
    )
    assert d["starts_at"] is not None
    assert d["starts_at"].hour == 19
    assert d["ends_at"] is not None
    assert d["ends_at"].hour == 21


def test_first_event_dict_meta_fallback_when_ld_missing_times() -> None:
    html = """
    <!DOCTYPE html>
    <html><head>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Event","name":"TBA schedule",
    "url":"https://example.com/evt","location":{"@type":"Place","name":"London"}}
    </script>
    <meta property="event:start_time" content="2026-08-08T15:30:00+01:00" />
    <meta property="event:end_time" content="2026-08-08T17:30:00+01:00" />
    </head><body></body></html>
    """
    d = first_event_dict(html, "https://example.com/evt")
    assert d is not None
    assert d["starts_at"] is not None and d["ends_at"] is not None
    assert d["starts_at"].hour == 15
    assert d["ends_at"].hour == 17
