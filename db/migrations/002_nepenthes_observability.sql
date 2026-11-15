-- LEONES NEPENTHES observability ingestion v1.
-- Raw source payloads are retained; clock domains are intentionally not joined.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS nepenthes_imports (
    import_id TEXT PRIMARY KEY,
    run_id TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    jsonl_path TEXT NOT NULL,
    jsonl_sha256 TEXT NOT NULL,
    nsys_path TEXT NOT NULL,
    nsys_sha256 TEXT NOT NULL,
    event_count INTEGER NOT NULL,
    activity_count INTEGER NOT NULL,
    event_kinds_json TEXT NOT NULL,
    activity_kinds_json TEXT NOT NULL,
    correlation_policy TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nepenthes_events (
    import_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    timestamp_unix_ns INTEGER NOT NULL,
    monotonic_ns INTEGER NOT NULL,
    request_id INTEGER NOT NULL,
    event_kind TEXT NOT NULL,
    label TEXT NOT NULL,
    value0 INTEGER NOT NULL,
    value1 INTEGER NOT NULL,
    duration_ns INTEGER NOT NULL,
    flags INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (import_id, event_id),
    FOREIGN KEY (import_id) REFERENCES nepenthes_imports(import_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS nsys_activities (
    import_id TEXT NOT NULL,
    activity_id INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    activity_kind TEXT NOT NULL,
    start_ns INTEGER,
    end_ns INTEGER,
    duration_ns INTEGER,
    correlation_id INTEGER,
    global_pid INTEGER,
    process_id INTEGER,
    device_id INTEGER,
    context_id INTEGER,
    stream_id INTEGER,
    name TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (import_id, activity_id),
    FOREIGN KEY (import_id) REFERENCES nepenthes_imports(import_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nepenthes_events_request
    ON nepenthes_events(import_id, request_id, event_kind);
CREATE INDEX IF NOT EXISTS idx_nepenthes_events_time
    ON nepenthes_events(import_id, monotonic_ns);
CREATE INDEX IF NOT EXISTS idx_nsys_activity_time
    ON nsys_activities(import_id, start_ns, end_ns);
CREATE INDEX IF NOT EXISTS idx_nsys_activity_corr
    ON nsys_activities(import_id, correlation_id);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_migrations(version)
VALUES ('002_nepenthes_observability');
