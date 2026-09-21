CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    framework TEXT NOT NULL,
    framework_version TEXT,
    adapter_version TEXT,
    schema_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    redaction_applied BOOLEAN NOT NULL,
    redaction_filter_version TEXT,
    run_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS steps(
    step_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES traces(trace_id),
    step_index INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    parent_step_id TEXT,
    timestamp_start TIMESTAMPTZ NOT NULL,
    timestamp_end TIMESTAMPTZ,
    status TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    redacted BOOLEAN NOT NULL,
    latency_ms NUMERIC,
    was_rate_limited BOOLEAN NOT NULL,
    error_type TEXT ,
    error_message TEXT,
    cache_key TEXT,
    payload JSONB NOT NULL

);