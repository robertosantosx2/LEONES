import json
import tempfile
import unittest
from pathlib import Path

from automation.discovery.llmfit_adapter import normalize, normalize_candidate


class TestLLMFitAdapter(unittest.TestCase):
    def test_candidate_keeps_estimate_separate_from_measurement(self):
        result = normalize_candidate(
            {
                "model": "meta-llama/Llama-3.2-1B-Instruct",
                "provider": "Meta",
                "params": 1.2,
                "tok_s": 71.2,
                "memory_gb": 1.3,
                "fit": "Perfect",
            },
            observed_at="2026-08-20T00:00:00+00:00",
        )
        self.assertEqual(result["model_id"], "meta-llama/Llama-3.2-1B-Instruct")
        self.assertEqual(result["estimated_tps"], 71.2)
        self.assertIsNone(result["measured_tps"])
        self.assertEqual(result["fit_level"], "Perfect")

    def test_normalize_models_shape(self):
        payload = {
            "system": {"cpu": "Intel i5-1035G1", "ram_gb": 7},
            "models": [
                {"id": "example/one", "tps": 20, "quantization": "Q8_0"},
                {"id": "example/two", "tps": 10},
            ],
        }
        result = normalize(payload, observed_at="2026-08-20T00:00:00+00:00")
        self.assertEqual(result["source"], "llmfit")
        self.assertEqual(result["hardware"]["cpu"], "Intel i5-1035G1")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["estimated_tps"], 20)

    def test_normalize_rejects_unknown_shape(self):
        with self.assertRaises(ValueError):
            normalize({"models": {"unexpected": True}})

    def test_normalized_output_is_json_serializable(self):
        result = normalize({"results": [{"name": "x", "score": 81}]})
        encoded = json.dumps(result)
        self.assertIn("llmfit", encoded)


if __name__ == "__main__":
    unittest.main()
