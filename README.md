# AI Events Scraper

https://ai-events-scraper.vercel.app/

A Python scraper that discovers in-person London enterprise AI events from multiple sources, stores them in PostgreSQL/Neon, and serves them via a FastAPI web application with full-text and semantic search.

- Currently scrapes eventbrite, meetup, techuk and google search. 
- Linkedin/socials had too many irrelevant posts for scraping actual events, google search had much better results
- The google search uses serper.dev api with a total of 2,500 queries for free, hopefully should be enough. 

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION                              │
├─────────────────────────────────────────────────────────────────────┤
│  Sources          Discovery      Fetch        Parse       Filter    │
│  ────────         ──────────     ─────        ─────       ──────    │
│  eventbrite   →   listing URLs   →  HTML   →  JSON-LD  →  keywords  │
│  meetup       →   GraphQL API    →  HTML   →  JSON-LD  →  (LLM)     │
│  techuk       →   calendar API   →  HTML   →  JSON-LD               │
│  google_search →  search results →  HTML   →  JSON-LD               │
│  seeds        →   manual URLs    →  HTML   →  JSON-LD               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         STORAGE                                     │
├─────────────────────────────────────────────────────────────────────┤
│  PostgreSQL/Neon                                                    │
│  - events table with tsvector (full-text search)                    │
│  - pgvector extension for semantic search (optional)                │
│  - pinned events protected from scraper overwrites                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION                                │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Web App                                                    │
│  - GET /api/events (search, filter, paginate)                       │
│  - GET /api/export (CSV download)                                   │
│  - Full-text search (tsvector) or semantic (pgvector)               │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### Sources Layer (`ai_events/sources/`)

Each scraper follows a convention-based pattern:
- Exports `run_[source](client: httpx.Client, conn: Connection) -> tuple[int, int]`
- Returns `(fetched_count, kept_count)`
- Registered in `ai_events/runner.py` SOURCES dict

**Pipeline:** discover URLs → fetch pages → parse JSON-LD → filter → upsert

### Data Model (`ai_events/models.py`)

```python
@dataclass
class RawEvent:
    source: str           # 'eventbrite', 'meetup', 'pinned', etc.
    url: str
    title: str
    description: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    venue: str | None
    city: str | None
    country: str | None
    is_in_person: bool | None
    attendance_mode_uri: str | None
    extra: dict[str, Any]
    pinned: bool          # Protected curated event
```

### Storage (`ai_events/storage.py`)

- **ID:** SHA256 hash of normalized URL (removes UTM params)
- **Upsert:** INSERT ... ON CONFLICT for idempotent writes
- **Pinned protection:** Rows with `pinned=true` cannot be overwritten by scrapers

### Filtering (`ai_events/filters.py`, `ai_events/enterprise_llm.py`)

Two-stage filtering with early exit:
1. **Keyword filters:** London location, enterprise focus, exclude consumer/webinar content
2. **LLM classification (optional):** Batch classification via Ollama for nuanced filtering

### Pinned Events (`ai_events/curated_events.py`, `ai_events/pinned_data/`)

- Hand-curated JSON catalog of enterprise AI conferences
- Protected from overwrites via `pinned=true` flag
- Fuzzy deduplication prevents scrapers from duplicating catalog events

### Web Layer (`ai_events/webapp/`)

- FastAPI with `/api/events`, `/api/export`, `/api/health`
- Full-text search via Postgres tsvector (always available)
- Semantic search via pgvector + Ollama embeddings (optional)

## Adding a New Scraper

1. Create `ai_events/sources/your_source.py`:

```python
from ai_events.schema_ld import first_event_dict
from ai_events.models import raw_from_parsed
from ai_events.filters import should_keep
from ai_events.storage import upsert_event

def run_your_source(client: httpx.Client, conn) -> tuple[int, int]:
    urls = discover_event_urls(client)
    fetched, kept = 0, 0
    for url in urls:
        fetched += 1
        html = client.get(url).text
        data = first_event_dict(html, url)
        if not data:
            continue
        event = raw_from_parsed("your_source", data)
        if should_keep(event):
            upsert_event(conn, event)
            kept += 1
    return (fetched, kept)
```

2. Register in `ai_events/runner.py`:

```python
from ai_events.sources.your_source import run_your_source

SOURCES = {
    ...
    "your_source": run_your_source,
}
```

## Key Files

| File | Purpose |
|------|---------|
| `ai_events/runner.py` | CLI entry point, source registration |
| `ai_events/models.py` | RawEvent dataclass |
| `ai_events/storage.py` | DB upsert, dedupe, export |
| `ai_events/schema_ld.py` | JSON-LD extraction from HTML |
| `ai_events/filters.py` | Keyword filtering rules |
| `ai_events/sources/*.py` | Individual scrapers |
| `ai_events/webapp/app.py` | FastAPI endpoints |
| `ai_events/webapp/queries.py` | Search implementation |
| `sql/schema.sql` | Database schema |

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SEMANTIC_SEARCH` | Enable pgvector search (default: true) |
| `ENTERPRISE_LLM_ENABLED` | Enable LLM filtering (default: false) |
| `EMBEDDING_OLLAMA_URL` | Ollama endpoint for embeddings |

## Common Commands

```bash
# Run all scrapers
python -m ai_events run

# Run specific sources
python -m ai_events run --sources eventbrite,meetup

# Preview Google search (no DB writes)
python -m ai_events preview-google-search

# Start web server
python -m ai_events serve

# Apply database schema
python -m ai_events db apply-schema

# Backfill embeddings for semantic search
python -m ai_events db backfill-embeddings

# Export to CSV
python -m ai_events export -o events.csv
```

## Automated Daily Scraping (GitHub Actions)

The scraper runs automatically every day via GitHub Actions.

**Workflow file:** `.github/workflows/scrape-daily.yml`

| Setting | Value |
|---------|-------|
| Schedule | 06:00 UTC daily |
| Trigger | `schedule` (automatic) or `workflow_dispatch` (manual) |
| Timeout | 120 minutes |

### Setup

1. Add `DATABASE_URL` secret: Settings → Secrets and variables → Actions → New repository secret
2. Workflow runs automatically at 06:00 UTC each day
3. Manually trigger from Actions tab → "Daily scrape" → "Run workflow"

### What it does

1. Checks out the repo
2. Sets up Python 3.12 with pip cache
3. Installs dependencies from `requirements.txt`
4. Runs `python -m ai_events run` (all sources, upsert only)