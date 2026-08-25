import unittest
from scripts.inference_config import resolve_inference_configuration
from scripts.model_selector import select


class InferencePreselectionTests(unittest.TestCase):
    def test_configuration_is_created_before_model_selection(self):
        config = resolve_inference_configuration(
            workload="coding",
            hardware={"cpu":"Intel i7","ram_gb":32,"vram_gb":8},
            runtime="llama.cpp",
            optimizations=["QUANTIZATION", "OFFLOAD / STREAMING"],
            context_tokens=8192,
        )
        self.assertEqual(config["decision_status"], "configuration_preselected")
        self.assertEqual(config["runtime"], "llama.cpp")
        self.assertEqual(config["measurement"], "not_measured")

    def test_model_selection_cannot_start_without_runtime(self):
        with self.assertRaises(ValueError):
            select([], workload="coding", hardware="Intel i7", ram_gb=32)


if __name__ == "__main__":
    unittest.main()
