-- Open LLM Atlas: JGB openness layer
-- Source: Jesus M. Gonzalez-Barahona, Generative AI in your own infrastructure (2026).
-- This is additive. It does not replace taxonomy_barahona or model quality scores.

CREATE TABLE IF NOT EXISTS jgb_classifications (
    jgb_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    jgb_level INTEGER NOT NULL CHECK (jgb_level BETWEEN 0 AND 5),
    jgb_class TEXT NOT NULL,
    access_level TEXT,
    model_control TEXT,
    data_control TEXT,
    autonomy_level TEXT,
    trust_level TEXT,
    self_hostable TEXT DEFAULT 'unknown',
    confidence TEXT DEFAULT 'unknown',
    evidence_summary TEXT,
    source_id TEXT,
    checked_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS jgb_evidence (
    evidence_id TEXT PRIMARY KEY,
    jgb_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    claim TEXT NOT NULL,
    evidence_url TEXT,
    evidence_type TEXT,
    retrieved_at TEXT,
    confidence TEXT DEFAULT 'unknown',
    notes TEXT,
    FOREIGN KEY (jgb_id) REFERENCES jgb_classifications(jgb_id)
);

CREATE INDEX IF NOT EXISTS idx_jgb_model ON jgb_classifications(model_id);
CREATE INDEX IF NOT EXISTS idx_jgb_level ON jgb_classifications(jgb_level);
CREATE INDEX IF NOT EXISTS idx_jgb_evidence ON jgb_evidence(jgb_id);
