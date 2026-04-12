# Enterprise AI events — London 


Production: deploy on [Vercel](https://vercel.com/) (Python / FastAPI; root `app.py` re-exports the app). Set **`DATABASE_URL`** in the project’s Environment Variables (same Neon string as locally). Default region in `vercel.json` is **Frankfurt (`fra1`)**; change it if your DB is elsewhere.

| Source | Method |
|--------|--------|
| Eventbrite | Discover pages (`/ai/`, `/enterprise-ai/`, `/machine-learning/`, plus legacy category listings) → event pages (`schema.org` JSON-LD) |
| Meetup | `gql2` `eventSearch` (keywords: enterprise AI, machine learning, LLMs, AI agent; London lat/lon, 25 mi) → event JSON-LD |
| techUK | Events calendar → event pages (**HTML parse**; JSON-LD when present); **broad AI filter** (`should_keep_techuk_ai`, no London requirement) |
| Google search | HTML result pages (Google + DuckDuckGo fallback, **no API keys**) → result URLs → event pages (JSON-LD or Open Graph fallback) |
| Seeds | `seeds/urls.txt` — paste public event URLs (e.g. from LinkedIn/X posts) |

## Setup

```bash
cd "/path/to/ai-events-scraper"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set **`DATABASE_URL`**. For local Postgres: `docker compose up -d`, then `python -m ai_events db apply-schema`.


## Run

```bash
python -m ai_events run
```

Requires **`DATABASE_URL`**. Options:

- `--sources all` or `eventbrite,meetup,techuk,google_search,seeds`
- `--seeds seeds/urls.txt`
- `--no-llm` — force the enterprise LLM off for this run (overrides `.env`)

### Enterprise LLM filter (optional, off by default)

After the usual keyword filters, **Eventbrite**, **Meetup**, **techUK**, and **google_search** can optionally batch events (5 per request) and send them to a **local** OpenAI-compatible API (default [Ollama](https://ollama.com/) at `http://127.0.0.1:11434/v1`). The model returns `0` or `1` per event; only `1` rows are upserted. **Seeds** are unchanged (keyword filter only).

Set **`ENTERPRISE_LLM_ENABLED=1`** in `.env` to enable. When the LLM is off, behavior is keyword filtering only. When it is on but a batch fails after retry, that batch is dropped.

## Web UI

```bash
python -m ai_events serve
```

Open **`http://127.0.0.1:8765/`** (or your Vercel URL; default `--port` is 8765). Opening `index.html` via `file://` is not supported: API calls and asset paths expect an HTTP origin.

## Export

```bash
python -m ai_events export --format csv -o out/events.csv
python -m ai_events export --format jsonl
```