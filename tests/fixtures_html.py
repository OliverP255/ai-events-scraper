"""Deterministic HTML/JSON snippets for scraper tests."""

from __future__ import annotations

import json

# Minimal JSON-LD for an in-person London enterprise AI Eventbrite-style event (matches tickets-111)
EVENT_PAGE_LONDON_OFFLINE_AI = """
<!DOCTYPE html>
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebPage","name":"ignore"}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"EducationEvent","name":"Enterprise AI Governance Summit",
"description":"B2B leaders discuss responsible AI and LLM deployment in London.",
"url":"https://www.eventbrite.com/e/enterprise-ai-governance-summit-tickets-111",
"startDate":"2026-06-01T09:00:00+01:00","endDate":"2026-06-01T17:00:00+01:00",
"eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
"location":{"@type":"Place","name":"Convention Centre, Shoreditch",
"address":{"@type":"PostalAddress","addressLocality":"London","addressCountry":"GB","streetAddress":"1 Example St"}}}
</script>
</head><body></body></html>
"""

# Same shape but Manchester venue (tickets-222)
EVENT_PAGE_EB_MANCHESTER_OFFLINE_AI = """
<!DOCTYPE html>
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"Enterprise AI in the North",
"description":"Machine learning for members.",
"url":"https://www.eventbrite.co.uk/e/enterprise-ai-north-tickets-222",
"startDate":"2026-06-04T09:00:00+01:00","endDate":"2026-06-04T17:00:00+01:00",
"eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
"location":{"@type":"Place","name":"Manchester Central",
"address":{"@type":"PostalAddress","addressLocality":"Manchester","addressCountry":"GB"}}}
</script>
</head><body></body></html>
"""

# In-person London AI on Meetup URL (matches discover link)
EVENT_PAGE_MEETUP_LONDON_OFFLINE_AI = """
<!DOCTYPE html>
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"Generative AI for Enterprise Leaders",
"description":"Corporate workshop on LLMs in Canary Wharf.",
"url":"https://www.meetup.com/my-group/events/314159265/",
"startDate":"2026-06-10T18:00:00+01:00","endDate":"2026-06-10T20:00:00+01:00",
"eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
"location":{"@type":"Place","name":"WeWork London",
"address":{"@type":"PostalAddress","addressLocality":"London","addressCountry":"GB"}}}
</script>
</head><body></body></html>
"""

# Online-only (Meetup-style VirtualLocation + Online mode)
EVENT_PAGE_ONLINE_AI = """
<!DOCTYPE html>
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"GenAI for Enterprise — Virtual",
"description":"Generative AI webinar for CIOs.","url":"https://www.meetup.com/g/events/1/",
"startDate":"2026-06-02T18:00:00+01:00","endDate":"2026-06-02T19:00:00+01:00",
"eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode",
"location":{"@type":"VirtualLocation","url":"https://www.meetup.com/g/events/1/"}}
</script>
</head><body></body></html>
"""

# In-person Manchester — AI keywords but wrong city
EVENT_PAGE_MANCHESTER_OFFLINE_AI = """
<!DOCTYPE html>
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"Machine Learning Meetup",
"description":"Analytics and ML for members.",
"url":"https://www.meetup.com/ml-mcr/events/2/",
"startDate":"2026-06-03T18:00:00+01:00","endDate":"2026-06-03T20:00:00+01:00",
"eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
"location":{"@type":"Place","name":"Manchester Central",
"address":{"@type":"PostalAddress","addressLocality":"Manchester","addressCountry":"GB"}}}
</script>
</head><body></body></html>
"""

# techUK-style Event without attendance mode — physical Place with London in name
EVENT_PAGE_TECHUK_LONDON = """
<!DOCTYPE html>
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"Enterprise AI Assurance in Financial Services",
"description":"Sector-specific AI governance roundtable for business leaders.",
"url":"https://www.techuk.org/what-we-deliver/events/ai-assurance-fs.html",
"startDate":"2026-07-01T10:00:00","endDate":"2026-07-01T12:00:00",
"location":{"@type":"Place","name":"Venue near Westminster, London",
"address":{"@type":"PostalAddress","addressLocality":"","addressCountry":"GB"}}}
</script>
</head><body></body></html>
"""


def listing_eventbrite_two_urls() -> str:
    return """
    <html><body>
    <a href="https://www.eventbrite.com/e/first-event-tickets-111?aff=ebdssbdestsearch">a</a>
    <a href="https://www.eventbrite.co.uk/e/second-event-tickets-222">b</a>
    </body></html>
    """


def meetup_find_one_event() -> str:
    return """
    <html><body>
    <a href="https://www.meetup.com/my-group/events/314159265/">x</a>
    </body></html>
    """


def techuk_calendar_two_links() -> str:
    return """
    <html><body>
    <a href="/what-we-deliver/events/one.html">One</a>
    <a href="/what-we-deliver/flagship-and-sponsored-events/two.html">Two</a>
    </body></html>
    """
