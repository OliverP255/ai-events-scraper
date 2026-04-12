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
from ai_events.sources.seeds import run_seeds
from ai_events.sources.techuk import run_techuk
from ai_events.storage import export_csv, export_json_lines

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
        print(f"pinned: loaded {n_pin} catalog events", file=sys.stderr)
        http = make_client(timeout=float(args.timeout))
        try:
            for name in names:
                if name == "seeds":
                    p = Path(args.seeds)
                    f, k = run_seeds(http, conn, p)
                    print(f"seeds: fetched {f}, kept {k}", file=sys.stderr)
                    continue
                fn = SOURCES.get(name)
                if not fn:
                    print(f"Unknown source: {name}", file=sys.stderr)
                    return 2
                f, k = fn(http, conn)
                print(f"{name}: fetched {f}, kept {k}", file=sys.stderr)
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
            search_pause_s=float(args.search_pause),
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
        help="Run google_search discovery + filters; print JSON only (no database writes)",
    )
    pg.add_argument("--timeout", default="45", help="HTTP timeout seconds")
    pg.add_argument(
        "--max-urls-per-query",
        default="14",
        help="Cap URLs per search query (default matches full run)",
    )
    pg.add_argument(
        "--max-fetch-total",
        default="72",
        help="Max unique result URLs to fetch (default matches full run)",
    )
    pg.add_argument(
        "--search-pause",
        default="1.2",
        help="Seconds to sleep between search queries (rate limit)",
    )
    pg.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable enterprise LLM (after_keyword_filter equals after_llm)",
    )
    pg.set_defaults(func=cmd_preview_google_search)

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
    d_prune = d_sub.add_parser(
        "prune-catalog",
        help="Remove mock pinned.catalog URLs, stale pinned rows, and scraper rows that duplicate pinned_events.json (title/date)",
    )
    d_prune.set_defaults(func=cmd_db_prune_catalog)

    args = p.parse_args(argv)
    code = args.func(args)
    return 0 if code is None else int(code)


if __name__ == "__main__":
    raise SystemExit(main())
