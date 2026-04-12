"""
Batch enterprise-AI relevance classification via a local OpenAI-compatible LLM (e.g. Ollama).

When ``ENTERPRISE_LLM_ENABLED`` is unset or false, the LLM step is **skipped** and candidates
pass through unchanged. Set to ``1`` / ``true`` to enable (requires a local OpenAI-compatible server).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import httpx

from ai_events.models import RawEvent
from ai_events.webapp.settings import load_env

BATCH_SIZE = 5
_DEFAULT_BASE = "http://127.0.0.1:11434/v1"
_DEFAULT_MODEL = "llama3.2"
_MAX_DESC_CHARS = 6000

_SYSTEM_PROMPT = """You label events for an enterprise-AI calendar (UK/London). Each event gets 1 (keep) or 0 (drop).

Use 1 only when BOTH:
(1) Audience is clearly senior/organizational decision-makers or their peers: CIO/CISO/CTO/CHRO/CRO, board/NED, VP/director/head of, partners at law/accounting firms, industry councils, PE/VC professionals on AI deals, invitation-only enterprise briefings. Internal company launches of a sanctioned enterprise AI tool for employees count as 1.
(2) The core topic is applied AI/ML in business: GenAI/LLMs, RAG, copilots, MLOps in production, governance/risk, regulated banking/insurance/pharma AI, retail/industrial ML, workforce analytics with ML — not "digital" or "cloud" alone.

Use 0 if the PRIMARY draw is any of: students or hackathons/buildathons; PhD/academic/CFP research; hobby AI art or Midjourney "fun"; creators/TikTok/YouTube income; side-hustle/prompt-to-profit; kids' coding; career fairs; pure K8s/devops/FOSS nights with no AI topic; dating/consumer founder parties; wellness retreats; tarot/novelty; mass-market beginner webinars; generic IT expos where AI is not central.

If unsure between 1 and 0: choose 0.

Calibration (same rules — short examples):
• CIO / CISO / council + GenAI or governance in regulated firms → 1
• Executive breakfast / NED briefing / CHRO forum + copilots, analytics ML, or enterprise AI → 1
• Partners + RAG/enterprise search; PE/VC + portfolio AI; internal sanctioned copilot launch → 1
• Student hackathon; kids coding camp; AI art hobby night; K8s with no ML; Rust OSS night; faceless-YouTube hustle; creator TikTok tips; wellness + gimmick AI → 0

The user message lists events as "### Event 0", "### Event 1", … in order. Your JSON labels array must have EXACTLY that many entries (same count as events). First label = Event 0, second = Event 1, etc.

Output ONLY one JSON object, no markdown fences, no words before or after:
{"labels":[0,1,...]}"""


def _user_classify_message(n: int, batch_body: str) -> str:
    return (
        f"There are exactly {n} events below (### Event 0 … ### Event {n - 1}). "
        f'Output only one JSON object: {{"labels": [<{n} integers, each 0 or 1>]}} in the same order.\n\n'
        + batch_body
    )


def _env_truthy(name: str, default: bool = False) -> bool:
    load_env()
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def enterprise_llm_enabled() -> bool:
    """Off unless ``ENTERPRISE_LLM_ENABLED`` is ``1`` / ``true`` / ``yes`` / ``on``."""
    return _env_truthy("ENTERPRISE_LLM_ENABLED", default=False)


def _base_url() -> str:
    load_env()
    return (os.environ.get("ENTERPRISE_LLM_BASE_URL") or _DEFAULT_BASE).rstrip("/")


def _model() -> str:
    load_env()
    return (os.environ.get("ENTERPRISE_LLM_MODEL") or _DEFAULT_MODEL).strip()


def _api_key() -> str | None:
    load_env()
    k = os.environ.get("ENTERPRISE_LLM_API_KEY", "").strip()
    return k or None


def _timeout_s() -> float:
    load_env()
    try:
        return float(os.environ.get("ENTERPRISE_LLM_TIMEOUT", "120"))
    except ValueError:
        return 120.0


def _strip_html(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", t).strip()


def _snippet(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    s = _strip_html(text) if "<" in text else text.strip()
    if len(s) > max_chars:
        return s[: max_chars - 1].rstrip() + "…"
    return s


def _format_batch(events: list[RawEvent]) -> str:
    parts: list[str] = []
    for i, ev in enumerate(events):
        title = (ev.title or "").strip() or "(no title)"
        desc = _snippet(ev.description, _MAX_DESC_CHARS)
        parts.append(f"### Event {i}\nTitle: {title}\nDescription: {desc}\n")
    return "\n".join(parts)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse first JSON object from model output (tolerates markdown fences and prefix text)."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    dec = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(s[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _labels_from_response(content: str, n: int) -> list[int] | None:
    obj = _extract_json_object(content)
    if not obj:
        return None
    labels = obj.get("labels")
    if not isinstance(labels, list) or len(labels) != n:
        return None
    out: list[int] = []
    for x in labels:
        if x in (0, 1):
            out.append(int(x))
        elif x is True:
            out.append(1)
        elif x is False:
            out.append(0)
        else:
            return None
    return out


def _chat_completions(
    client: httpx.Client,
    *,
    user_content: str,
) -> str:
    url = f"{_base_url()}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body: dict[str, Any] = {
        "model": _model(),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }
    r = client.post(url, json=body, headers=headers, timeout=_timeout_s())
    r.raise_for_status()
    data = r.json()
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("missing choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise ValueError("missing message content")
    return content


def _classify_batch(client: httpx.Client, batch: list[RawEvent]) -> list[int] | None:
    n = len(batch)
    if n == 0:
        return []
    user_content = _user_classify_message(n, _format_batch(batch))
    last_err: str | None = None
    for attempt in range(2):
        try:
            content = _chat_completions(client, user_content=user_content)
            labels = _labels_from_response(content, n)
            if labels is not None:
                return labels
            last_err = "parse or length mismatch"
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as e:
            last_err = str(e)
    print(f"enterprise_llm: batch failed after retry: {last_err}", file=sys.stderr)
    return None


def filter_enterprise_events(
    client: httpx.Client,
    candidates: list[RawEvent],
    *,
    enabled: bool | None = None,
) -> list[RawEvent]:
    """
    Keep only events the LLM labels as 1. Batches of :const:`BATCH_SIZE`.

    If ``enabled`` is False, returns ``candidates`` unchanged.
    If ``enabled`` is None, uses ``ENTERPRISE_LLM_ENABLED`` (defaults to off).
    On API/parse failure for a batch, that batch is dropped (nothing from it is kept).
    """
    if enabled is False:
        return list(candidates)
    if enabled is None:
        enabled = enterprise_llm_enabled()
    if not enabled:
        return list(candidates)
    if not candidates:
        return []

    kept: list[RawEvent] = []
    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i : i + BATCH_SIZE]
        labels = _classify_batch(client, batch)
        if labels is None:
            continue
        for ev, lab in zip(batch, labels, strict=True):
            if lab == 1:
                kept.append(ev)
    return kept
