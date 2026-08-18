import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


class SemanticContractTests(unittest.TestCase):
    def test_promotion_requires_quality_pass_and_osi(self):
        schema = load("promotion-quality-gate-v1.json")
        rules = schema["allOf"]
        self.assertTrue(rules)
        then = rules[0]["then"]["properties"]["quality_gate"]["properties"]
        self.assertEqual(then["state"]["const"], "PASS")
        self.assertEqual(set(then["osi_state"]["enum"]), {"NOT_REQUIRED", "PASS"})

    def test_router_only_exposes_allowed_osi_modes(self):
        schema = load("atlas-router-contract-v1.json")
        modes = schema["properties"]["request"]["properties"]["osi_mode"]["enum"]
        self.assertEqual(modes, ["OPEN_ALL", "FORCE_COPYLEFT_CHECK"])

    def test_evidence_states_keep_estimated_distinct_from_verified(self):
        schema = load("atlas-evidence-contract-v1.json")
        states = schema["properties"]["evidence"]["items"]["properties"]["verification_state"]["enum"]
        self.assertIn("ESTIMATED", states)
        self.assertIn("VERIFIED", states)
        self.assertNotEqual(states.index("ESTIMATED"), states.index("VERIFIED"))

    def test_router_recommendation_requires_evidence_and_uncertainty(self):
        schema = load("atlas-router-contract-v1.json")
        required = schema["properties"]["recommendation"]["required"]
        self.assertIn("evidence_refs", required)
        self.assertIn("uncertainty", required)

    def test_canonical_writer_is_not_part_of_router_contract(self):
        schema = load("atlas-router-contract-v1.json")
        serialized = json.dumps(schema, sort_keys=True)
        self.assertNotIn("ATLAS_WRITE", serialized)

    def test_contract_versions_are_aligned(self):
        names = [
            "atlas-evidence-contract-v1.json",
            "promotion-quality-gate-v1.json",
            "atlas-router-contract-v1.json",
        ]
        versions = {load(name)["properties"]["contract_version"]["const"] for name in names}
        self.assertEqual(versions, {"1.0"})


if __name__ == "__main__":
    unittest.main()
