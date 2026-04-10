# Enterprise AI events — London 


https://ai-events-web.onrender.com/ 

<<<<<<< HEAD
| Source | Method |
|--------|--------|
| Eventbrite | Discover pages (`/ai/`, `/enterprise-ai/`, `/machine-learning/`, plus legacy category listings) → event pages (`schema.org` JSON-LD) |
| Meetup | `gql2` `eventSearch` (keywords: enterprise AI, machine learning, LLMs, AI agent; London lat/lon, 25 mi) → event JSON-LD |
| techUK | Events calendar → event pages (**HTML parse**; JSON-LD when present); **broad AI filter** (`should_keep_techuk_ai`, no London requirement) |
| Seeds | `seeds/urls.txt` — paste public event URLs (e.g. from LinkedIn/X posts) |

Automated scraping of **LinkedIn** or **X** search is not included (login walls, ToS, breakage). Use **seeds** for links you find there.
=======
Python scraper that aggregates events in **London** matching **enterprise / workplace AI** keywords. Data is stored in **PostgreSQL** (Neon or local Docker); the web UI reads the same database.
>>>>>>> ca95f6a8fedec0f6b2bec09613f97e4f374d5f7b

## Setup

```bash
cd "/path/to/ai-events-scraper"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set **`DATABASE_URL`**. For local Postgres: `docker compose up -d`, then `python -m ai_events db apply-schema`.

<<<<<<< HEAD
## Tests

Contract and integration tests use **pytest** and **mocked HTTP** (no live sites required). Storage integration tests need **`DATABASE_URL`** and an applied schema (they skip if unset).

```bash
pip install -r requirements-dev.txt
pytest
```

What the suite checks:

- **Filters** — Eventbrite, Meetup, and seeds use the full keyword gate (`passes_business_and_ai_keywords`). **techUK** only requires AI/ML terms (`should_keep_techuk_ai` with `require_london=False`). **London** for Eventbrite and seeds; **Meetup** skips London text (`require_london=False`). In-person optional in `should_keep` (commented out).
- **JSON-LD** — offline vs `VirtualLocation`, London fields from `schema.org` events.
- **Dates/times** — `parse_iso_datetime`, meta fallbacks, `subEvent`, and stored `starts_at`/`ends_at` in integration tests (`tests/test_datetime_util.py`, `tests/test_schema_datetimes.py`).
- **Eventbrite / seeds** — discovery + detail pipeline; rows excluded when they fail **London**. **techUK** does not require London text. **Meetup** does not re-check London text after GQL discovery (see `tests/test_*_integration.py`).

=======
>>>>>>> ca95f6a8fedec0f6b2bec09613f97e4f374d5f7b
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

## Export

```bash
python -m ai_events export --format csv -o out/events.csv
python -m ai_events export --format jsonl
```
<<<<<<< HEAD

## Rules

- **Content** (active for Eventbrite / Meetup / seeds): **Hustle / income-pitch** phrases → reject. **Beginner-audience** phrases → reject. **Developer / hackathon / research** audience → reject. Otherwise need **AI/ML** terms plus **founder / exec / enterprise / investor / GTM**-style signals (`passes_business_and_ai_keywords`). **techUK** uses **`should_keep_techuk_ai`** (AI/ML terms only; UK-wide).
- **London** (active for Eventbrite and seeds): same fields must match London / central postcode-style hints. **Meetup** and **techUK** use `require_london=False` in their filter calls.
- **Legacy broad matcher** `passes_enterprise_ai` remains for unit tests; it is not used in `should_keep`.
- **In-person** (disabled): `passes_in_person` is commented out in `should_keep` — re-enable when ready.

## Dates and times

- **`starts_at` / `ends_at`** in Postgres and CSV exports are **ISO-8601** strings (with offset when the source provides one).
- Parsing uses `ai_events/datetime_util.py`: supports `Z`, fractional seconds, `+0100`-style offsets, date-only days, and **`subEvent`** in JSON-LD when the parent `Event` omits times.
- If JSON-LD has no `startDate`/`endDate`, the scraper falls back to **`event:start_time` / `event:end_time`** (and some `itemprop`/`time` tags) when present.
Respect site terms and `robots.txt`; use reasonable request rates (default single-threaded HTTP client).
=======
>>>>>>> ca95f6a8fedec0f6b2bec09613f97e4f374d5f7b
