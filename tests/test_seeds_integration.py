"""Seed URLs: file-backed list ingested with same filters."""

from __future__ import annotations

from pathlib import Path

import httpx

from psycopg import Connection

from ai_events.sources.seeds import load_seed_urls, run_seeds
from ai_events.storage import iter_events_rows
from tests.fixtures_html import EVENT_PAGE_LONDON_OFFLINE_AI


def test_load_seed_urls_skips_comments_and_blank(tmp_path: Path) -> None:
    p = tmp_path / "urls.txt"
    p.write_text(
        "\n# comment\n\nhttps://a.com/x\n  https://b.com/y  \n",
        encoding="utf-8",
    )
    assert load_seed_urls(p) == ["https://a.com/x", "https://b.com/y"]


def test_run_seeds(tmp_path: Path, pg_conn: Connection) -> None:
    seed = tmp_path / "one.txt"
    seed.write_text("https://www.eventbrite.com/e/x-tickets-111\n", encoding="utf-8")
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, text=EVENT_PAGE_LONDON_OFFLINE_AI)
        if "eventbrite.com" in str(r.url)
        else httpx.Response(404, text="")
    )
    with httpx.Client(transport=transport) as client:
        fetched, kept, manual = run_seeds(client, pg_conn, seed)
    assert fetched == 1
    assert kept == 1
    assert manual == 0
    assert len(list(iter_events_rows(pg_conn))) == 1
    assert list(iter_events_rows(pg_conn))[0]["source"] == "seed"
