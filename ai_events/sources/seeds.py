from __future__ import annotations

from pathlib import Path

import httpx
from psycopg import Connection

from ai_events.filters import should_keep
from ai_events.models import raw_from_parsed
from ai_events.schema_ld import first_event_dict
from ai_events.storage import upsert_event


def load_seed_urls(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("http://") or line.startswith("https://"):
            out.append(line)
    return out


def run_seeds(client: httpx.Client, conn: Connection, seed_file: Path) -> tuple[int, int]:
    kept = 0
    fetched = 0
    for u in load_seed_urls(seed_file):
        try:
            r = client.get(u)
            r.raise_for_status()
        except httpx.HTTPError:
            continue
        fetched += 1
        parsed = first_event_dict(r.text, str(r.url))
        if not parsed:
            continue
        ev = raw_from_parsed("seed", parsed, extra={"seed_file": seed_file.name})
        if should_keep(ev):
            upsert_event(conn, ev)
            kept += 1
    return fetched, kept
