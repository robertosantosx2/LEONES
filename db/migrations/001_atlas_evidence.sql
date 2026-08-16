-- LEONES — Atlas + Evidence physical storage v1
-- SQLite-oriented canonical schema. No execution/runtime code is included here.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    contract_version TEXT NOT NULL DEFAULT '1.0',
    type TEXT NOT NULL,
    verification_state TEXT NOT NULL CHECK (
        verification_state IN ('VERIFIED','ESTIMATED','UNVERIFIED','DISPUTED','STALE')
    ),
    source TEXT,
    observed_at TEXT,
    collected_at TEXT,
    methodology TEXT,
    artifact_ref TEXT,
    claims_json TEXT NOT NULL DEFAULT '[]',
    trace_id TEXT,
    run_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_state ON evidence(verification_state);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source);
CREATE INDEX IF NOT EXISTS idx_evidence_observed_at ON evidence(observed_at);

CREATE TABLE IF NOT EXISTS atlas_entities (
    entity_id TEXT PRIMARY KEY,
    contract_version TEXT NOT NULL DEFAULT '1.0',
    entity_type TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state = 'ACCEPTED'),
    version TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    promotion_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS atlas_entity_evidence (
    entity_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (entity_id, evidence_id),
    FOREIGN KEY (entity_id) REFERENCES atlas_entities(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS atlas_lineage (
    entity_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    parent_entity_id TEXT,
    promotion_id TEXT,
    PRIMARY KEY (entity_id, source_type, parent_entity_id),
    FOREIGN KEY (entity_id) REFERENCES atlas_entities(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_entity_id) REFERENCES atlas_entities(entity_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_atlas_entity_type ON atlas_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_atlas_promotion ON atlas_entities(promotion_id);
CREATE INDEX IF NOT EXISTS idx_lineage_parent ON atlas_lineage(parent_entity_id);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_migrations(version) VALUES ('001_atlas_evidence');
