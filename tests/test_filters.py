"""Contract tests: keyword + London gating (helpers tested separately)."""

from __future__ import annotations

from datetime import datetime

import pytest

from ai_events.filters import (
    passes_beginner_audience,
    passes_business_and_ai_keywords,
    passes_consumer_ai_hustle,
    passes_enterprise_ai,
    passes_founders_executives_tech_leaders,
    passes_hustle_pitch,
    passes_ic_hackathon_research_audience,
    passes_in_person,
    passes_london,
    should_keep,
    should_keep_techuk_ai,
)
from ai_events.models import RawEvent


def _ev(
    *,
    title: str,
    description: str | None = None,
    venue: str | None = None,
    city: str | None = None,
    country: str | None = None,
    is_in_person: bool | None = True,
    url: str = "https://example.com/e/1",
) -> RawEvent:
    return RawEvent(
        source="test",
        url=url,
        title=title,
        description=description,
        starts_at=datetime(2026, 6, 1, 9, 0, 0),
        ends_at=None,
        venue=venue,
        city=city,
        country=country,
        is_in_person=is_in_person,
        attendance_mode_uri="https://schema.org/OfflineEventAttendanceMode",
    )


@pytest.mark.parametrize(
    "title,desc,expect",
    [
        ("Enterprise AI Forum", None, True),
        ("GenAI breakfast", "LLM deployment", True),
        ("CIO roundtable on governance", None, True),
        ("Football in the park", None, False),
        ("Networking mixer", "drinks only", False),
    ],
)
def test_passes_enterprise_ai(title: str, desc: str | None, expect: bool) -> None:
    text = f"{title}\n{desc or ''}"
    assert passes_enterprise_ai(text) is expect


@pytest.mark.parametrize(
    "title,desc,expect",
    [
        ("Enterprise breakfast", "Claude tooling for teams", True),
        ("Startup pitch night", "machine learning track", True),
        ("Company offsite", "yoga and hiking", False),
        ("AI meetup", "discuss agents", False),
        ("London social", "networking for founders", False),
        ("Side income with AI", "business growth in London", False),
        ("LLM night for developers", "embeddings and RAG", False),
        ("Generative AI for beginners", "No prior experience required", False),
        ("Enterprise MLOps meetup", "Advanced RAG patterns", True),
        ("Founders AI salon", "generative AI and GTM", True),
        ("RAG deep dive", "for software engineers", False),
        ("Research symposium on LLMs", "call for papers", False),
        ("AI hackathon", "build with GPT", False),
        ("C-suite breakfast", "generative AI strategy", True),
        (
            "Build Your First Successful AI SaaS Startup Today! - Workshop",
            "generative AI",
            False,
        ),
        (
            "Launch Your Own Successful AI App | AI Startup | Workshop 2026",
            "machine learning",
            False,
        ),
        (
            "Viral Content Faceless AI - Income Strategy Workshop",
            "ChatGPT automation",
            False,
        ),
        ("Building Your First GenAI Solution", "workshop for teams", False),
        (
            "How to Go From Raw Idea to Polished Pitch using AI",
            "generative AI",
            False,
        ),
        ("AI Leadership for Marketing Experts", "generative AI for CMOs", False),
        (
            "Build Enterprise Worthy LLM Inference with Open Source and Kubernetes",
            "AI technical",
            False,
        ),
    ],
)
def test_passes_business_and_ai_keywords(
    title: str, desc: str | None, expect: bool
) -> None:
    ev = _ev(title=title, description=desc, venue=None, city="London")
    assert passes_business_and_ai_keywords(ev) is expect


def test_passes_consumer_ai_hustle_detects() -> None:
    ev = _ev(
        title="Launch your own AI app workshop",
        description="startup",
        city="London",
    )
    assert passes_consumer_ai_hustle(ev) is True


def test_ic_hackathon_research_detects() -> None:
    ev = _ev(title="ML for researchers", description="LLM papers", city="London")
    assert passes_ic_hackathon_research_audience(ev) is True


def test_founders_executives_signal() -> None:
    ev = _ev(title="Plain AI", description="agents only", city="London")
    assert passes_founders_executives_tech_leaders(ev) is False
    ev2 = _ev(title="Founder AI dinner", description="LLM strategy", city="London")
    assert passes_founders_executives_tech_leaders(ev2) is True


def test_passes_hustle_pitch_detects_spam() -> None:
    ev = _ev(
        title="Passive income with ChatGPT",
        description="Six figures from home",
        city="London",
    )
    assert passes_hustle_pitch(ev) is True


def test_passes_beginner_audience_detects() -> None:
    ev = _ev(
        title="AI 101 for newcomers",
        description="Absolute beginner friendly. No prior experience.",
        city="London",
    )
    assert passes_beginner_audience(ev) is True


def test_should_keep_rejects_beginner_even_when_london() -> None:
    ev = _ev(
        title="Intro to LLMs for beginners",
        description="Entry level workshop for your company.",
        city="London",
        venue="Shoreditch, London",
    )
    assert should_keep(ev) is False


@pytest.mark.parametrize(
    "venue,city,expect",
    [
        ("Shoreditch House, London", None, True),
        (None, "London", True),
        ("EC2A 3AY venue", None, True),
        ("Manchester Arena", "Manchester", False),
        ("UK wide", None, False),
    ],
)
def test_passes_london(venue: str | None, city: str | None, expect: bool) -> None:
    ev = _ev(title="Enterprise AI meetup", description="agents", venue=venue, city=city)
    assert passes_london(ev) is expect


@pytest.mark.parametrize(
    "is_ip,title,desc,expect",
    [
        (False, "AI in London", "x", False),
        (True, "AI in London", "x", True),
        (None, "AI London", "online only event", False),
    ],
)
def test_passes_in_person(
    is_ip: bool | None, title: str, desc: str, expect: bool
) -> None:
    ev = _ev(title=title, description=desc, is_in_person=is_ip)
    assert passes_in_person(ev) is expect


def test_should_keep_requires_business_ai_and_london() -> None:
    ev = _ev(
        title="Company AI breakfast",
        description="Machine learning for executives.",
        venue="Canary Wharf, London",
        city="London",
        is_in_person=True,
    )
    assert should_keep(ev) is True


def test_should_keep_rejects_non_ai_even_when_london() -> None:
    ev = _ev(
        title="Knitting circle",
        description="Bring wool — corporate sponsors welcome.",
        venue="Cafe in Shoreditch, London",
        city="London",
        is_in_person=True,
    )
    assert should_keep(ev) is False


def test_should_keep_rejects_hustle_even_when_london_and_keywords() -> None:
    ev = _ev(
        title="AI side hustle masterclass",
        description="Replace your income with generative AI funnels.",
        venue="Online, London",
        city="London",
    )
    assert should_keep(ev) is False


def test_should_keep_allows_online_when_london_and_keywords() -> None:
    ev = _ev(
        title="Enterprise AI Virtual",
        description="LLM webinar",
        venue="Online — audience in London",
        city="London",
        is_in_person=False,
    )
    assert should_keep(ev) is True


def test_should_reject_without_london_signal() -> None:
    ev = _ev(
        title="Enterprise AI strategy",
        description="generative AI for leadership",
        venue="Leeds",
        city="Leeds",
        is_in_person=True,
    )
    assert should_keep(ev) is False


def test_should_keep_without_london_when_opted_out_still_needs_ai_signal() -> None:
    ev = _ev(
        title="Summer picnic",
        description="Sandwiches and games.",
        venue="Leeds",
        city="Leeds",
        is_in_person=True,
    )
    assert should_keep(ev, require_london=False) is False


def test_should_keep_without_london_when_keywords_present() -> None:
    ev = _ev(
        title="Startup ML night",
        description="Business networking and machine learning.",
        venue="Leeds",
        city="Leeds",
        is_in_person=True,
    )
    assert should_keep(ev, require_london=False) is True


def test_should_keep_techuk_ai_only_needs_ai_and_london() -> None:
    ev = _ev(
        title="Sector roundtable",
        description="Discussion of machine learning adoption.",
        venue="Westminster, London",
        city="London",
    )
    assert should_keep_techuk_ai(ev) is True


def test_should_keep_techuk_ai_rejects_without_ai_signal() -> None:
    ev = _ev(
        title="Digital policy breakfast",
        description="Regulation and compliance.",
        venue="London",
        city="London",
    )
    assert should_keep_techuk_ai(ev) is False


def test_should_keep_techuk_ai_rejects_non_london() -> None:
    ev = _ev(
        title="AI governance forum",
        description="generative AI in the public sector",
        venue="Birmingham",
        city="Birmingham",
    )
    assert should_keep_techuk_ai(ev) is False


def test_should_keep_exec_roundtable_without_london() -> None:
    ev = _ev(
        title="Executive AI roundtable",
        description="Open discussion on LLMs.",
        venue="Leeds",
        city="Leeds",
    )
    assert should_keep(ev, require_london=False) is True
