import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "db" / "migrations" / "001_atlas_evidence.sql"


def connection():
    db = sqlite3.connect(":memory:")
    db.executescript(MIGRATION.read_text(encoding="utf-8"))
    return db


def test_storage_tables_exist():
    db = connection()
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"evidence", "atlas_entities", "atlas_entity_evidence", "atlas_lineage", "schema_migrations"}.issubset(names)


def test_atlas_rejects_non_accepted_state():
    db = connection()
    try:
        db.execute("INSERT INTO atlas_entities(entity_id, entity_type, state) VALUES ('x','model','DISCOVERED')")
        db.commit()
        raise AssertionError("Atlas accepted a non-canonical state")
    except sqlite3.IntegrityError:
        pass


def test_evidence_state_is_constrained():
    db = connection()
    try:
        db.execute("INSERT INTO evidence(evidence_id,type,verification_state) VALUES ('e1','benchmark','UNKNOWN')")
        db.commit()
        raise AssertionError("Evidence accepted an unknown verification state")
    except sqlite3.IntegrityError:
        pass


def test_atlas_evidence_link_requires_existing_evidence():
    db = connection()
    db.execute("INSERT INTO atlas_entities(entity_id, entity_type, state) VALUES ('m1','model','ACCEPTED')")
    try:
        db.execute("INSERT INTO atlas_entity_evidence(entity_id,evidence_id) VALUES ('m1','missing')")
        db.commit()
        raise AssertionError("Atlas linked to missing evidence")
    except sqlite3.IntegrityError:
        pass


def test_migration_is_recorded():
    db = connection()
    assert db.execute("SELECT version FROM schema_migrations").fetchone()[0] == "001_atlas_evidence"
