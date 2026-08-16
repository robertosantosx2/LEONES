"""Canonical Atlas repository over the SQLite storage contract."""

import json
import sqlite3
from pathlib import Path
from typing import Any

MIGRATION = Path(__file__).resolve().parents[2] / "db" / "migrations" / "001_atlas_evidence.sql"

class AtlasRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))

    def get(self, entity_id: str):
        row = self.db.execute("SELECT entity_id, entity_type, state, version, attributes_json, promotion_id FROM atlas_entities WHERE entity_id = ?", (entity_id,)).fetchone()
        if row is None:
            return None
        evidence = [r[0] for r in self.db.execute("SELECT evidence_id FROM atlas_entity_evidence WHERE entity_id = ? ORDER BY evidence_id", (entity_id,))]
        return {"entity_id": row[0], "entity_type": row[1], "state": row[2], "version": row[3], "attributes": json.loads(row[4]), "promotion_id": row[5], "evidence_refs": evidence}

    def list_by_type(self, entity_type: str):
        return [self.get(row[0]) for row in self.db.execute("SELECT entity_id FROM atlas_entities WHERE entity_type = ? ORDER BY entity_id", (entity_type,))]

    def link_evidence(self, entity_id: str, evidence_id: str):
        self.db.execute("INSERT INTO atlas_entity_evidence(entity_id, evidence_id) VALUES (?, ?)", (entity_id, evidence_id))
        self.db.commit()

    def create_canonical(self, entity: dict[str, Any], evidence_refs: list[str], lineage: dict[str, Any]):
        if entity.get("state") != "ACCEPTED":
            raise ValueError("ATLAS_REQUIRES_ACCEPTED_STATE")
        if not evidence_refs:
            raise ValueError("ATLAS_REQUIRES_EVIDENCE")
        self.db.execute("INSERT INTO atlas_entities(entity_id, contract_version, entity_type, state, version, attributes_json, promotion_id) VALUES (?, '1.0', ?, 'ACCEPTED', ?, ?, ?)", (entity["entity_id"], entity["entity_type"], entity.get("version"), json.dumps(entity.get("attributes", {}), ensure_ascii=False), lineage.get("promotion_id")))
        for evidence_id in evidence_refs:
            self.link_evidence(entity["entity_id"], evidence_id)
        self.db.execute("INSERT INTO atlas_lineage(entity_id, source_type, parent_entity_id, promotion_id) VALUES (?, ?, ?, ?)", (entity["entity_id"], lineage["source_type"], lineage.get("parent_entity_id"), lineage.get("promotion_id")))
        self.db.commit()
