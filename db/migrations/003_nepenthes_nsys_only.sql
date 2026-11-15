-- LEONES NEPENTHES Nsight-only ingestion.
-- This schema deliberately has no JSONL/run_id foreign key: historical Nsight
-- captures can be preserved without inventing a paired NEPENTHES trace.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS nepenthes_nsys_imports (
    import_id TEXT PRIMARY KEY,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nsys_path TEXT NOT NULL,
    nsys_sha256 TEXT NOT NULL,
    activity_count INTEGER NOT NULL,
    activity_kinds_json TEXT NOT NULL,
    detected_table_counts_json TEXT NOT NULL,
    coverage_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    correlation_policy TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nepenthes_nsys_activities (
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
    FOREIGN KEY (import_id) REFERENCES nepenthes_nsys_imports(import_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nepenthes_nsys_activity_time
    ON nepenthes_nsys_activities(import_id, start_ns, end_ns);
CREATE INDEX IF NOT EXISTS idx_nepenthes_nsys_activity_corr
    ON nepenthes_nsys_activities(import_id, correlation_id);

INSERT OR IGNORE INTO schema_migrations(version)
VALUES ('003_nepenthes_nsys_only');
