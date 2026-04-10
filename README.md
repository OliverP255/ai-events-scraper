# Enterprise AI events — London (in-person)


https://ai-events-web.onrender.com/ 

Python scraper that aggregates **upcoming in-person** events in **London** matching **enterprise / workplace AI** keywords. Data is stored in **PostgreSQL** (Neon or local Docker); the web UI reads the same database.

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

- `--sources all` or `eventbrite,meetup,luma,techuk,seeds`
- `--seeds seeds/urls.txt`

## Web UI

```bash
python -m ai_events serve
```

## Export

```bash
python -m ai_events export --format csv -o out/events.csv
python -m ai_events export --format jsonl
```
