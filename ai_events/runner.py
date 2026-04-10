from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_events.http_util import client as make_client
from ai_events.pg_connect import connect_psycopg
from ai_events.sources.eventbrite import run_eventbrite
from ai_events.sources.luma import run_luma
from ai_events.sources.meetup import run_meetup
from ai_events.sources.seeds import run_seeds
from ai_events.sources.techuk import run_techuk
from ai_events.storage import export_csv, export_json_lines

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEEDS = ROOT / "seeds" / "urls.txt"

SOURCES = {
    "eventbrite": run_eventbrite,
    "meetup": run_meetup,
    "luma": run_luma,
    "techuk": run_techuk,
}


def cmd_run(args: argparse.Namespace) -> int:
    names = [s.strip() for s in args.sources.split(",") if s.strip()]
    if names == ["all"]:
        names = list(SOURCES.keys()) + ["seeds"]

    with connect_psycopg() as conn:
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
        raise SystemExit(1) from e

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
        help="Comma-separated: eventbrite,meetup,luma,techuk,seeds or 'all'",
    )
    r.add_argument("--seeds", default=str(DEFAULT_SEEDS), help="Newline-separated seed URLs")
    r.add_argument("--timeout", default="30", help="HTTP timeout seconds")
    r.set_defaults(func=cmd_run)

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

    args = p.parse_args(argv)
    code = args.func(args)
    return 0 if code is None else int(code)


if __name__ == "__main__":
    raise SystemExit(main())
