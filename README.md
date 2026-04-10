# Enterprise AI events — London (in-person)

Python scraper that aggregates **upcoming in-person** events in **London** matching **enterprise / workplace AI** keywords. Data is stored in **PostgreSQL** (Neon or local Docker); the web UI reads the same database.

## Sources

| Source | Method |
|--------|--------|
| Eventbrite | Discover pages (`/ai/`, `/enterprise-ai/`, `/machine-learning/`, plus legacy category listings) → event pages (`schema.org` JSON-LD) |
| Meetup | `gql2` `eventSearch` (keywords: enterprise AI, machine learning, LLMs, AI agent; London lat/lon, 25 mi) → event JSON-LD |
| Luma | `luma.com/ai` and `luma.com/london` SSR (`__NEXT_DATA__`, offline events only) |
| techUK | Events calendar → event pages (JSON-LD) |
| Seeds | `seeds/urls.txt` — paste public event URLs (e.g. from LinkedIn/X posts) |

Automated scraping of **LinkedIn** or **X** search is not included (login walls, ToS, breakage). Use **seeds** for links you find there.

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

## Rules

- **Content** (active): **Hustle / income-pitch** phrases → reject. **Beginner-audience** phrases (e.g. beginners, newcomers, no prior experience, entry level, for beginners) → reject. Otherwise need **AI/ML** terms plus **business** *or* **professional/community** *or* **strong AI** *or* **two+** AI-flavoured hits — except **Eventbrite** and **Meetup**, which require **enterprise-scale or role** signals (see `strict_professional` in `should_keep`). See `passes_business_and_ai_keywords`, `passes_hustle_pitch`, and `passes_beginner_audience` in `ai_events/filters.py`.
- **London** (active for Eventbrite, Luma, techUK, seeds): same fields must match London / central postcode-style hints. **Meetup** uses `should_keep(..., require_london=False)`.
- **Legacy broad matcher** `passes_enterprise_ai` remains for unit tests; it is not used in `should_keep`.
- **In-person** (disabled): `passes_in_person` is commented out in `should_keep` — re-enable when ready. **Luma** still only ingests **offline** events at the source level.

## Dates and times

- **`starts_at` / `ends_at`** in Postgres and CSV exports are **ISO-8601** strings (with offset when the source provides one).
- Parsing uses `ai_events/datetime_util.py`: supports `Z`, fractional seconds, `+0100`-style offsets, date-only days, and **`subEvent`** in JSON-LD when the parent `Event` omits times.
- If JSON-LD has no `startDate`/`endDate`, the scraper falls back to **`event:start_time` / `event:end_time`** (and some `itemprop`/`time` tags) when present.
- **Luma** copies **`event_timezone`** (IANA name, e.g. `Europe/London`) into `extra_json` for display tooling.

Respect site terms and `robots.txt`; use reasonable request rates (default single-threaded HTTP client).
