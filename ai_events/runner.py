from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ai_events.curated_events import ensure_pinned_events, prune_stale_catalog_rows
from ai_events.pinned_dedupe import delete_scraper_rows_duplicating_pinned_catalog
from ai_events.http_util import client as make_client
from ai_events.pg_connect import connect_psycopg
from ai_events.sources.eventbrite import run_eventbrite
from ai_events.sources.google_search import run_google_search
from ai_events.sources.meetup import run_meetup
from ai_events.sources.seeds import (
    CURATED_SEED_HUB_URLS,
    load_manual_seed_rows,
    raw_event_from_manual_row,
    refresh_seed_metadata,
    run_seeds,
)
from ai_events.sources.techuk import run_techuk
from ai_events.storage import (
    dedupe_events_by_normalized_url,
    delete_events_for_normalized_urls,
    export_csv,
    export_json_lines,
    upsert_event,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEEDS = ROOT / "seeds" / "urls.txt"

SOURCES = {
    "eventbrite": run_eventbrite,
    "meetup": run_meetup,
    "techuk": run_techuk,
    "google_search": run_google_search,
}


def cmd_run(args: argparse.Namespace) -> int:
    if getattr(args, "no_llm", False):
        os.environ["ENTERPRISE_LLM_ENABLED"] = "0"

    names = [s.strip() for s in args.sources.split(",") if s.strip()]
    if names == ["all"]:
        names = list(SOURCES.keys()) + ["seeds"]

    with connect_psycopg() as conn:
        n_pin = ensure_pinned_events(conn)
        print(f"pinned: loaded {n_pin} catalog events", file=sys.stderr, flush=True)

    http = make_client(timeout=float(args.timeout))
    try:
        for name in names:
            with connect_psycopg() as conn:
                if name == "seeds":
                    p = Path(args.seeds)
                    f, k, m = run_seeds(http, conn, p)
                    d = dedupe_events_by_normalized_url(conn)
                    print(
                        f"seeds: fetched {f}, kept_auto {k}, manual {m}, url-dedupe removed {d}",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue
                fn = SOURCES.get(name)
                if not fn:
                    print(f"Unknown source: {name}", file=sys.stderr)
                    return 2
                f, k = fn(http, conn)
                print(f"{name}: fetched {f}, kept {k}", file=sys.stderr, flush=True)
    finally:
        http.close()
    return 0


def cmd_refresh_seeds(args: argparse.Namespace) -> int:
    """Remove hub URLs from DB, re-fetch all seed URLs, upsert parsed metadata (no filter), apply manual JSON, dedupe."""
    p = Path(args.seeds)
    with connect_psycopg() as conn:
        n_del = delete_events_for_normalized_urls(conn, list(CURATED_SEED_HUB_URLS))
        print(f"refresh-seeds: removed {n_del} hub row(s)", file=sys.stderr, flush=True)

    http = make_client(timeout=float(args.timeout))
    try:
        with connect_psycopg() as conn:
            ok, bad = refresh_seed_metadata(http, conn, p)
            print(
                f"refresh-seeds: metadata upserted {ok}, fetch/parse failed {bad}",
                file=sys.stderr,
                flush=True,
            )
            manual_n = 0
            for row in load_manual_seed_rows(p):
                ev = raw_event_from_manual_row(row, seed_file=p.name)
                upsert_event(conn, ev)
                manual_n += 1
            print(f"refresh-seeds: manual supplements {manual_n}", file=sys.stderr, flush=True)
            d = dedupe_events_by_normalized_url(conn)
            print(f"refresh-seeds: url-dedupe removed {d}", file=sys.stderr, flush=True)
    finally:
        http.close()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Install web deps: pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1) from None

    url = f"http://{args.host}:{args.port}/"
    print(f"Open {url} — API {url}api/events", file=sys.stderr)
    print("Ctrl+C to stop.", file=sys.stderr)
    uvicorn.run(
        "ai_events.webapp.app:app",
        host=args.host,
        port=int(args.port),
        reload=bool(args.reload),
    )
    return 0


def cmd_db_apply_schema(args: argparse.Namespace) -> int:
    from ai_events.webapp.schema_apply import apply_schema

    apply_schema()
    print("Schema applied.", file=sys.stderr)
    return 0


def cmd_db_backfill_embeddings(args: argparse.Namespace) -> int:
    from ai_events.webapp.embed_backfill import backfill_embeddings

    limit = getattr(args, "limit", None)
    with connect_psycopg() as conn:
        r = backfill_embeddings(conn, limit=limit)
    print(
        f"backfill-embeddings: candidates={r['candidates']} "
        f"updated={r['updated']} failed={r['failed']}",
        file=sys.stderr,
    )
    return 0


def cmd_db_prune_catalog(args: argparse.Namespace) -> int:
    with connect_psycopg() as conn:
        r = prune_stale_catalog_rows(conn)
        dup_ids = delete_scraper_rows_duplicating_pinned_catalog(conn)
    n = int(r["total_removed"])
    print(
        f"prune-catalog: removed {n} row(s) "
        f"(mock/placeholder URLs: {len(r['removed_mock_url'])}, "
        f"stale source=pinned: {len(r['removed_stale_pinned_source'])})",
        file=sys.stderr,
    )
    if r["removed_mock_url"]:
        print("  deleted ids (mock URL / test URL):", ", ".join(r["removed_mock_url"]), file=sys.stderr)
    if r["removed_stale_pinned_source"]:
        print("  deleted ids (stale pinned):", ", ".join(r["removed_stale_pinned_source"]), file=sys.stderr)
    if dup_ids:
        print(
            f"prune-catalog: removed {len(dup_ids)} scraper row(s) duplicating pinned catalog titles/dates",
            file=sys.stderr,
        )
        print("  deleted ids (scraper dupes):", ", ".join(dup_ids), file=sys.stderr)
    return 0


def cmd_db_dedupe(args: argparse.Namespace) -> int:
    """Remove duplicate non-pinned rows: same normalized URL, then same-day near-duplicate titles."""
    from ai_events.db_prune import dedupe_scraper_duplicates

    with connect_psycopg() as conn:
        r = dedupe_scraper_duplicates(conn)
    print(
        f"dedupe: removed {r['normalized_url_removed']} row(s) (same normalized URL), "
        f"{r['same_day_title_removed_count']} row(s) (same day + similar title)",
        file=sys.stderr,
    )
    for item in r["same_day_title_removed"]:
        print(f"  {item['id']}: {item['reason']}", file=sys.stderr)
    return 0


def cmd_db_prune_quality(args: argparse.Namespace) -> int:
    """Remove non-pinned rows that fail keyword filters + same-day title near-duplicates."""
    from ai_events.db_prune import prune_quality

    dry = bool(getattr(args, "dry_run", False))
    with connect_psycopg() as conn:
        if not dry:
            dup_ids = delete_scraper_rows_duplicating_pinned_catalog(conn)
            if dup_ids:
                print(
                    f"prune-quality: removed {len(dup_ids)} scraper row(s) duplicating pinned catalog",
                    file=sys.stderr,
                )
        report = prune_quality(conn, dry_run=dry)
    n = report["removed_count"]
    print(
        f"prune-quality: {'would remove' if dry else 'removed'} {n} row(s) (filters + duplicates)",
        file=sys.stderr,
    )
    for item in report["removed"]:
        print(f"  {item['id']}: {item['reason']}", file=sys.stderr)
    return 0


def cmd_preview_google_search(args: argparse.Namespace) -> int:
    if getattr(args, "no_llm", False):
        os.environ["ENTERPRISE_LLM_ENABLED"] = "0"
    from ai_events.sources.google_search import preview_google_search

    http = make_client(timeout=float(args.timeout))
    try:
        data = preview_google_search(
            http,
            max_urls_per_query=int(args.max_urls_per_query),
            max_fetch_total=int(args.max_fetch_total),
        )
    finally:
        http.close()
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    with connect_psycopg() as conn:
        if args.format == "csv":
            s = export_csv(conn)
        else:
            s = export_json_lines(conn)
    out = Path(args.output) if args.output else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(s, encoding="utf-8")
        print(str(out), file=sys.stderr)
    else:
        sys.stdout.write(s)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="London enterprise AI events (in-person) scraper")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Fetch sources and upsert into Postgres (DATABASE_URL)")
    r.add_argument(
        "--sources",
        default="all",
        help="Comma-separated: eventbrite,meetup,techuk,google_search,seeds or 'all'",
    )
    r.add_argument("--seeds", default=str(DEFAULT_SEEDS), help="Newline-separated seed URLs")
    r.add_argument("--timeout", default="30", help="HTTP timeout seconds")
    r.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable enterprise LLM filter (keyword filters only; see ENTERPRISE_LLM_ENABLED)",
    )
    r.set_defaults(func=cmd_run)

    pg = sub.add_parser(
        "preview-google-search",
        help="Run google_search discovery via Custom Search API; print JSON only (no database writes)",
    )
    pg.add_argument("--timeout", default="45", help="HTTP timeout seconds")
    pg.add_argument(
        "--max-urls-per-query",
        default="10",
        help="Cap URLs per search query (default 10, max 10 per CSE API)",
    )
    pg.add_argument(
        "--max-fetch-total",
        default="100",
        help="Max unique result URLs to fetch (default 100)",
    )
    pg.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable enterprise LLM (after_keyword_filter equals after_llm)",
    )
    pg.set_defaults(func=cmd_preview_google_search)

    rf = sub.add_parser(
        "refresh-seeds",
        help="Re-fetch seed URLs, upsert parsed metadata (no thin-page filter), apply .manual.json, dedupe; removes known hub URLs from DB",
    )
    rf.add_argument(
        "--seeds",
        default=str(ROOT / "seeds" / "search_curated_from_web.txt"),
        help="Newline-separated seed URLs (default: seeds/search_curated_from_web.txt)",
    )
    rf.add_argument("--timeout", default="30", help="HTTP timeout seconds")
    rf.set_defaults(func=cmd_refresh_seeds)

    e = sub.add_parser("export", help="Dump Postgres to CSV or JSON lines")
    e.add_argument("--format", choices=("csv", "jsonl"), default="csv")
    e.add_argument("-o", "--output", help="Write file instead of stdout")
    e.set_defaults(func=cmd_export)

    s = sub.add_parser("serve", help="Web UI + JSON API (Postgres / Neon)")
    s.add_argument("--host", default="127.0.0.1", help="Bind address")
    s.add_argument("--port", default="8765", help="Port")
    s.add_argument("--reload", action="store_true", help="Dev auto-reload")
    s.set_defaults(func=cmd_serve)

    d = sub.add_parser("db", help="Postgres schema tools")
    d_sub = d.add_subparsers(dest="db_cmd", required=True)
    d_apply = d_sub.add_parser("apply-schema", help="Apply sql/schema.sql (needs DATABASE_URL)")
    d_apply.set_defaults(func=cmd_db_apply_schema)
    d_emb = d_sub.add_parser(
        "backfill-embeddings",
        help="Set events.embedding via Ollama (OLLAMA host + nomic-embed-text); needs pgvector column",
    )
    d_emb.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max rows with NULL embedding to process (default: all)",
    )
    d_emb.set_defaults(func=cmd_db_backfill_embeddings)
    d_prune = d_sub.add_parser(
        "prune-catalog",
        help="Remove mock pinned.catalog URLs, stale pinned rows, and scraper rows that duplicate pinned_data/pinned_events.json (title/date)",
    )
    d_prune.set_defaults(func=cmd_db_prune_catalog)
    d_dedupe = d_sub.add_parser(
        "dedupe",
        help="Remove non-pinned duplicate rows: same normalized URL, then same-day + similar title (see storage + db_prune)",
    )
    d_dedupe.set_defaults(func=cmd_db_dedupe)
    d_pq = d_sub.add_parser(
        "prune-quality",
        help="Remove non-pinned rows that fail filters.py rules + same-day near-duplicate titles; also scraper dupes of pinned catalog unless --dry-run",
    )
    d_pq.add_argument(
        "--dry-run",
        action="store_true",
        help="Print removals only; do not delete (pinned-catalog dedupe also skipped)",
    )
    d_pq.set_defaults(func=cmd_db_prune_quality)

    args = p.parse_args(argv)
    code = args.func(args)
    return 0 if code is None else int(code)


if __name__ == "__main__":
    raise SystemExit(main())
