## Target

- In-person **enterprise AI** events in **London** (hustle/beginner denylists, reject dev/hackathon/research audience, require founder/exec/investor-style signals — see `ai_events/filters.py`).

## Built-in scrapers

- Meetup — Meetup `gql2` `eventSearch` (keywords: enterprise AI, machine learning, LLMs, AI agent; London centre, 25 mi); see `ai_events/sources/meetup.py`.  
- Eventbrite — London discover listings (`/ai/`, `/enterprise-ai/`, `/machine-learning/`, plus legacy category URLs in code) → JSON-LD  
- techUK — [Events calendar](https://www.techuk.org/what-we-deliver/events.html) — event pages parsed from HTML (JSON-LD if present); broad AI filter (`should_keep_techuk_ai`, UK-wide including online)  
- **Google search** — HTML search (Google + DuckDuckGo fallback, no API keys) → fetch result URLs → JSON-LD or Open Graph; same keyword + enterprise LLM filters as Eventbrite.  

## Manual / rich sources (no paid APIs)

Paste public event URLs into `seeds/urls.txt` (one per line), then run with `--sources seeds` or `all`.

You can still add links by hand from:

- LinkedIn Events search, e.g. `https://www.linkedin.com/search/results/events/?keywords=enterprise%20ai`  
- LinkedIn post search for announcements  
- X (Twitter) posts linking to Eventbrite, venue sites, etc.

See `README.md` for CLI usage.
