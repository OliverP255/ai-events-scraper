from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from ai_events.webapp import db
from ai_events.webapp.queries import list_sources, search_events
from ai_events.webapp.settings import database_url, load_env

load_env()

STATIC = Path(__file__).resolve().parent / "static"


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    s = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    yield
    await db.close_pool()


app = FastAPI(title="AI Events", lifespan=lifespan)

# Lets the UI work when opened from file:// or another origin (dev); same-origin needs no CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, "database_configured": database_url() is not None}


@app.get("/api/meta")
async def meta() -> dict[str, object]:
    sources = await list_sources()
    return {"sources": sources, "database_available": await db.get_pool() is not None}


@app.get("/api/events")
async def api_events(
    q: str | None = Query(None, description="Full-text search (Postgres plainto_tsquery)"),
    source: str | None = Query(None),
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    pool = await db.get_pool()
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    items, total = await search_events(
        q=q,
        source=source,
        date_from=df,
        date_to=dt,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "database_available": pool is not None,
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")
