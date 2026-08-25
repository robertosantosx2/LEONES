import unittest
from scripts.runtime_gate import resolve_runtime


class RuntimeSelectionConfigurationTests(unittest.TestCase):
    def test_runtime_plan_contains_category_moe_parameters_and_optimizations(self):
        candidate = {
            "selection_status": "BENCHMARK_REQUIRED",
            "model_id": "example-moe",
            "model_name": "Example MoE",
            "category": "text",
            "moe": {"is_moe": True},
            "model": {"total_params_m": 100000, "active_params_m": 5000},
            "parameter_selection_basis": "active_parameters_m",
            "runtime": "AirLLM",
            "quantization": "4-bit",
            "optimization_families": ["OFFLOAD / STREAMING", "SPARSE / MoE"],
            "workload": {"agentic": False},
            "rank": 1,
            "fit_score": 0.8,
        }
        plan = resolve_runtime(candidate)
        self.assertEqual(plan["category"], "text")
        self.assertEqual(plan["architecture_class"], "moe")
        self.assertEqual(plan["parameters"]["active_parameters_m"], 5000)
        self.assertEqual(plan["parameters"]["selection_basis"], "active_parameters_m")
        self.assertIn("OFFLOAD / STREAMING", plan["optimization_families"])
        self.assertTrue(plan["measurement_required"])
        self.assertIsNone(plan["measured_tps"])


if __name__ == "__main__":
    unittest.main()
