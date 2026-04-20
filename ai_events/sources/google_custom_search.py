"""Google Custom Search API for event discovery."""

from __future__ import annotations

import sys
from typing import Any, Sequence
from urllib.parse import urlencode

import httpx
from psycopg import Connection

from ai_events.enterprise_llm import filter_enterprise_events
from ai_events.filters import should_keep
from ai_events.models import RawEvent, raw_from_parsed
from ai_events.schema_ld import best_event_dict
from ai_events.storage import _norm_url, upsert_event
from ai_events.webapp.settings import google_search_api_key, google_search_engine_id

# Hosts to skip (not event pages)
_SKIP_HOST_SUBSTR = (
    "google.",
    "gstatic.",
    "youtube.",
    "youtu.be",
    "facebook.",
    "fb.com",
    "instagram.",
    "tiktok.",
    "wikipedia.org",
    "linkedin.com",
    "twitter.com",
    "x.com",
)


def _host_ok(url: str) -> bool:
    try:
        from urllib.parse import urlparse

        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    return not any(s in host for s in _SKIP_HOST_SUBSTR)


def _unique_urls(urls: list[str], cap: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        u = u.strip()
        if not u.startswith("http"):
            continue
        nu = _norm_url(u)
        if nu in seen or not _host_ok(nu):
            continue
        seen.add(nu)
        out.append(nu)
        if len(out) >= cap:
            break
    return out


def discover_urls_google_cse(
    client: httpx.Client, query: str, *, max_urls: int = 10
) -> list[str]:
    """
    Call Google Custom Search API and extract result URLs.

    Returns empty list if API key/engine ID not configured or on error.
    """
    api_key = google_search_api_key()
    engine_id = google_search_engine_id()
    if not api_key or not engine_id:
        return []

    # CSE allows max 10 results per request; use pagination if needed
    urls: list[str] = []
    start = 1
    while len(urls) < max_urls:
        params = {
            "key": api_key,
            "cx": engine_id,
            "q": query,
            "num": min(10, max_urls - len(urls)),
            "start": start,
        }
        url = f"https://www.googleapis.com/customsearch/v1?{urlencode(params)}"
        try:
            r = client.get(url, timeout=15.0)
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError, TypeError) as e:
            print(
                f"google_custom_search: API error for query '{query}': {e}",
                file=sys.stderr,
            )
            break

        items = data.get("items") or []
        for item in items:
            link = item.get("link")
            if isinstance(link, str) and link.startswith("http"):
                urls.append(link)

        # Check for next page
        queries = data.get("queries") or {}
        next_page = queries.get("nextPage") or []
        if not next_page:
            break
        start = next_page[0].get("startIndex", start + 10)
        if start > 91:  # CSE max is 100 results (10 pages)
            break

    return _unique_urls(urls, max_urls)


def _raw_event_preview(ev: RawEvent) -> dict[str, Any]:
    desc = ev.description
    if desc and len(desc) > 800:
        desc = desc[:799].rstrip() + "..."
    return {
        "source": ev.source,
        "url": ev.url,
        "title": ev.title,
        "description": desc,
        "starts_at": ev.starts_at.isoformat() if ev.starts_at else None,
        "ends_at": ev.ends_at.isoformat() if ev.ends_at else None,
        "venue": ev.venue,
        "city": ev.city,
        "country": ev.country,
        "is_in_person": ev.is_in_person,
        "extra": ev.extra,
    }


def google_cse_gather(
    client: httpx.Client,
    *,
    source: str,
    queries: Sequence[str],
    max_urls_per_query: int = 10,
    max_fetch_total: int = 72,
) -> tuple[int, list[str], list[dict[str, Any]], list[RawEvent]]:
    """
    Run Google Custom Search discovery and page fetches.

    Returns:
        queries_executed, unique_urls, one dict per URL attempt, keyword-filter candidates.
    """
    if not google_search_api_key() or not google_search_engine_id():
        print(
            "google_custom_search: GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_ENGINE_ID not set",
            file=sys.stderr,
        )
        return 0, [], [], []

    all_urls: list[str] = []
    seen_q: set[str] = set()
    queries_executed = 0

    for q in queries:
        q = (q or "").strip()
        if not q or q in seen_q:
            continue
        seen_q.add(q)
        queries_executed += 1
        batch = discover_urls_google_cse(client, q, max_urls=max_urls_per_query)
        all_urls.extend(batch)

    to_fetch = _unique_urls(all_urls, max_fetch_total)
    fetched_rows: list[dict[str, Any]] = []
    candidates: list[RawEvent] = []

    for u in to_fetch:
        row: dict[str, Any] = {"requested_url": u}
        try:
            r = client.get(u, timeout=30.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            row["http_ok"] = False
            row["error"] = str(e)[:400]
            fetched_rows.append(row)
            continue
        row["http_ok"] = True
        final_url = str(r.url)
        row["final_url"] = final_url
        parsed = best_event_dict(r.text, final_url)
        if not parsed:
            row["parsed"] = False
            fetched_rows.append(row)
            continue
        ev = raw_from_parsed(
            source,
            parsed,
            extra={"discovered_via": "google_custom_search"},
        )
        row.update(_raw_event_preview(ev))
        row["parsed"] = True
        kp = should_keep(ev)
        row["keyword_pass"] = kp
        fetched_rows.append(row)
        if kp:
            candidates.append(ev)

    return queries_executed, to_fetch, fetched_rows, candidates


def preview_google_cse(
    client: httpx.Client,
    *,
    source: str,
    queries: Sequence[str],
    max_urls_per_query: int = 10,
    max_fetch_total: int = 72,
) -> dict[str, Any]:
    """Dry-run: same pipeline as run_google_cse but no DB writes."""
    qn, to_fetch, fetched_rows, candidates = google_cse_gather(
        client,
        source=source,
        queries=queries,
        max_urls_per_query=max_urls_per_query,
        max_fetch_total=max_fetch_total,
    )
    after_llm = filter_enterprise_events(client, list(candidates))
    http_ok = sum(1 for r in fetched_rows if r.get("http_ok"))
    parsed_n = sum(1 for r in fetched_rows if r.get("parsed"))
    return {
        "summary": {
            "queries_executed": qn,
            "urls_discovered_unique": len(to_fetch),
            "http_fetch_ok": http_ok,
            "parsed_events": parsed_n,
            "keyword_pass": len(candidates),
            "llm_pass": len(after_llm),
        },
        "discovered_urls": to_fetch,
        "fetched": fetched_rows,
        "after_keyword_filter": [_raw_event_preview(e) for e in candidates],
        "after_llm": [_raw_event_preview(e) for e in after_llm],
    }


def run_google_cse(
    client: httpx.Client,
    conn: Connection,
    *,
    source: str,
    queries: Sequence[str],
    max_urls_per_query: int = 10,
    max_fetch_total: int = 72,
) -> tuple[int, int]:
    """
    For each search query, discover URLs via Google Custom Search API,
    fetch pages, map to RawEvent, apply should_keep + enterprise LLM.
    """
    _, _, fetched_rows, candidates = google_cse_gather(
        client,
        source=source,
        queries=queries,
        max_urls_per_query=max_urls_per_query,
        max_fetch_total=max_fetch_total,
    )
    fetched = sum(1 for r in fetched_rows if r.get("http_ok"))
    kept = 0
    for ev in filter_enterprise_events(client, candidates):
        upsert_event(conn, ev)
        kept += 1
    return fetched, kept