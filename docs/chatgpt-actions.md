# ChatGPT Custom GPT (internal) — Actions setup

This project exposes a **trimmed OpenAPI** file so you can attach your deployed API to a **Custom GPT** via **Actions**. No API key or rate limiting is configured in the app (internal/trusted use only).

## What was added

1. **`openapi/chatgpt-actions.yaml`** — OpenAPI 3.0.3 with three operations:
   - `GET /api/health` — `getHealth`
   - `GET /api/meta` — `getMeta` (sources + `database_available`)
   - `GET /api/events` — `listEvents` (query: `q`, `source`, `from`, `to`, `limit`, `offset`)

   CSV export is **not** included (keeps model context small).

2. **`GET /openapi/chatgpt-actions.yaml`** — Serves that file from the running app so ChatGPT can **import from URL** (e.g. `https://<your-host>/openapi/chatgpt-actions.yaml`).

## Configure the OpenAPI server URL

Before or after import, the **server base URL** must match your deployment (no trailing slash):

- Edit `servers[0].url` in `openapi/chatgpt-actions.yaml` and redeploy, **or**
- After importing in ChatGPT, set / fix the server URL in the Actions UI if your ChatGPT version allows it.

Placeholder in repo: `https://REPLACE-WITH-YOUR-HOST`.

## ChatGPT builder steps

1. Create a **Custom GPT** → **Configure** → **Actions** → **Create new action**.
2. **Import** from URL: `https://<your-deployment>/openapi/chatgpt-actions.yaml` (or paste the YAML).
3. **Authentication:** None (matches current app).
4. Save and test with prompts like: “List sources”, “Search events about agents in June 2026”, “What’s the health of the API?”

## Suggested GPT instructions (paste into Instructions)

Use a short system-style block, for example:

- Call **getHealth** or **getMeta** if you need to know whether the database is available or which `source` values exist.
- For event lists, use **listEvents**. Use ISO8601 for `from` / `to` when the user gives dates.
- Default **limit** to 50 unless the user needs more (max500).
- Summarize **items** with title, dates, city, url, source, pinned; for pinned rows, mention `extra_json.details` sections if present.
- If `database_available` is false or **items** is empty, say the backend may be misconfigured or filters matched nothing.

## Search behaviour (for your team)

With `q` set, the API uses **semantic** search when `SEMANTIC_SEARCH` is on, embeddings exist, and the embed call succeeds; otherwise **Postgres full-text** (`plainto_tsquery`). See `ai_events/webapp/queries.py`.
