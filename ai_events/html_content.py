"""Extract visible main content from HTML for richer event descriptions."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def merge_description_with_main_content(description: str | None, main_text: str) -> str | None:
    """Append or prefer main body text vs existing meta/JSON-LD description (dedupe overlaps)."""
    mt = main_text.strip()
    if not mt:
        return description
    ex = (description or "").strip()
    if not ex:
        return mt
    if ex in mt:
        return mt
    if mt in ex:
        return ex
    return f"{ex}\n\n---\n\n{mt}"


def extract_main_text_html(html: str, *, max_chars: int = 12000) -> str:
    """
    Best-effort main article text: ``main`` / ``article`` / ``[role=main]``, else ``body``
    with noisy chrome removed. Caps length for filters and storage.
    """
    if not html or not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    root = None
    for selector in ("main", "article", '[role="main"]'):
        hit = soup.select_one(selector)
        if hit:
            root = hit
            break

    if root is None:
        for sel in ("nav", "footer", "header"):
            for t in soup.find_all(sel):
                t.decompose()
        for t in soup.find_all("aside"):
            t.decompose()
        root = soup.body if soup.body else soup

    text = root.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out
