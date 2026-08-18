import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


class StorageContractTests(unittest.TestCase):
    def test_atlas_storage_accepts_only_canonical_entities(self):
        schema = load("atlas-storage-v1.json")
        state = schema["properties"]["entity"]["properties"]["state"]["const"]
        required = schema["required"]
        self.assertEqual(state, "ACCEPTED")
        self.assertTrue({"entity", "evidence_refs", "lineage"}.issubset(required))

    def test_atlas_storage_requires_lineage(self):
        schema = load("atlas-storage-v1.json")
        lineage_required = schema["properties"]["lineage"]["required"]
        self.assertIn("source_type", lineage_required)

    def test_evidence_storage_requires_provenance(self):
        schema = load("evidence-storage-v1.json")
        self.assertIn("provenance", schema["required"])
        self.assertIn("source", schema["properties"]["provenance"]["required"])

    def test_storage_contract_versions_are_aligned(self):
        self.assertEqual(load("atlas-storage-v1.json")["properties"]["contract_version"]["const"], "1.0")
        self.assertEqual(load("evidence-storage-v1.json")["properties"]["contract_version"]["const"], "1.0")

    def test_storage_evidence_keeps_verification_states(self):
        schema = load("evidence-storage-v1.json")
        states = schema["properties"]["verification_state"]["enum"]
        self.assertEqual(set(states), {"VERIFIED", "ESTIMATED", "UNVERIFIED", "DISPUTED", "STALE"})


if __name__ == "__main__":
    unittest.main()
