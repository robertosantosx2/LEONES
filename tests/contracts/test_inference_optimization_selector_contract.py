import unittest
from pathlib import Path


class InferenceOptimizationSelectorContractTests(unittest.TestCase):
    def test_optimization_knowledge_is_published(self):
        path = Path(__file__).parents[2] / "web" / "data" / "inference-optimization.json"
        self.assertTrue(path.exists())

    def test_required_families_are_present(self):
        import json
        path = Path(__file__).parents[2] / "web" / "data" / "inference-optimization.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        families = {x["id"] for x in data["families"]}
        self.assertTrue({
            "quantization", "offload-streaming", "sparse-moe", "cache-decoding",
            "compiled-hardware", "distributed", "experimental"
        } <= families)

    def test_selector_order_is_the_frozen_rc3_order(self):
        import json
        path = Path(__file__).parents[2] / "web" / "data" / "inference-optimization.json"
        order = json.loads(path.read_text(encoding="utf-8"))["selector_order"]
        self.assertEqual(
            order,
            [
                "hermes_discovery",
                "hardware_profile.v1",
                "candidate-set.v1",
                "external_model_evidence",
                "deterministic_model_ranking",
                "user_model_choice",
                "user_stack_choice",
                "runtime-selection.v1",
                "use_case",
                "hardware",
                "estimators",
                "BENCHMARK",
                "measurement",
                "evidence",
                "recommendation",
            ],
        )

    def test_moe_rule_is_explicit(self):
        import json
        path = Path(__file__).parents[2] / "web" / "data" / "inference-optimization.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("active_parameters_m", data["moe_rule"])
        self.assertIn("total_parameters_m", data["moe_rule"])


if __name__ == "__main__":
    unittest.main()
