from __future__ import annotations

from ai_events.pg_connect import connect_psycopg
from ai_events.webapp.settings import ROOT


def apply_schema() -> None:
    path = ROOT / "sql" / "schema.sql"
    if not path.is_file():
        raise SystemExit(f"Missing schema file: {path}")

    sql = path.read_text(encoding="utf-8")

    with connect_psycopg() as conn:
        conn.execute(sql)
        conn.commit()
