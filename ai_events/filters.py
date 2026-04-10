from __future__ import annotations

import re

from ai_events.models import RawEvent
from ai_events.pinned_dedupe import is_scraper_duplicate_of_pinned

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
    r"masterclass\s+for\s+(?:beginners\s+)?(?:to\s+)?(?:launch|build|scale)\s+(?:your\s+)?(?:business|income)|"
    r"prompt\s+to\s+profit|"
    r"\b(?:get\s+rich|get\s+paid)\s+with\s+ai\b"
    r")",
    re.I,
)

# Consumer “build my first SaaS / viral income” — not high-value enterprise AI (reject if matched).
_CONSUMER_AI_HUSTLE = re.compile(
    r"(?:"
    r"(?:build|building|create|creating)\s+your\s+first\b|"
    r"\byour\s+first\s+successful\b|"
    r"\blaunch\s+your\s+own\b|"
    r"\bviral\s+content\b|"
    r"\bfaceless\s+ai\b|"
    r"\bfaceless\b.*\b(?:ai|video|channel|youtube)\b|"
    r"\bincome\s+strategy\b|"
    r"\b(?:youtube|tiktok|instagram)\s+(?:automation|income|money)\b|"
    r"\braw\s+idea\b.*\bpitch\b|\bpolished\s+pitch\b|"
    r"\bgo\s+from\b.*\bidea\b.*\bpitch\b|"
    r"\bscale\s+your\s+brand\b|"
    r"\bsocial\s+media\b.*\b(?:networking|startups)\b|"
    r"\bcontent\s+creation\b.*\b(?:networking|marketing)\b|"
    r"\bnext[- ]?level\b.*\b(?:sales|social\s+media)\b|"
    r"\bmarketing\s+experts?\b|"
    r"\bglobal\s+virtual\s+networking\b"
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

# Targets IC technical roles, hackathons, or academic research — reject if matched.
_IC_HACK_RESEARCH_AUDIENCE = re.compile(
    r"(?:"
    r"\bhackathon\b|\bhackfest\b|\bcodefest\b|\bbuildathon\b|"
    r"\bfor\s+developers\b|\bdevelopers?\s+only\b|\bdev\s+meetup\b|\bdev\s+day\b|"
    r"\bsoftware\s+engineers?\b|\bml\s+engineers?\b|\bdata\s+engineers?\b|"
    r"\bfor\s+engineers\b|\bengineers?\s+only\b|\bprincipal\s+engineers?\b|"
    r"\bresearch\s+(?:seminar|symposium|track|day)\b|\bcall\s+for\s+papers\b|"
    r"\bfor\s+researchers\b|\bresearchers?\s+only\b|"
    r"\bacademic\s+conference\b|\bphd\s+students?\b|"
    r"\bcoding\s+workshop\b|\bhands[- ]on\s+coding\b|"
    r"\bopen\s+source\s+(?:night|meetup|contributors?)\b|"
    r"\bpython\b.*\bcoding\b|\bcoding\s*&\s*innovation\b|"
    r"\bcitizen\s+developers?\b|"
    r"\bkubernetes\b.*\b(?:llm|inference|gpu|mlops)\b|"
    r"\b(?:llm|gpu)\s+inference\b.*\bkubernetes\b|"
    r"\bopen\s+source\b.*\bkubernetes\b.*\b(?:inference|llm)\b"
    r")",
    re.I,
)

# Founders, execs, investors, GTM — at least one required after AI + exclusions.
_FOUNDER_EXEC_TECH_LEADER = re.compile(
    r"(?:"
    r"\bco?[- ]?founders?\b|\bfounders?\b|"
    r"\bstartup\b|\bscale[- ]?ups?\b|\bunicorns?\b|"
    r"\b(?:CEO|CFO|COO|CMO|CRO|CPO|CHRO|CTO|CIO|CDO)\b|"
    r"\benterprise\b|\bb2b\b|\bcorporate\b|"
    r"\bexecutives?\b|\bc-?suite\b|\bnon[- ]?exec\b|"
    r"\bleadership\b|\bleaders?\s+lunch\b|\bleaders?\s+dinner\b|\bleaders?\s+roundtable\b|"
    r"\bboard\b|\bdirector(?:s)?\s+(?:\&|and|,)?\s*(?:officers?|board)\b|"
    r"\b(?:vice[\s-])?president\b|\b(?:svp|evp)\b|\bvp\b|"
    r"\b(?:chief|head)\s+of\b|"
    r"\bmanaging\s+director\b|"
    r"\bventure\b|\binvestors?\b|\bangel\s+investors?\b|\bVCs?\b|\bLPs?\b|"
    r"\bgo[- ]?to[- ]?market\b|\bgtm\b|"
    r"\bcommercial\b|\brevenue\b|"
    r"\bproduct\s+(?:leader|strategy|leadership)\b|"
    r"\bstrategic\b|\bstrategy\b|\broundtable\b|\bsummit\b"
    r")",
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


def passes_consumer_ai_hustle(ev: RawEvent) -> bool:
    """True if copy looks like first-SaaS / viral-income / faceless-AI course spam (reject)."""
    t = _keyword_blob(ev)
    return bool(_CONSUMER_AI_HUSTLE.search(t))


def passes_beginner_audience(ev: RawEvent) -> bool:
    """True if copy targets beginners / no experience (should reject)."""
    t = _keyword_blob(ev)
    return bool(_BEGINNER_AUDIENCE.search(t))


def passes_ic_hackathon_research_audience(ev: RawEvent) -> bool:
    """True if copy targets developers, IC engineers, hackathons, or research (reject)."""
    t = _keyword_blob(ev)
    return bool(_IC_HACK_RESEARCH_AUDIENCE.search(t))


def passes_founders_executives_tech_leaders(ev: RawEvent) -> bool:
    """True if copy signals founders, execs, investors, or senior tech-business audience."""
    t = _keyword_blob(ev)
    return bool(_FOUNDER_EXEC_TECH_LEADER.search(t))


def passes_business_and_ai_keywords(ev: RawEvent) -> bool:
    """
    Reject hustle and beginner-only positioning; require AI signal; reject events
    aimed at developers, hackathons, or academic research; require founder / exec /
    investor / GTM-style audience signals.
    """
    t = _keyword_blob(ev)
    if len(t.strip()) < 3:
        return False
    if passes_hustle_pitch(ev):
        return False
    if passes_consumer_ai_hustle(ev):
        return False
    if passes_beginner_audience(ev):
        return False
    if not _AI_TECH.search(t):
        return False
    if passes_ic_hackathon_research_audience(ev):
        return False
    if not passes_founders_executives_tech_leaders(ev):
        return False
    return True


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
    if is_scraper_duplicate_of_pinned(ev):
        return False
    if not passes_business_and_ai_keywords(ev):
        return False
    if require_london and not passes_london(ev):
        return False
    # if not passes_in_person(ev):
    #     return False
    return True


def should_keep_techuk_ai(ev: RawEvent, *, require_london: bool = True) -> bool:
    """
    techUK listings are enterprise-oriented; only require AI/ML-related wording and London.
    """
    if is_scraper_duplicate_of_pinned(ev):
        return False
    t = _keyword_blob(ev)
    if len(t.strip()) < 3:
        return False
    if not _AI_TECH.search(t):
        return False
    if require_london and not passes_london(ev):
        return False
    return True
