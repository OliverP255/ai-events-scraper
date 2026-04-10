-- Events table (Neon / Postgres). Apply: python -m ai_events db apply-schema

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    venue TEXT,
    city TEXT,
    country TEXT,
    is_in_person BOOLEAN,
    attendance_mode_uri TEXT,
    extra_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL,
    search_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector(
            'english',
            coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(venue, '') || ' ' || coalesce(city, '')
        )
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_events_starts ON events (starts_at);
CREATE INDEX IF NOT EXISTS idx_events_source ON events (source);
CREATE INDEX IF NOT EXISTS idx_events_fts ON events USING GIN (search_tsv);
