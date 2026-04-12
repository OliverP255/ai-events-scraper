# Enterprise AI events — London 


Production: deploy on [Vercel](https://vercel.com/) (Python / FastAPI; root `app.py` re-exports the app). Set **`DATABASE_URL`** in the project’s Environment Variables (same Neon string as locally). Default region in `vercel.json` is **Frankfurt (`fra1`)**; change it if your DB is elsewhere.

| Source | Method |
|--------|--------|
| Eventbrite | Discover pages (`/ai/`, `/enterprise-ai/`, `/machine-learning/`, plus legacy category listings) → event pages (`schema.org` JSON-LD) |
| Meetup | `gql2` `eventSearch` (keywords: enterprise AI, machine learning, LLMs, AI agent; London lat/lon, 25 mi) → event JSON-LD |
| techUK | Events calendar → event pages (**HTML parse**; JSON-LD when present); **broad AI filter** (`should_keep_techuk_ai`, no London requirement) |
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

- `--sources all` or `eventbrite,meetup,techuk,seeds`
- `--seeds seeds/urls.txt`

## Web UI

```bash
python -m ai_events serve
```

Open **`http://127.0.0.1:8000/`** (or your Vercel URL). Opening `index.html` via `file://` is not supported: API calls and asset paths expect an HTTP origin.

## Export

```bash
python -m ai_events export --format csv -o out/events.csv
python -m ai_events export --format jsonl
```