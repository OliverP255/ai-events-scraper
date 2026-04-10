from __future__ import annotations

import re

from ai_events.models import RawEvent

# --- Disabled for now (re-enable in should_keep one at a time) -----------------
# Broad "enterprise / workplace AI" signals (title + description).
_ENTERPRISE_AI = re.compile(
    r"\b("
    r"enterprise|b2b|business\s+ai|workplace|corporate|"
    r"chief\s+information|cio\b|ciso\b|cto\b|"
    r"generative\s+ai|gen\s*ai|llm\b|large\s+language|"
    r"machine\s+learning|\bmlops\b|"
    r"artificial\s+intelligence|\bai\b|"
    r"governance|responsible\s+ai|"
    r"agentic|copilot|automation|"
    r"data\s+science|analytics"
    r")\b",
    re.I,
)
# ------------------------------------------------------------------------------


_LONDON = re.compile(
    r"\b("
    r"london|greater\s+london|"
    r"ec[1-4][a-z]?\b|wc[12][a-z]?\b|sw1[a-z]\b|"
    r"e1[0-9a-z]{1,2}\b|w1[0-9a-z]{1,2}\b|"
    r"city\s+of\s+london|canary\s+wharf|shoreditch|westminster"
    r")\b",
    re.I,
)

# Income-pitch / MLM-style webinars (reject if matched).
_HUSTLE_PITCH = re.compile(
    r"(?:"
    r"side\s*hustle|side\s+income|passive\s+income|"
    r"financial\s+freedom|replace\s+your\s+(?:income|salary|job)|"
    r"quit\s+your\s+(?:job|9\s*-?\s*5)|"
    r"\b(?:six|seven)\s*[- ]?\s*figures?\b|"
    r"make\s+money\s+(?:online|with\s+ai|from\s+ai)|"
    r"earn\s+(?:£|\$|€)?\s*[\d,]+\s*(?:per|a\s+)?(?:day|week|month)|"
    r"unlimited\s+income|income\s+potential|"
    r"affiliate\s+(?:marketing|program)|dropship(?:ping)?|"
    r"masterclass\s+for\s+(?:beginners\s+)?(?:to\s+)?(?:launch|build|scale)\s+(?:your\s+)?(?:business|income)"
    r")",
    re.I,
)

# Explicitly beginner / zero-prior-experience audience (reject if matched).
_BEGINNER_AUDIENCE = re.compile(
    r"(?:"
    r"\bbeginners?\b|"
    r"\bnewbies?\b|\bnewcomers?\b|"
    r"first[\s-]timers?\b|"
    r"\bno\s+prior\s+experience\b|"
    r"\bno\s+experience\s+(?:required|necessary|needed)\b|"
    r"\bzero\s+(?:prior\s+)?(?:coding\s+)?experience\b|"
    r"\bnever\s+(?:coded|programmed)\s+before\b|"
    r"\babsolute\s+beginner\b|"
    r"\bintro\s+level\b|"
    r"\bentry[\s-]level\b|"
    r"\b101\s+series\b|"
    r"\bfor\s+beginners\b"
    r")",
    re.I,
)

_BUSINESS_CONTEXT = re.compile(
    r"\b("
    r"enterprise|business|company|startup|corporate|b2b|workplace|"
    r"organisation|organization|founders?|commercial|scale-?ups?|\bsme\b|"
    r"firm|c-?suite|executives?|industry|industries|employers?|"
    r"ventures?"
    r")\b",
    re.I,
)

# Engineers, research, product — events that are "serious" but not always "business".
_PROFESSIONAL_CONTEXT = re.compile(
    r"\b("
    r"developer|engineers?|engineering|research(?:er|ers)?|scientists?|"
    r"universit(?:y|ies)|academic|labs?|phd|papers?|"
    r"product|platform|infrastructures?|operations?|"
    r"governance|compliance|security|safety|responsible|"
    r"meetups?|community|workshops?|conferences?|summits?|"
    r"hackathons?|builders?|analytics|data\s+teams?|"
    r"open\s+source|oss\b"
    r")\b",
    re.I,
)

# Broad AI / ML signals (need at least one).
_AI_TECH = re.compile(
    r"(?:"
    r"\bAI\b|"
    r"\bML\b|"
    r"\bLLMs?\b|"
    r"\bGPT\b|"
    r"\bRAG\b|"
    r"machine\s+learning|"
    r"deep\s+learning|"
    r"neural\s+nets?|"
    r"\bclaude\b|\bopenclaw\b|"
    r"\bagents?\b|agentic|"
    r"gen\s*ai|generative\s+ai|"
    r"large\s+language|"
    r"embeddings?|vectors?|"
    r"transformers?|"
    r"\bMLOps\b|"
    r"fine[\s-]?tun(?:e|ing)|"
    r"artificial\s+intelligence"
    r")",
    re.I,
)

# Strong standalone signals — one hit is enough without business/professional words.
_STRONG_AI = re.compile(
    r"(?:"
    r"\b(?:gpt-?4|gpt-?3|gpt-?5|openai|anthropic)\b|"
    r"\blangchain\b|\bllama\b|"
    r"retrieval[\s-]augmented|"
    r"large\s+language\s+models?"
    r")",
    re.I,
)

# Count distinct AI-flavoured matches (two+ → community / deep-tech meetup without "business").
_AI_COUNT = re.compile(
    r"(?:\bAI\b|\bML\b|\bLLMs?\b|\bGPT\b|machine\s+learning|\bagents?\b|"
    r"generative\s+ai|gen\s*ai|neural|embeddings?|transformers?|claude|RAG\b)",
    re.I,
)


def _keyword_blob(ev: RawEvent) -> str:
    return " ".join(
        filter(
            None,
            [
                ev.title,
                ev.description or "",
                ev.venue or "",
                ev.city or "",
            ],
        )
    )


def passes_hustle_pitch(ev: RawEvent) -> bool:
    """True if copy looks like income / side-hustle spam (should reject)."""
    t = _keyword_blob(ev)
    return bool(_HUSTLE_PITCH.search(t))


def passes_beginner_audience(ev: RawEvent) -> bool:
    """True if copy targets beginners / no experience (should reject)."""
    t = _keyword_blob(ev)
    return bool(_BEGINNER_AUDIENCE.search(t))


def passes_business_and_ai_keywords(ev: RawEvent) -> bool:
    """
    Reject hustle pitches and beginner-only positioning; require AI signal; then
    business OR professional context, or strong / duplicate AI signals for pure-tech meetups.
    """
    t = _keyword_blob(ev)
    if len(t.strip()) < 3:
        return False
    if passes_hustle_pitch(ev):
        return False
    if passes_beginner_audience(ev):
        return False
    if not _AI_TECH.search(t):
        return False
    if _BUSINESS_CONTEXT.search(t) or _PROFESSIONAL_CONTEXT.search(t):
        return True
    if _STRONG_AI.search(t):
        return True
    if len(_AI_COUNT.findall(t)) >= 2:
        return True
    return False


def passes_enterprise_ai(text: str) -> bool:
    """Disabled in ``should_keep`` for now; kept for unit tests / future use."""
    t = (text or "").strip()
    if len(t) < 3:
        return False
    return bool(_ENTERPRISE_AI.search(t))


def passes_london(ev: RawEvent) -> bool:
    blob = " ".join(
        filter(
            None,
            [
                ev.title,
                ev.description or "",
                ev.venue or "",
                ev.city or "",
                ev.country or "",
            ],
        )
    )
    if _LONDON.search(blob):
        return True
    if ev.city and _LONDON.search(ev.city):
        return True
    if ev.venue and _LONDON.search(ev.venue):
        return True
    return False


def passes_in_person(ev: RawEvent) -> bool:
    """Disabled in ``should_keep`` for now; kept for unit tests / future use."""
    if ev.is_in_person is False:
        return False
    if ev.is_in_person is True:
        return True
    desc = (ev.description or "") + " " + (ev.title or "")
    if re.search(r"\b(online\s+only|virtual\s+only|zoom\s+only)\b", desc, re.I):
        return False
    if re.search(r"\bvirtual\s+location\b", desc, re.I):
        return False
    return True


def should_keep(ev: RawEvent, *, require_london: bool = True) -> bool:
    if not passes_business_and_ai_keywords(ev):
        return False
    if require_london and not passes_london(ev):
        return False
    # if not passes_in_person(ev):
    #     return False
    return True
