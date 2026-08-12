"""SQLite-backed Leones Atlas store (minimal v0.2 implementation)."""

import sqlite3
from pathlib import Path

from .core.contracts import HardwareProfile, ModelCandidate

SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    revision TEXT,
    quantization TEXT,
    formats TEXT NOT NULL DEFAULT '',
    capabilities TEXT NOT NULL DEFAULT ''
);
"""


class SQLiteAtlas:
    def __init__(self, path: str | Path = "leones_atlas.sqlite") -> None:
        self.path = Path(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(SCHEMA)

    def add_model(self, model: ModelCandidate) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO models(model_id, revision, quantization, formats, capabilities) VALUES (?, ?, ?, ?, ?)",
                (
                    model.model_id,
                    model.revision,
                    model.quantization,
                    ",".join(model.formats),
                    ",".join(model.capabilities),
                ),
            )

    def candidates(self, hardware: HardwareProfile) -> list[ModelCandidate]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT model_id, revision, quantization, formats, capabilities FROM models"
            ).fetchall()
        return [
            ModelCandidate(
                model_id=row[0],
                revision=row[1],
                quantization=row[2],
                formats=tuple(filter(None, row[3].split(","))),
                capabilities=tuple(filter(None, row[4].split(","))),
            )
            for row in rows
        ]
