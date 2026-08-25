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

    def test_selector_order_puts_optimization_before_estimators(self):
        import json
        path = Path(__file__).parents[2] / "web" / "data" / "inference-optimization.json"
        order = json.loads(path.read_text(encoding="utf-8"))["selector_order"]
        self.assertLess(order.index("use_case"), order.index("estimators"))
        self.assertLess(order.index("hardware"), order.index("estimators"))
        self.assertLess(order.index("runtime"), order.index("estimators"))
        self.assertLess(order.index("optimization"), order.index("estimators"))
        self.assertLess(order.index("dense_or_moe"), order.index("candidate_models"))

    def test_moe_rule_is_explicit(self):
        import json
        path = Path(__file__).parents[2] / "web" / "data" / "inference-optimization.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("active_parameters_m", data["moe_rule"])
        self.assertIn("total_parameters_m", data["moe_rule"])


if __name__ == "__main__":
    unittest.main()
