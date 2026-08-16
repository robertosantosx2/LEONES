"""Evidence repository over the SQLite storage contract."""

import json
import sqlite3
from pathlib import Path
from typing import Any

MIGRATION = Path(__file__).resolve().parents[2] / "db" / "migrations" / "001_atlas_evidence.sql"

class EvidenceRepository:
    VALID_STATES = {"VERIFIED", "ESTIMATED", "UNVERIFIED", "DISPUTED", "STALE"}

    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))

    def get(self, evidence_id: str):
        row = self.db.execute("SELECT evidence_id, type, verification_state, source, observed_at, collected_at, methodology, artifact_ref, claims_json, trace_id, run_id FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if row is None:
            return None
        return {"evidence_id": row[0], "type": row[1], "verification_state": row[2], "provenance": {"source": row[3], "observed_at": row[4], "collected_at": row[5], "methodology": row[6], "artifact_ref": row[7]}, "claims": json.loads(row[8]), "trace_id": row[9], "run_id": row[10]}

    def create(self, evidence: dict[str, Any]):
        state = evidence.get("verification_state")
        if state not in self.VALID_STATES:
            raise ValueError("INVALID_EVIDENCE_STATE")
        provenance = evidence.get("provenance", {})
        self.db.execute("INSERT INTO evidence(evidence_id, contract_version, type, verification_state, source, observed_at, collected_at, methodology, artifact_ref, claims_json, trace_id, run_id) VALUES (?, '1.0', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (evidence["evidence_id"], evidence["type"], state, provenance.get("source"), provenance.get("observed_at"), provenance.get("collected_at"), provenance.get("methodology"), provenance.get("artifact_ref"), json.dumps(evidence.get("claims", []), ensure_ascii=False), evidence.get("trace_id"), evidence.get("run_id")))
        self.db.commit()

    def list_by_state(self, state: str):
        if state not in self.VALID_STATES:
            raise ValueError("INVALID_EVIDENCE_STATE")
        return [self.get(row[0]) for row in self.db.execute("SELECT evidence_id FROM evidence WHERE verification_state = ? ORDER BY evidence_id", (state,))]
