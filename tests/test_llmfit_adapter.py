import json
import unittest
from unittest.mock import patch

from automation.discovery.llmfit_adapter import normalize, normalize_candidate, runtime_command, select_candidate


class TestLLMFitAdapter(unittest.TestCase):
    def test_candidate_keeps_estimate_separate_from_measurement(self):
        with patch("automation.discovery.llmfit_adapter.runtime_command", return_value="llama-server"):
            result = normalize_candidate(
                {
                    "name": "meta-llama/Llama-3.2-1B-Instruct",
                    "provider": "Meta",
                    "params_b": 1.2,
                    "estimated_tps": 71.2,
                    "memory_required_gb": 1.3,
                    "fit_level": "Perfect",
                    "runtime": "llamacpp",
                    "best_quant": "Q4_K_M",
                    "installed": True,
                },
                observed_at="2026-08-20T00:00:00+00:00",
            )
        self.assertEqual(result["model_id"], "meta-llama/Llama-3.2-1B-Instruct")
        self.assertEqual(result["estimated_tps"], 71.2)
        self.assertIsNone(result["measured_tps"])
        self.assertEqual(result["fit_level"], "perfect")
        self.assertEqual(result["best_quant"], "Q4_K_M")
        self.assertEqual(result["evidence_status"], "estimated")
        self.assertTrue(result["runtime_available"])

    def test_airllm_capability_requires_both_imports(self):
        with patch("automation.discovery.llmfit_adapter._python_import", side_effect=lambda module: module in {"airllm", "torch"}):
            self.assertEqual(runtime_command("airllm"), "python:airllm")
        with patch("automation.discovery.llmfit_adapter._python_import", return_value=False):
            self.assertIsNone(runtime_command("airllm"))

    def test_normalize_models_shape(self):
        payload = {
            "system": {"cpu": "Intel i5-1035G1", "ram_gb": 7},
            "models": [
                {"id": "example/one", "tps": 20, "quantization": "Q8_0"},
                {"id": "example/two", "tps": 10},
            ],
        }
        with patch("automation.discovery.llmfit_adapter.runtime_command", return_value=None):
            result = normalize(payload, observed_at="2026-08-20T00:00:00+00:00")
        self.assertEqual(result["source"], "llmfit")
        self.assertEqual(result["hardware"]["cpu"], "Intel i5-1035G1")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["estimated_tps"], 20)

    def test_selection_prefers_candidate_that_meets_target(self):
        envelope = {"candidates": [
            {"model_id": "small", "fit_level": "perfect", "score": 95,
             "estimated_tps": 7, "installed": True, "runtime_available": True},
            {"model_id": "target", "fit_level": "good", "score": 90,
             "estimated_tps": 12, "installed": True, "runtime_available": True},
        ]}
        selected = select_candidate(envelope, target_tps=10)
        self.assertEqual(selected["model_id"], "target")

    def test_selection_never_uses_too_tight(self):
        envelope = {"candidates": [{
            "model_id": "unsafe", "fit_level": "too_tight", "score": 100,
            "estimated_tps": 100, "installed": True, "runtime_available": True,
        }]}
        self.assertIsNone(select_candidate(envelope))

    def test_selection_can_require_installed_runtime(self):
        envelope = {"candidates": [{
            "model_id": "not-installed", "fit_level": "perfect", "score": 99,
            "estimated_tps": 50, "installed": False, "runtime_available": True,
        }]}
        self.assertIsNone(select_candidate(envelope, require_installed=True))

    def test_normalize_rejects_unknown_shape(self):
        with self.assertRaises(ValueError):
            normalize({"models": {"unexpected": True}})

    def test_normalized_output_is_json_serializable(self):
        with patch("automation.discovery.llmfit_adapter.runtime_command", return_value=None):
            result = normalize({"results": [{"name": "x", "score": 81}]})
        encoded = json.dumps(result)
        self.assertIn("llmfit", encoded)


if __name__ == "__main__":
    unittest.main()
