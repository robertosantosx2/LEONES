import unittest

from scripts.router import route_recommendation


class RouterContractTests(unittest.TestCase):
    def recommendation(self, **extra):
        item = {
            "model_id": "demo/model",
            "runtime": "FreeToken",
            "selection_status": "BENCHMARK_REQUIRED",
            "evidence_refs": ["exec-42", "atlas:model/demo"],
        }
        item.update(extra)
        return item

    def test_router_accepts_traceable_measured_recommendation(self):
        result = route_recommendation(self.recommendation(), osi_mode="OPEN_ALL")
        self.assertTrue(result["router"]["read_only"])
        self.assertTrue(result["router"]["evidence_traceable"])
        self.assertEqual(result["evidence_refs"], ["exec-42", "atlas:model/demo"])

    def test_router_supports_copyleft_check_mode(self):
        result = route_recommendation(self.recommendation(), osi_mode="FORCE_COPYLEFT_CHECK")
        self.assertEqual(result["router"]["osi_mode"], "FORCE_COPYLEFT_CHECK")

    def test_router_rejects_missing_evidence(self):
        with self.assertRaisesRegex(ValueError, "evidence_refs"):
            route_recommendation(self.recommendation(evidence_refs=[]))

    def test_router_rejects_unknown_osi_mode(self):
        with self.assertRaisesRegex(ValueError, "unsupported osi_mode"):
            route_recommendation(self.recommendation(), osi_mode="NOT_A_MODE")

    def test_router_cannot_write_atlas(self):
        with self.assertRaisesRegex(ValueError, "read-only"):
            route_recommendation(self.recommendation(action="ATLAS_WRITE"))

    def test_router_does_not_mutate_input(self):
        original = self.recommendation()
        route_recommendation(original)
        self.assertNotIn("router", original)


if __name__ == "__main__":
    unittest.main()
