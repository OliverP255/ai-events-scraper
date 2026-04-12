-- Events table (Neon / Postgres). Apply: python -m ai_events db apply-schema
-- Semantic search: enable pgvector in the Neon console (or CREATE EXTENSION below) and run
-- ``python -m ai_events db backfill-embeddings`` after ``ollama pull nomic-embed-text``.

CREATE EXTENSION IF NOT EXISTS vector;

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
    pinned BOOLEAN NOT NULL DEFAULT false,
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

-- Existing deployments created before `pinned` was added:
ALTER TABLE events ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT false;

-- Must match EMBEDDING_DIM (default 768 for nomic-embed-text via Ollama).
ALTER TABLE events ADD COLUMN IF NOT EXISTS embedding vector(768);

CREATE INDEX IF NOT EXISTS idx_events_embedding_hnsw ON events USING hnsw (embedding vector_cosine_ops);
