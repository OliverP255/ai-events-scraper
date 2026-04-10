# Enterprise AI events — London (in-person)

Python scraper that aggregates **upcoming in-person** events in **London** matching **enterprise / workplace AI** keywords. Data is stored in **PostgreSQL** (Neon or local Docker); the web UI reads the same database.

## Setup

```bash
cd "/path/to/ai-events-scraper"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set **`DATABASE_URL`**. For local Postgres: `docker compose up -d`, then `python -m ai_events db apply-schema`.

## Tests

Contract and integration tests use **pytest** and **mocked HTTP** (no live sites required). Storage integration tests need **`DATABASE_URL`** and an applied schema (they skip if unset).

```bash
pip install -r requirements-dev.txt
pytest
```

What the suite checks:

- **Filters** — `passes_hustle_pitch` rejects income-pitch / side-hustle copy; `passes_beginner_audience` rejects beginner / no-experience positioning; `passes_business_and_ai_keywords` requires AI/ML signals plus business **or** professional/community context (or strong / duplicate AI signals). **Eventbrite** and **Meetup** use a stricter gate (`strict_professional`): enterprise/B2B/corporate/executive/scale-up or job-title-style terms (e.g. engineer, researcher, CEO) — startup/founder alone is not enough. **Luma** and other sources use the default gate. **London** for most sources; **Meetup** skips London text (`require_london=False`). In-person optional in `should_keep` (commented out).
- **JSON-LD** — offline vs `VirtualLocation`, London fields from `schema.org` events.
- **Dates/times** — `parse_iso_datetime`, meta fallbacks, `subEvent`, and stored `starts_at`/`ends_at` in integration tests (`tests/test_datetime_util.py`, `tests/test_schema_datetimes.py`).
- **Luma** — offline rows parsed; `location_type: online` never becomes a stored event; UTC times and timezone in `extra_json`.
- **Eventbrite / techUK / seeds** — discovery + detail pipeline; rows excluded when they fail **London**. **Meetup** does not re-check London text after GQL discovery (see `tests/test_*_integration.py`).

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
