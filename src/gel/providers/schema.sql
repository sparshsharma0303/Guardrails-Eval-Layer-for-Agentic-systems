CREATE TABLE IF NOT EXISTS cache (
    cache_key TEXT PRIMARY KEY,
    model TEXT,
    provider TEXT,
    prompt TEXT,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);