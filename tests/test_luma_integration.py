"""Luma London page: offline AI rows kept; online rows never parsed."""

from __future__ import annotations

import httpx
from psycopg import Connection

from ai_events.sources import luma as lu
from ai_events.storage import iter_events_rows
from tests.fixtures_html import (
    luma_next_data_london,
    luma_offline_ai_item,
    luma_online_item,
)


def test_run_luma_counts_online_as_seen_but_not_parsed(pg_conn: Connection) -> None:
    html = luma_next_data_london([luma_offline_ai_item(), luma_online_item()])
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, text=html)
        if str(r.url).startswith(("https://luma.com/ai", "https://luma.com/london"))
        else httpx.Response(404, text="")
    )
    with httpx.Client(transport=transport) as client:
        total, kept = lu.run_luma(client, pg_conn)
    assert total == 2
    assert kept == 1
    rows = list(iter_events_rows(pg_conn))
    assert len(rows) == 1
    assert "Enterprise AI" in rows[0]["title"]
    assert rows[0]["starts_at"] == "2026-08-01T08:00:00+00:00"
    assert rows[0]["ends_at"] == "2026-08-01T10:00:00+00:00"
    assert "Europe/London" in (rows[0]["extra_json"] or "")
