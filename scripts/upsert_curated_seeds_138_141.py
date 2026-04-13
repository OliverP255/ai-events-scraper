"""Curated upsert for seeds/search_curated_from_web.txt lines 138–141 (final URLs in file)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ai_events.models import RawEvent
from ai_events.pg_connect import connect_psycopg
from ai_events.storage import dedupe_events_by_normalized_url, upsert_event

LON = ZoneInfo("Europe/London")
BATCH = "search_curated_from_web_urls_138_141"


def _dt(y: int, m: int, d: int, h: int = 0, mi: int = 0) -> datetime:
    return datetime(y, m, d, h, mi, tzinfo=LON)


def _ev(
    url: str,
    title: str,
    description: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
    venue: str | None,
    *,
    extra_notes: dict | None = None,
    is_in_person: bool | None = True,
) -> RawEvent:
    extra: dict = {"curated_research": True, "batch": BATCH}
    if extra_notes:
        extra.update(extra_notes)
    return RawEvent(
        source="seed",
        url=url,
        title=title,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        venue=venue,
        city="London",
        country="GB",
        is_in_person=is_in_person,
        attendance_mode_uri=None,
        extra=extra,
    )


EVENTS: list[RawEvent] = [
    _ev(
        "https://www.techuk.org/what-we-deliver/flagship-and-sponsored-events/building-the-smarter-state-2026.html",
        "Building the Smarter State 2026",
        "techUK’s annual conference for senior government and technology leaders on digital transformation of public services: responsible AI in the public sector, digital sovereignty, resilience, procurement, and lessons from leading digital governments (speakers listed on the official page include UK and international public-sector CTOs and digital leaders).",
        _dt(2026, 5, 13, 9, 0),
        _dt(2026, 5, 13, 17, 0),
        "Central London",
        extra_notes={"hours_source": "Official techUK event page: 9am–5pm, 13 May 2026."},
    ),
    _ev(
        "https://www.ai.engineer/europe",
        "AI Engineer Europe 2026",
        "Three-day flagship for AI engineers: workshop day (8 April), then two days of multi-track talks and expo (9–10 April) on agents, MCP, coding agents, evals, infra, and tooling — in London with an online track (official site: April 8–10, 2026 · London, UK & Online).",
        _dt(2026, 4, 8, 9, 0),
        _dt(2026, 4, 10, 18, 0),
        "London",
        extra_notes={
            "format": "In-person (London) and online; schedule grid on site ends ~late afternoon on 10 April.",
            "area_note": "Attendee hotel block copy references London SW1P 3EE (Westminster/South Bank area).",
        },
    ),
    _ev(
        "https://communitystack.io/conferences/cloud-native-london",
        "Cloud Native & Open Source AI Conference (Community Stack)",
        "Single-day, multi-track practitioner conference at BrainStation on cloud native platforms, Kubernetes AI workloads, open-source LLM and agentic systems in production — main, leadership, and workshop tracks (no vendor roadmap pitch format per organiser).",
        _dt(2026, 6, 11, 9, 0),
        _dt(2026, 6, 11, 17, 15),
        "BrainStation, London",
        extra_notes={"agenda_source": "Official page agenda: doors09:00, closing keynote ends 16:35, networking & close 17:15."},
    ),
    _ev(
        "https://www.bcs.org/events-calendar/2026/november/search-solutions-2026/",
        "Search Solutions 2026",
        "BCS Information Retrieval Specialist Group (IRSG) annual forum for search and information retrieval: practitioner-focused tutorials and conference content bridging research and industry. The programme is a Tutorial Day on 24 November and a Conference Day on 25 November (separate registration); BCS London office listing gives conference hours 9:30am–9:00pm on Wednesday 25 November.",
        _dt(2026, 11, 25, 9, 30),
        _dt(2026, 11, 25, 21, 0),
        "BCS, 25 Copthall Avenue, London EC2R 7BP",
        extra_notes={
            "tutorial_day": "Tuesday 24 November 2026 — tutorial day; times not stated on this page.",
            "time_source": "BCS event listing: Wednesday 25 November, 9:30am–9:00pm.",
        },
    ),
]


def main() -> None:
    assert len(EVENTS) == 4, len(EVENTS)
    conn = connect_psycopg()
    try:
        for ev in EVENTS:
            upsert_event(conn, ev)
        removed = dedupe_events_by_normalized_url(conn)
        print(f"Upserted {len(EVENTS)} curated seed events; dedupe removed {removed} duplicate row(s).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
