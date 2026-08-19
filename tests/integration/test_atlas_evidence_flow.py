import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "db" / "migrations" / "001_atlas_evidence.sql"


class AtlasEvidenceFlowTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))

    def tearDown(self):
        self.db.close()

    def add_evidence(self, evidence_id="ev-1", state="VERIFIED"):
        self.db.execute(
            "INSERT INTO evidence(evidence_id,type,verification_state,source) VALUES (?,?,?,?)",
            (evidence_id, "benchmark", state, "test"),
        )

    def add_accepted_entity(self, entity_id="model-1", evidence_id="ev-1", promotion_id="promo-1"):
        self.db.execute(
            "INSERT INTO atlas_entities(entity_id,entity_type,state,promotion_id) VALUES (?,?,?,?)",
            (entity_id, "model", "ACCEPTED", promotion_id),
        )
        self.db.execute(
            "INSERT INTO atlas_entity_evidence(entity_id,evidence_id) VALUES (?,?)",
            (entity_id, evidence_id),
        )

    def test_evidence_can_become_atlas_only_when_referenced(self):
        self.add_evidence()
        self.db.execute(
            "INSERT INTO atlas_entities(entity_id,entity_type,state,promotion_id) VALUES (?,?,?,?)",
            ("model-1", "model", "ACCEPTED", "promo-1"),
        )
        self.db.execute(
            "INSERT INTO atlas_entity_evidence(entity_id,evidence_id) VALUES (?,?)",
            ("model-1", "ev-1"),
        )
        row = self.db.execute(
            "SELECT e.evidence_id FROM atlas_entity_evidence ae JOIN evidence e ON e.evidence_id=ae.evidence_id WHERE ae.entity_id=?",
            ("model-1",),
        ).fetchone()
        self.assertEqual(row[0], "ev-1")

    def test_atlas_cannot_reference_missing_evidence(self):
        self.db.execute(
            "INSERT INTO atlas_entities(entity_id,entity_type,state,promotion_id) VALUES (?,?,?,?)",
            ("model-1", "model", "ACCEPTED", "promo-1"),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO atlas_entity_evidence(entity_id,evidence_id) VALUES (?,?)",
                ("model-1", "missing"),
            )

    def test_atlas_rejects_noncanonical_state(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO atlas_entities(entity_id,entity_type,state,promotion_id) VALUES (?,?,?,?)",
                ("model-1", "model", "REVIEW", "promo-1"),
            )

    def test_estimated_evidence_remains_estimated(self):
        self.add_evidence(state="ESTIMATED")
        state = self.db.execute(
            "SELECT verification_state FROM evidence WHERE evidence_id='ev-1'"
        ).fetchone()[0]
        self.assertEqual(state, "ESTIMATED")
        self.assertNotEqual(state, "VERIFIED")

    def test_lineage_requires_existing_parent_when_present(self):
        self.add_evidence()
        self.add_accepted_entity()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO atlas_lineage(entity_id,source_type,parent_entity_id,promotion_id) VALUES (?,?,?,?)",
                ("model-1", "fine_tune", "missing-parent", "promo-1"),
            )

    def test_promotion_id_is_preserved(self):
        self.add_evidence()
        self.add_accepted_entity(promotion_id="promo-42")
        value = self.db.execute(
            "SELECT promotion_id FROM atlas_entities WHERE entity_id='model-1'"
        ).fetchone()[0]
        self.assertEqual(value, "promo-42")


if __name__ == "__main__":
    unittest.main()
