"""Store model metadata in Leones Atlas.

This module has one responsibility: persist and retrieve ModelInfo records.
It does not download models and does not execute them.
"""

import sqlite3
from pathlib import Path

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
"""


class ModelStore:
    """Small SQLite persistence layer for model metadata."""

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
