"""Upsert curated research rows for seeds/search_curated_from_web.txt lines 78–117."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ai_events.models import RawEvent
from ai_events.pg_connect import connect_psycopg
from ai_events.storage import dedupe_events_by_normalized_url, upsert_event

LON = ZoneInfo("Europe/London")
BATCH = "search_curated_from_web_urls_61_100"


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
        is_in_person=True,
        attendance_mode_uri=None,
        extra=extra,
    )


EVENTS: list[RawEvent] = [
    _ev(
        "https://events.databricks.com/FY27-AI-Days-London",
        "Databricks AI Days London",
        "In-person Databricks AI Days for data and AI leaders and practitioners: keynotes, breakout sessions, and networking focused on the lakehouse, generative AI, and production analytics on Databricks.",
        _dt(2026, 3, 19, 9, 30),
        _dt(2026, 3, 19, 18, 0),
        "London (venue published in registration)",
 ),
    _ev(
        "https://events.databricks.com/devconnect-london",
        "Databricks DevConnect London",
        "Evening technical meetup for data and AI practitioners hosted by Databricks Developer Relations (with Qubika): product deep-dives, real-world talks, and networking.",
        _dt(2026, 4, 29, 17, 0),
        _dt(2026, 4, 29, 21, 0),
        "Databricks London, 11–14 Windmill St, London W1T 2JG",
    ),
    _ev(
        "https://cloud.google.com/events/ai-agents-live-london",
        "Google Cloud AI Live + Labs London (Day 1)",
        "Invite-only in-person briefing on agentic AI and Google Cloud: keynote with customer panel, hands-on agent session, and networking (as published on the event page).",
        _dt(2026, 3, 25, 13, 0),
        _dt(2026, 3, 25, 19, 0),
        "The Arches, 471–473 Dereham Pl, London EC2A 3HJ",
    ),
    _ev(
        "https://aka.ms/agentconLondon2026",
        "AgentCon London",
        "One-day developer conference on the AI Agents World Tour: talks, workshops, and demos for engineers building and shipping AI agents.",
        _dt(2026, 9, 8, 9, 0),
        _dt(2026, 9, 8, 17, 0),
        "LSBU Hub, 100–116 London Rd, London SE1 6LN",
    ),
    _ev(
        "https://event.idc.com/event/cio-summit-uk/",
        "IDC European CIO Summit UK 2026",
        "Full-day IDC executive forum for CIOs and senior IT leaders on technology modernization, resilience, risk, and scaling AI responsibly.",
        _dt(2026, 4, 14, 9, 30),
        _dt(2026, 4, 14, 17, 0),
        "etc.venues County Hall, Belvedere Rd, London",
    ),
    _ev(
        "https://event.idc.com/event/idc-insight-executive-event/",
        "IDC & Insight Executive Event — The AI Foundation",
        "One-day executive briefing (IDC × Insight) on building the technical and cultural foundations needed to move from AI pilots to scalable production.",
        _dt(2026, 4, 22, 11, 0),
        _dt(2026, 4, 22, 17, 0),
        "Cavendish Venues — 1 America Square, London EC3",
    ),
    _ev(
        "https://event.idc.com/event/futuretech-summit-uk/",
        "IDC European FutureTech Summit UK 2026",
        "IDC summit for CTOs, architects, and technology leaders on AI-ready infrastructure, cloud-native platforms, edge, data, and responsible AI at scale.",
        _dt(2026, 11, 5, 9, 30),
        _dt(2026, 11, 5, 17, 0),
        "etc.venues County Hall, Belvedere Rd, London",
    ),
    _ev(
        "https://event.idc.com/event/ai-data-summit-uk/",
        "IDC European AI & Data Summit UK 2026",
        "Full-day IDC forum for CDOs and AI/data leaders on trusted data foundations, scaling AI, governance, and compliance (including EU AI Act context).",
        _dt(2026, 9, 10, 8, 30),
        _dt(2026, 9, 10, 16, 45),
        "London, United Kingdom",
    ),
    _ev(
        "https://aiimpact.isg-one.com/london",
        "ISG AI Impact Summit 2026 — London",
        "One-and-a-half-day executive summit on turning AI investment into measurable business outcomes, autonomy, data readiness, and new operating models.",
        _dt(2026, 9, 9, 9, 0),
        _dt(2026, 9, 10, 18, 0),
        "Park Plaza Victoria, London",
    ),
    _ev(
        "https://datascience.thepeopleevents.com/",
        "Data Science Week /4th Data Science & AI Summit — London 2026",
        "Two-day London conference on AI, data science, machine learning, and analytics with keynotes, tracks, and an exhibition (4th edition).",
        _dt(2026, 10, 1, 9, 0),
        _dt(2026, 10, 2, 18, 0),
        "London (see organiser venue page for room)",
    ),
    _ev(
        "https://mlconference.ai/london/",
        "MLcon London 2026",
        "Multi-day programme on ML, generative AI, and MLOps: workshops 11 & 14–15 May, core conference & expo 12–13 May at Park Plaza Victoria.",
        _dt(2026, 5, 12, 9, 0),
        _dt(2026, 5, 13, 18, 0),
        "Park Plaza Victoria London, 239 Vauxhall Bridge Rd, London SW1V 1EQ",
    ),
    _ev(
        "https://2026.mvml.org/",
        "MVML 2026 — 12th International Conference on Machine Vision and Machine Learning",
        "Academic conference (in-person in London with virtual participation) on machine vision and machine learning; co-located with ICSTA 2026.",
        _dt(2026, 8, 16, 9, 0),
        _dt(2026, 8, 18, 17, 0),
        "London, United Kingdom (venue per registration materials)",
    ),
    _ev(
        "https://www.fintechtalents.com/events/europe/festival-london/",
        "FTT Fintech Festival — London 2026",
        "Two-day festival for banking, fintech, and payments leaders across multiple stages (including AI transformation and co-located identity and fraud tracks).",
        _dt(2026, 11, 9, 9, 0),
        _dt(2026, 11, 10, 18, 0),
        "The Brewery, London",
    ),
    _ev(
        "https://moneylive-insights.com/events/summit/",
        "MoneyLIVE Summit 2026",
        "Two-day banking and payments leadership conference (agenda dated 9–10 March 2026). Note: page hero also advertises a 2027 edition—dates above follow the published 2026 programme.",
        _dt(2026, 3, 9, 9, 0),
        _dt(2026, 3, 10, 18, 0),
        "Business Design Centre, London",
        extra_notes={"schedule_note": "Hero banner shows 2–3 Mar 2027 BDC; detailed 2026 agenda uses 9–10 Mar 2026."},
    ),
    _ev(
        "https://www.insurtechinsights.com/europe/",
        "Insurtech Insights Europe 2027",
        "Europe’s large-scale insurtech conference for carriers, insurtechs, and investors (2027 edition).",
        _dt(2027, 3, 17, 9, 0),
        _dt(2027, 3, 18, 18, 0),
        "InterContinental London – The O2, Waterview Dr, London SE10 0TW",
        extra_notes={"year_note": "Dates confirmed via ticket partner listing; verify on insurtechinsights.com."},
    ),
    _ev(
        "https://informaconnect.com/finovateeurope/",
        "FinovateEurope 2026",
        "Fast-paced fintech conference with 7-minute demos, executive keynotes, and networking; Informa Connect notes 2027 edition TBC on the hub while 2026 ran 10–11 Feb in London.",
        _dt(2026, 2, 10, 9, 0),
        _dt(2026, 2, 11, 18, 0),
        "InterContinental London – The O2",
        extra_notes={"hub_note": "Marketing site highlights 2027 TBC; row reflects widely published 2026 London dates."},
    ),
    _ev(
        "https://www.fintechconnect.com/",
        "FinTech Connect 2026",
        "Major fintech exhibition and conference co-located with Tokenize: LDN; enterprise buyers meet solution providers across AI, core modernisation, payments, and compliance.",
        _dt(2026, 12, 1, 9, 0),
        _dt(2026, 12, 2, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://london.insuretechconnect.com/",
        "ITC London 2027",
        "Invite-only insurtech conference for senior London Market and UK insurance leaders.",
        _dt(2027, 1, 25, 9, 0),
        _dt(2027, 1, 26, 18, 0),
        "The Brewery, London",
    ),
    _ev(
        "https://intelligentautomation-conference.com/global/",
        "Intelligent Automation Conference Global — London 2026",
        "Part of TechEx Global: enterprise intelligent automation and AI ops content co-located with AI & Big Data, Cyber Security & Cloud, and related expos at Olympia.",
        _dt(2026, 2, 4, 9, 0),
        _dt(2026, 2, 5, 16, 0),
        "Olympia London",
    ),
    _ev(
        "https://www.giant.health/",
        "GIANT Health London 2026",
        "Two-day in-person NHS innovation and health-tech festival (AI, medtech, and digital health) at the Business Design Centre.",
        _dt(2026, 12, 7, 9, 0),
        _dt(2026, 12, 8, 18, 0),
        "Business Design Centre, London",
    ),
    _ev(
        "https://events.newsweek.com/ai-health-london-2026",
        "Newsweek AI Health Summit London 2026",
        "One-day summit for NHS and UK healthcare leaders on deploying AI safely and effectively: keynotes, case studies, panels, and networking.",
        _dt(2026, 7, 2, 8, 15),
        _dt(2026, 7, 2, 18, 0),
        "London (per organiser registration)",
    ),
    _ev(
        "https://www.kingsfund.org.uk/events/digital-health-ai-conference-2026",
        "The King’s Fund — Digital health and AI conference 2026",
        "Full-day conference on building an AI-enabled health and care system that works for people: implementation, infrastructure, inclusion, and leadership.",
        _dt(2026, 6, 30, 8, 15),
        _dt(2026, 6, 30, 17, 0),
        "The King’s Fund, London W1G 0AN",
    ),
    _ev(
        "https://ihm.org.uk/event/health-ai-tech-show/",
        "Health + AI Tech Show 2026",
        "Full-day summit with three parallel tracks on clinical AI, genomics and biotech AI, and hospital operations; hands-on labs and exhibition. Structured event fields list Big Penny Social as location (body copy also mentions BPS Venues).",
        _dt(2026, 4, 29, 8, 0),
        _dt(2026, 4, 29, 21, 0),
        "Big Penny Social, London E17 6AL",
        extra_notes={"venue_note": "IHM page body mentions BPS Venues; date/time/location block points to Big Penny Social."},
    ),
    _ev(
        "https://events.economist.com/ai-health-summit/",
        "Economist Impact — AI in Health Summit (co-located with Future of Health Europe)",
        "AI in Health Summit sessions on 1 October 2026, co-located with Future of Health Europe (30 September–1 October), in person at the Royal College of Physicians.",
        _dt(2026, 10, 1, 9, 0),
        _dt(2026, 10, 1, 18, 0),
        "Royal College of Physicians, 11 St Andrews Pl, London NW1 4LE",
        extra_notes={"colocated": "Future of Health Europe spans 30 Sep–1 Oct 2026."},
    ),
    _ev(
        "https://events.economist.com/business-innovation-summit/",
        "Economist Impact — AI and Business Innovation Summit 2026",
        "Main summit on 25 March 2026 exploring generative, agentic, and physical AI in business; co-located AI for CFOs day on 24 March per organiser copy.",
        _dt(2026, 3, 25, 9, 0),
        _dt(2026, 3, 25, 18, 0),
        "Convene 155 Bishopsgate, London EC2M 3YD",
        extra_notes={"colocated": "AI for CFOs Summit on 24 March 2026."},
    ),
    _ev(
        "https://events.economist.com/physical-ai-and-robotics-summit/",
        "Economist Impact — Physical AI and Robotics Summit 2026",
        "In-person executive summit on deploying robotics and physical AI at scale: operations, economics, regulation, and labour-market implications.",
        _dt(2026, 10, 13, 9, 0),
        _dt(2026, 10, 13, 18, 0),
        "Convene 200 Aldersgate, 200 Aldersgate St, London EC1A 4HD",
    ),
    _ev(
        "https://womenindata.co.uk/women-in-data-flagship-2026/",
        "Women in Data Flagship 2026",
        "Flagship Women in Data conference for thousands of professionals across data, AI, and technology (balloted entry).",
        _dt(2026, 3, 26, 9, 0),
        _dt(2026, 3, 26, 18, 0),
        "InterContinental London – The O2, 1 Waterview Dr, London SE10 0TW",
    ),
    _ev(
        "https://rsvp.servicenow.com/ukpssummitlondon",
        "ServiceNow UK Public Services Summit — London 2026",
        "Full-day summit for UK public-sector leaders on delivering AI and digital transformation in government, health, local government, and education.",
        _dt(2026, 5, 12, 8, 45),
        _dt(2026, 5, 12, 17, 30),
        "Royal Lancaster London, Lancaster Terrace, London W2 2TY",
    ),
    _ev(
        "https://www.servicenow.com/events/world-forum/london.html",
        "ServiceNow World Forum — London 2026",
        "Annual World Forum for AI and ServiceNow customers and partners (date per UK Public Services RSVP hub; london.html currently highlights the prior year’s recap).",
        _dt(2026, 10, 30, 8, 30),
        _dt(2026, 10, 30, 18, 30),
        "ExCeL London",
        extra_notes={
            "source_note": "World Forum date taken from rsvp.servicenow.com ukpssummitlondon sidebar; confirm when global registration opens."
        },
    ),
    _ev(
        "https://blackhat.com/eu-26/",
        "Black Hat Europe 2026",
        "Black Hat Europe briefings and trainings at ExCeL London (seed path eu-26 may 404; dates from blackhat.com/upcoming).",
        _dt(2026, 12, 7, 9, 0),
        _dt(2026, 12, 10, 18, 0),
        "ExCeL London",
        extra_notes={"url_note": "Official calendar lists Black Hat Europe 2026 7–10 Dec at ExCeL London."},
    ),
    _ev(
        "https://aimagazine.com/events/tech-and-ai-live/ai-live-london-summit-2026",
        "AI LIVE: The London Summit 2026",
        "Two-day conference and expo on enterprise AI, automation, governance, identity, and transformation with executive workshops and immersive demos.",
        _dt(2026, 10, 20, 9, 0),
        _dt(2026, 10, 21, 18, 0),
        "Olympia London",
    ),
    _ev(
        "https://dtxevents.io/london/",
        "DTX London 2026",
        "Two-day expo on digital and business transformation (AI, cyber, data, automation), co-located with UCX at ExCeL London.",
        _dt(2026, 10, 14, 9, 0),
        _dt(2026, 10, 15, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://ucxevents.io/london/",
        "UCX London 2026",
        "Unified communications and customer experience technology expo co-located with DTX at ExCeL London.",
        _dt(2026, 10, 14, 9, 0),
        _dt(2026, 10, 15, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://irmuk.co.uk/data-ai-conference-2026/",
        "Data & AI Conference Europe 2026 (IRM UK)",
        "Five-day IRM programme: workshops 2, 5 & 6 November; conference and exhibition 3–4 November at etc.venues Fenchurch Street.",
        _dt(2026, 11, 2, 9, 0),
        _dt(2026, 11, 6, 18, 0),
        "etc.venues Fenchurch Street, 8 Fenchurch Pl, London",
    ),
    _ev(
        "https://irmuk.co.uk/dg-ai-governance-conference/",
        "Data Governance, AI Governance & MDM Conference Europe 2026 (IRM UK)",
        "Five-day IRM programme: conference and exhibits 23–24 March at Convene 133 Houndsditch; workshops 25–27 March at etc.venues Fenchurch Street.",
        _dt(2026, 3, 23, 9, 0),
        _dt(2026, 3, 27, 18, 0),
        "Convene 133 Houndsditch, London (workshops: etc.venues Fenchurch Street)",
    ),
    _ev(
        "https://www.cloudtransformationconference.com/global/en-gb/",
        "Cloud Transformation Expo Global — London 2026",
        "Cloud and digital transformation track co-located with TechEx Global (shared Olympia pass with Cyber Security & Cloud, AI & Big Data, IoT, and related expos).",
        _dt(2026, 2, 4, 9, 0),
        _dt(2026, 2, 5, 16, 0),
        "Olympia London – The Grand",
    ),
    _ev(
        "https://www.digicatapult.org.uk/apply/events/advice-annual-summit-2026/",
        "ADViCE Annual Summit 2026",
        "Half-day summit on AI for decarbonisation hosted by Digital Catapult with Energy Systems Catapult and The Alan Turing Institute: keynotes, lightning talks, and demos.",
        _dt(2026, 4, 29, 10, 0),
        _dt(2026, 4, 29, 13, 30),
        "Digital Catapult, London",
    ),
    _ev(
        "https://www.legalgeek.co/conference/",
        "Legal Geek Conference 2026",
        "Two-day legal technology and innovation conference: TED-style talks, workshops, roundtables, and networking.",
        _dt(2026, 10, 14, 9, 0),
        _dt(2026, 10, 15, 18, 0),
        "The Old Truman Brewery, 15 Hanbury St, London E1 6QR",
    ),
    _ev(
        "https://stateofopencon.com/",
        "State of Open Conference — London 2027",
        "Open technology conference series; London dates listed for 2027 (2026 editions include Edinburgh and Cambridge per organiser homepage).",
        _dt(2027, 2, 9, 9, 0),
        _dt(2027, 2, 10, 18, 0),
        "London (venue TBC)",
        extra_notes={"series_note": "Homepage: Edinburgh 5 Jun 2026, Cambridge 8 Jul 2026; London 9–10 Feb 2027."},
    ),
    _ev(
        "https://www.techexevent.com/global/",
        "TechEx Global 2026 — London",
        "Two-day co-located enterprise technology festival at Olympia (AI & Big Data, Intelligent Automation, Cyber Security & Cloud, IoT, Digital Transformation, Edge, and more).",
        _dt(2026, 2, 4, 9, 0),
        _dt(2026, 2, 5, 16, 0),
        "Olympia London – The Grand",
        extra_notes={"hours_note": "Exhibitor hub lists visitor access 09:00–16:00 and setup day 3 Feb."},
    ),
]


def main() -> None:
    assert len(EVENTS) == 40, len(EVENTS)
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
