"""
HTML search discovery (no API keys): Google result pages + DuckDuckGo HTML fallback.

Result pages and target sites may block datacenter IPs; this is best-effort only.
"""

from __future__ import annotations

import re
import time
from typing import Any, Sequence
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from psycopg import Connection

from ai_events.enterprise_llm import filter_enterprise_events
from ai_events.filters import should_keep
from ai_events.models import RawEvent, raw_from_parsed
from ai_events.schema_ld import best_event_dict
from ai_events.storage import _norm_url, upsert_event

# Hosts we never fetch as event pages (trackers, search, obvious non-event hubs).
_SKIP_HOST_SUBSTR = (
    "google.",
    "gstatic.",
    "youtube.",
    "youtu.be",
    "facebook.",
    "fb.com",
    "instagram.",
    "tiktok.",
    "duckduckgo.",
    "bing.com",
    "microsoft.com",
    "wikipedia.org",
)


def _host_ok(url: str) -> bool:
    try:
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


def _extract_google_urls(html: str, max_urls: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not isinstance(href, str):
            continue
        target: str | None = None
        if href.startswith("/url?"):
            q = parse_qs(urlparse(f"https://www.google.com{href}").query)
            for key in ("q", "url"):
                vals = q.get(key)
                if vals and str(vals[0]).startswith("http"):
                    target = str(vals[0])
                    break
        elif href.startswith("https://www.google.com/url?") or href.startswith(
            "http://www.google.com/url?"
        ):
            q = parse_qs(urlparse(href).query)
            for key in ("q", "url"):
                vals = q.get(key)
                if vals and str(vals[0]).startswith("http"):
                    target = str(vals[0])
                    break
        if target:
            found.append(unquote(target))
        if len(found) >= max_urls * 3:
            break
    return _unique_urls(found, max_urls)


def google_search_urls(client: httpx.Client, query: str, *, max_urls: int = 20) -> list[str]:
    # gbv=1 often yields lighter HTML; still may be blocked without a browser session.
    url = f"https://www.google.com/search?q={quote_plus(query)}&num=30&hl=en&gbv=1"
    try:
        r = client.get(url)
        r.raise_for_status()
    except httpx.HTTPError:
        return []
    return _extract_google_urls(r.text, max_urls)


def _extract_duckduckgo_urls(html: str, max_urls: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    for a in soup.select("a.result__a"):
        href = a.get("href")
        if not isinstance(href, str) or not href:
            continue
        if href.startswith("//"):
            href = "https:" + href
        p = urlparse(href)
        qs = parse_qs(p.query)
        uddg = qs.get("uddg")
        if uddg:
            found.append(unquote(uddg[0]))
        elif href.startswith("http") and "duckduckgo.com" not in (p.hostname or ""):
            found.append(href)
        if len(found) >= max_urls * 3:
            break
    if len(found) < 3:
        for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"', html):
            href = m.group(1)
            if href.startswith("//"):
                href = "https:" + href
            p = urlparse(href)
            qs = parse_qs(p.query)
            uddg = qs.get("uddg")
            if uddg:
                found.append(unquote(uddg[0]))
            elif href.startswith("http") and "duckduckgo.com" not in (p.hostname or ""):
                found.append(href)
    return _unique_urls(found, max_urls)


def duckduckgo_search_urls(client: httpx.Client, query: str, *, max_urls: int = 20) -> list[str]:
    try:
        r = client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": ""},
            headers={"Referer": "https://duckduckgo.com/"},
        )
        r.raise_for_status()
    except httpx.HTTPError:
        return []
    return _extract_duckduckgo_urls(r.text, max_urls)


def discover_urls_for_query(client: httpx.Client, query: str, *, max_urls: int) -> list[str]:
    g = google_search_urls(client, query, max_urls=max_urls)
    need = max(0, max_urls - len(g))
    d: list[str] = []
    if need:
        time.sleep(0.8)
        d = duckduckgo_search_urls(client, query, max_urls=need)
    merged = g + [u for u in d if u not in set(g)]
    return _unique_urls(merged, max_urls)


def _raw_event_preview(ev: RawEvent) -> dict[str, Any]:
    desc = ev.description
    if desc and len(desc) > 800:
        desc = desc[:799].rstrip() + "…"
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


def search_discover_gather(
    client: httpx.Client,
    *,
    source: str,
    queries: Sequence[str],
    max_urls_per_query: int = 14,
    max_fetch_total: int = 72,
    search_pause_s: float = 1.2,
) -> tuple[int, list[str], list[dict[str, Any]], list[RawEvent]]:
    """
    Run search discovery and page fetches. Does not write to the database.

    Returns:
        queries_executed, unique_urls, one dict per URL attempt, keyword-filter candidates.
    """
    all_urls: list[str] = []
    seen_q: set[str] = set()
    queries_executed = 0
    for q in queries:
        q = (q or "").strip()
        if not q or q in seen_q:
            continue
        seen_q.add(q)
        queries_executed += 1
        batch = discover_urls_for_query(client, q, max_urls=max_urls_per_query)
        all_urls.extend(batch)
        if search_pause_s > 0:
            time.sleep(search_pause_s)

    to_fetch = _unique_urls(all_urls, max_fetch_total)
    fetched_rows: list[dict[str, Any]] = []
    candidates: list[RawEvent] = []

    for u in to_fetch:
        row: dict[str, Any] = {"requested_url": u}
        try:
            r = client.get(u)
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
            extra={"discovered_via": "html_search"},
        )
        row.update(_raw_event_preview(ev))
        row["parsed"] = True
        kp = should_keep(ev)
        row["keyword_pass"] = kp
        fetched_rows.append(row)
        if kp:
            candidates.append(ev)

    return queries_executed, to_fetch, fetched_rows, candidates


def preview_search_discovered(
    client: httpx.Client,
    *,
    source: str,
    queries: Sequence[str],
    max_urls_per_query: int = 14,
    max_fetch_total: int = 72,
    search_pause_s: float = 1.2,
) -> dict[str, Any]:
    """Dry-run: same pipeline as ``run_search_discovered`` but no DB writes."""
    qn, to_fetch, fetched_rows, candidates = search_discover_gather(
        client,
        source=source,
        queries=queries,
        max_urls_per_query=max_urls_per_query,
        max_fetch_total=max_fetch_total,
        search_pause_s=search_pause_s,
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


def run_search_discovered(
    client: httpx.Client,
    conn: Connection,
    *,
    source: str,
    queries: Sequence[str],
    max_urls_per_query: int = 14,
    max_fetch_total: int = 72,
    search_pause_s: float = 1.2,
) -> tuple[int, int]:
    """
    For each search query, discover URLs (Google HTML + DDG fill-in), fetch pages,
    map to RawEvent (JSON-LD or OG fallback), apply ``should_keep`` + enterprise LLM
    like Eventbrite.
    """
    _, _, fetched_rows, candidates = search_discover_gather(
        client,
        source=source,
        queries=queries,
        max_urls_per_query=max_urls_per_query,
        max_fetch_total=max_fetch_total,
        search_pause_s=search_pause_s,
    )
    fetched = sum(1 for r in fetched_rows if r.get("http_ok"))
    kept = 0
    for ev in filter_enterprise_events(client, candidates):
        upsert_event(conn, ev)
        kept += 1
    return fetched, kept
