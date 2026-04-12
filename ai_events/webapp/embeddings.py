"""Ollama (or OpenAI-compatible) text embeddings for semantic search."""

from __future__ import annotations

import json
import sys

import httpx

from ai_events.webapp.settings import (
    embedding_dimensions,
    embedding_http_timeout_s,
    embedding_model,
    embeddings_api_url,
)


def event_text_for_embedding(
    title: str | None,
    description: str | None,
    venue: str | None,
    city: str | None,
) -> str:
    parts = [
        (title or "").strip(),
        (description or "").strip(),
        (venue or "").strip(),
        (city or "").strip(),
    ]
    blob = "\n\n".join(p for p in parts if p)
    return blob[:12000] if len(blob) > 12000 else blob


def vector_to_pg_literal(vec: list[float]) -> str:
    """Format for Postgres `::vector` cast (asyncpg passes as string)."""
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


def _post_embed(client: httpx.Client, text: str) -> list[float] | None:
    url = embeddings_api_url()
    model = embedding_model()
    timeout = embedding_http_timeout_s()
    expected = embedding_dimensions()
    try:
        r = client.post(
            url,
            json={"model": model, "prompt": text},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"embeddings: HTTP error: {e}", file=sys.stderr)
        return None
    emb = data.get("embedding")
    if not isinstance(emb, list) or not emb:
        print("embeddings: missing embedding array in response", file=sys.stderr)
        return None
    try:
        out = [float(x) for x in emb]
    except (TypeError, ValueError):
        return None
    if len(out) != expected:
        print(
            f"embeddings: dimension {len(out)} != EMBEDDING_DIM {expected}",
            file=sys.stderr,
        )
        return None
    return out


def embed_text_sync(text: str) -> list[float] | None:
    if not (text or "").strip():
        return None
    with httpx.Client() as client:
        return _post_embed(client, text.strip())


async def embed_text_async(text: str) -> list[float] | None:
    if not (text or "").strip():
        return None
    url = embeddings_api_url()
    model = embedding_model()
    timeout = embedding_http_timeout_s()
    expected = embedding_dimensions()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url,
                json={"model": model, "prompt": text.strip()},
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"embeddings: async HTTP error: {e}", file=sys.stderr)
        return None
    emb = data.get("embedding")
    if not isinstance(emb, list) or not emb:
        return None
    try:
        out = [float(x) for x in emb]
    except (TypeError, ValueError):
        return None
    if len(out) != expected:
        print(
            f"embeddings: dimension {len(out)} != EMBEDDING_DIM {expected}",
            file=sys.stderr,
        )
        return None
    return out


async def any_embedding_in_db() -> bool:
    from ai_events.webapp import db

    pool = await db.get_pool()
    if pool is None:
        return False
    try:
        v = await db.fetch_val(
            "SELECT EXISTS(SELECT 1 FROM events WHERE embedding IS NOT NULL LIMIT 1)"
        )
        return bool(v)
    except Exception as e:
        print(f"semantic search: embedding check failed (fallback FTS): {e}", file=sys.stderr)
        return False
