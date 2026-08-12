"""Store model metadata and evidence in Leones Atlas.

This module has one responsibility: persist and retrieve Atlas records.
It does not download models and does not execute them.
"""

import sqlite3
from pathlib import Path

from .atlas_evidence import Evidence
from .model import ModelInfo


SCHEMA = """
CREATE TABLE IF NOT EXISTS model_catalog (
    model_id TEXT PRIMARY KEY,
    family TEXT,
    revision TEXT,
    format TEXT,
    quantization TEXT,
    size_gb REAL,
    capabilities TEXT NOT NULL DEFAULT '',
    license TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS model_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'external-unvalidated',
    reviewer TEXT,
    reviewed_at TEXT,
    notes TEXT,
    FOREIGN KEY(model_id) REFERENCES model_catalog(model_id)
);
"""


class ModelStore:
    """Small SQLite persistence layer for Atlas metadata and evidence."""

    def __init__(self, atlas_path: str | Path) -> None:
        self.path = Path(atlas_path)
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA)

    def add(self, model: ModelInfo) -> None:
        """Insert or replace one model record."""
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT OR REPLACE INTO model_catalog
                (model_id, family, revision, format, quantization, size_gb,
                 capabilities, license, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model.model_id, model.family, model.revision, model.format,
                    model.quantization, model.size_gb, model.capabilities_text(),
                    model.license, model.source,
                ),
            )

    def get(self, model_id: str) -> ModelInfo | None:
        """Return one model by ID, or None when it is not registered."""
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT model_id, family, revision, format, quantization, size_gb, capabilities, license, source FROM model_catalog WHERE model_id = ?",
                (model_id,),
            ).fetchone()
        if row is None:
            return None
        return ModelInfo(
            model_id=row[0], family=row[1], revision=row[2], format=row[3],
            quantization=row[4], size_gb=row[5],
            capabilities=tuple(filter(None, row[6].split(","))),
            license=row[7], source=row[8],
        )

    def add_evidence(
        self,
        model_id: str,
        evidence: Evidence,
        reviewer: str | None = None,
        reviewed_at: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Store evidence without changing its declared status."""
        with sqlite3.connect(self.path) as db:
            exists = db.execute(
                "SELECT 1 FROM model_catalog WHERE model_id = ?", (model_id,)
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown model: {model_id}")
            db.execute(
                """INSERT INTO model_evidence
                (model_id, source, evidence_type, source_type, status,
                 reviewer, reviewed_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model_id, evidence.source, evidence.evidence_type,
                    evidence.source_type, evidence.status, reviewer,
                    reviewed_at, notes,
                ),
            )

    def evidence(self, model_id: str) -> list[Evidence]:
        """Return evidence records for one model."""
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT source, evidence_type, source_type, status FROM model_evidence WHERE model_id = ? ORDER BY evidence_id",
                (model_id,),
            ).fetchall()
        return [Evidence(*row) for row in rows]
