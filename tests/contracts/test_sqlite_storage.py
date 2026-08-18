import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "db" / "migrations" / "001_atlas_evidence.sql"


def connection():
    db = sqlite3.connect(":memory:")
    db.executescript(MIGRATION.read_text(encoding="utf-8"))
    return db


class SQLiteStorageTests(unittest.TestCase):
    def test_storage_tables_exist(self):
        db = connection()
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"evidence", "atlas_entities", "atlas_entity_evidence", "atlas_lineage", "schema_migrations"}.issubset(names))
        db.close()

    def test_atlas_rejects_non_accepted_state(self):
        db = connection()
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO atlas_entities(entity_id, entity_type, state) VALUES ('x','model','DISCOVERED')")
            db.commit()
        db.close()

    def test_evidence_state_is_constrained(self):
        db = connection()
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO evidence(evidence_id,type,verification_state) VALUES ('e1','benchmark','UNKNOWN')")
            db.commit()
        db.close()

    def test_atlas_evidence_link_requires_existing_evidence(self):
        db = connection()
        db.execute("INSERT INTO atlas_entities(entity_id, entity_type, state) VALUES ('m1','model','ACCEPTED')")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO atlas_entity_evidence(entity_id,evidence_id) VALUES ('m1','missing')")
            db.commit()
        db.close()

    def test_migration_is_recorded(self):
        db = connection()
        self.assertEqual(db.execute("SELECT version FROM schema_migrations").fetchone()[0], "001_atlas_evidence")
        db.close()


if __name__ == "__main__":
    unittest.main()
