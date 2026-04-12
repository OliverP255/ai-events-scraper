"""Fill ``events.embedding`` via Ollama (sync HTTP). Run: ``python -m ai_events db backfill-embeddings``."""

from __future__ import annotations

import sys
from typing import Any

from psycopg import Connection

from ai_events.webapp.embeddings import (
    embed_text_sync,
    event_text_for_embedding,
    vector_to_pg_literal,
)


def backfill_embeddings(conn: Connection, *, limit: int | None = None) -> dict[str, Any]:
    from ai_events.webapp.settings import embedding_dimensions

    dim = embedding_dimensions()
    updated = 0
    failed = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, description, venue, city FROM events
            WHERE embedding IS NULL
            ORDER BY fetched_at DESC
            """
            + (" LIMIT %s" if limit is not None else ""),
            (limit,) if limit is not None else (),
        )
        rows = cur.fetchall()
    for row in rows:
        rid = row[0]
        text = event_text_for_embedding(row[1], row[2], row[3], row[4])
        if not text.strip():
            continue
        vec = embed_text_sync(text)
        if vec is None or len(vec) != dim:
            failed += 1
            continue
        lit = vector_to_pg_literal(vec)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE events SET embedding = %s::vector WHERE id = %s",
                    (lit, rid),
                )
            conn.commit()
            updated += 1
        except Exception as e:
            conn.rollback()
            print(f"backfill-embeddings: update failed for {rid}: {e}", file=sys.stderr)
            failed += 1
    return {"updated": updated, "failed": failed, "candidates": len(rows)}
