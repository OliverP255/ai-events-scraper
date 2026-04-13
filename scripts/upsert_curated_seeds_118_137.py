"""Curated upsert for seeds/search_curated_from_web.txt lines 118–137 (next 20 after line 117)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ai_events.models import RawEvent
from ai_events.pg_connect import connect_psycopg
from ai_events.storage import dedupe_events_by_normalized_url, upsert_event

LON = ZoneInfo("Europe/London")
BATCH = "search_curated_from_web_urls_118_137"


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
        "https://www.technologyformarketing.co.uk/",
        "Technology for Marketing 2026",
        "UK marketing and MarTech exhibition and conference (CPD-accredited content), co-located with eCommerce Expo and related shows at ExCeL — themes include AI, automation, and customer data.",
        _dt(2026, 9, 23, 9, 0),
        _dt(2026, 9, 24, 18, 0),
        "ExCeL London",
        extra_notes={"hours_note": "Standard trade-show window assumed; confirm opening times in exhibitor/delegate comms."},
    ),
    _ev(
        "https://uk.bettshow.com",
        "Bett UK 2027",
        "World-leading education technology show: exhibitors, stages, CPD content, and networking for schools, HE, government, and EdTech (site advertises 20–22 January 2027 at ExCeL).",
        _dt(2027, 1, 20, 9, 0),
        _dt(2027, 1, 22, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://www.proptechshow.com/",
        "London PropTech Show 2026",
        "Third annual European proptech trade show and conference covering AI, smart buildings, investment, regulation, and digital transformation in real estate.",
        _dt(2026, 3, 24, 9, 0),
        _dt(2026, 3, 25, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://www.cogxleadershipsummit.com/",
        "CogX (Studios, Salons, Awards & Labs)",
        "CogX now runs as distributed programming: Studios (digital shows), invitation-only Salons, Awards, and Labs rather than a single dated London mega-festival. There is no one public London date on this hub page.",
        None,
        None,
        None,
        extra_notes={"format_note": "See cogxleadershipsummit.com for Salon/Awards/Labs participation; no flagship London summit dates listed for 2026."},
    ),
    _ev(
        "https://ai-uk.turing.ac.uk/",
        "AI UK (programme hub)",
        "Official web hub for AI UK, The Alan Turing Institute’s national showcase of UK data science and AI. The institute’s public listing does not currently confirm a 2026 edition date on pages we could retrieve; check the hub for the next announced dates.",
        None,
        None,
        None,
        extra_notes={"date_note": "Primary site often behind Cloudflare; no verified 2026 start/end from official crawl."},
    ),
    _ev(
        "https://www.turing.ac.uk/events/ai-science",
        "AI for Science Conference 2026",
        "One-day Turing Institute conference on AI transforming scientific discovery: physical systems, simulation, climate, materials, fusion, and trustworthy AI (partner listing includes full timings).",
        _dt(2026, 3, 31, 9, 15),
        _dt(2026, 3, 31, 18, 30),
        "The Royal Society, London",
        extra_notes={"partner_times": "Times confirmed via University of Cambridge C2D3 partner event listing for the same conference."},
    ),
    _ev(
        "https://cdao-uk.coriniumintelligence.com/",
        "CDAO UK",
        "Two-day senior forum for CDOs and data & analytics leaders on governance, AI, data strategy, and business impact. Organiser homepage advertises the next London edition in February 2027 without specific days at time of research.",
        None,
        None,
        "London",
        extra_notes={"date_note": "Site header: February 2027, London — confirm days when Corinium publishes the 2027 agenda."},
    ),
    _ev(
        "https://www.inspiredbusinessmedia.com/summit/cdo-inspired-summit-uk-2026-october",
        "CDO Inspired Summit UK — October 2026",
        "Summit for CDOs and data leaders on data-driven innovation, analytics, and AI integration. Page lists20 October 2026 at Syon Park (body copy incorrectly references March/two days in one paragraph).",
        _dt(2026, 10, 20, 9, 0),
        _dt(2026, 10, 20, 18, 0),
        "Syon Park, London",
        extra_notes={"copy_warning": "Hero date is 20 Oct 2026; ignore erroneous 'March' two-day sentence in mid-page marketing copy."},
    ),
    _ev(
        "https://festivalofgenomics.com/london/",
        "Festival of Genomics & Biodata London 2027",
        "UK life-sciences festival spanning genomics, biodata, AI in diagnostics, drug discovery, and multi-omics, with large free-delegate programme.",
        _dt(2027, 1, 27, 9, 0),
        _dt(2027, 1, 28, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://informaconnect.com/quantminds-international/",
        "QuantMinds International 2026",
        "Flagship quant finance conference with summits and workshops on derivatives, portfolio construction, machine learning in finance, and innovation (co-located networking with RiskMinds).",
        _dt(2026, 11, 16, 9, 0),
        _dt(2026, 11, 19, 18, 0),
        "InterContinental London – The O2",
    ),
    _ev(
        "https://informaconnect.com/riskminds-international/",
        "RiskMinds International 2026",
        "Global risk management conference for financial institutions: regulation, climate risk, cyber and AI resilience, liquidity, and conduct — runs alongside QuantMinds at the InterContinental O2.",
        _dt(2026, 11, 16, 9, 0),
        _dt(2026, 11, 19, 18, 0),
        "InterContinental London – The O2",
    ),
    _ev(
        "https://europe.risklive.net/",
        "Risk Live Europe 2026",
        "Risk.net festival for CROs and senior risk leaders: 30 June–1 July 2026 conference & exhibition at InterContinental O2 (29 June invite-only Leaders’ Forum per organiser copy).",
        _dt(2026, 6, 30, 9, 0),
        _dt(2026, 7, 1, 18, 0),
        "InterContinental London – The O2",
        extra_notes={"leaders_day": "29 June 2026: invite-only Leaders’ Forum and reception."},
    ),
    _ev(
        "https://solutions.lseg.com/Quant_Summit_London_2026",
        "LSEG Quant Summit London 2026",
        "Full day hosted by LSEG Post Trade Solutions: morning ORE/Risk Analytics Lab masterclass and afternoon Quant Summit on open-source risk, XVA/SIMM, AI in quant, and networking reception.",
        _dt(2026, 5, 11, 9, 30),
        _dt(2026, 5, 11, 19, 0),
        "LSEG, 10 Paternoster Square, London EC4M 7LS",
        extra_notes={"agenda_note": "Published agenda: sessions to 17:00, networking reception until 19:00."},
    ),
    _ev(
        "https://www.arena-international.com/event/digital-insurance/",
        "11th Annual Digital Transformation in Insurance Conference 2026",
        "Two-day insurer-focused conference on digital operating models, data, AI, security, and workforce change (agenda timestamps from organiser).",
        _dt(2026, 5, 19, 9, 0),
        _dt(2026, 5, 20, 18, 0),
        "Hilton London Bankside",
    ),
    _ev(
        "https://www.insurance-innovators.com/events/summit/",
        "Insurance Innovators Summit 2026",
        "Large insurance and insurtech leadership conference with multi-stage content on AI, transformation, claims, cyber, and distribution.",
        _dt(2026, 11, 3, 9, 0),
        _dt(2026, 11, 4, 18, 0),
        "Business Design Centre, London",
    ),
    _ev(
        "https://innovation.globalgovernmentforum.com/",
        "Global Government Forum Innovation 2027",
        "Civil-service innovation conference (Excel London). Site thanks delegates for Innovation 2026 and promotes Innovation 2027 on16–17 March 2027.",
        _dt(2027, 3, 16, 9, 0),
        _dt(2027, 3, 17, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://www.digital-government.co.uk/",
        "DigiGov Expo 2026",
        "UK public-sector technology exhibition and conference: six theatres, government village, and supplier showcase (timings on site).",
        _dt(2026, 9, 23, 9, 30),
        _dt(2026, 9, 24, 16, 45),
        "ExCeL London",
    ),
    _ev(
        "https://www.govtechsummit.eu/",
        "The GovTech Summit 2026",
        "Curated one-day summit connecting senior government decision-makers with tech founders and investors — AI implementation, procurement, health, and local government themes.",
        _dt(2026, 4, 16, 9, 0),
        _dt(2026, 4, 16, 18, 0),
        "Central Hall Westminster, London",
        extra_notes={"hours_note": "Day schedule not fully timed on hero page; end time assumed standard conference day."},
    ),
    _ev(
        "https://www.hettshow.co.uk/",
        "HETT Show 2026",
        "Healthcare technology and digital transformation expo for NHS and public-sector health audiences (CPD-certified streams).",
        _dt(2026, 9, 29, 9, 0),
        _dt(2026, 9, 30, 18, 0),
        "ExCeL London",
    ),
    _ev(
        "https://www.techuk.org/what-we-deliver/events/tech-policy-conference-2026.html",
        "techUK Tech Policy Conference 2026",
        "Flagship UK tech policy conference bringing together Westminster, Whitehall, regulators, and industry on competitiveness, AI adoption, digital ID, and sovereignty.",
        _dt(2026, 3, 16, 9, 0),
        _dt(2026, 3, 16, 17, 30),
        "London",
        extra_notes={"venue_note": "Page states London; detailed venue on registration materials."},
    ),
]


def main() -> None:
    assert len(EVENTS) == 20, len(EVENTS)
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
