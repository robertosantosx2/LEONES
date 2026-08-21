import unittest

from automation.router.selection_envelope import build_selection_envelope


class TestSelectionEnvelope(unittest.TestCase):
    def test_freezes_measured_selection(self):
        out = build_selection_envelope({
            "candidate_id": "llmfit:x:Q4",
            "model_id": "x",
            "runtime": "airllm",
            "runtime_command": "python:airllm",
            "best_quant": "Q4",
            "estimated_tps": 20,
            "measured_tps": 12,
            "runtime_evidence": {"status": "measured"},
        }, task_id="A01-001", use_case="coding")
        self.assertEqual(out["schema_version"], "leones.runtime-selection.v1")
        self.assertEqual(out["selection_reason"], "measured-runtime-evidence")
        self.assertEqual(out["measured_tps"], 12)

    def test_estimate_fallback_is_explicit(self):
        out = build_selection_envelope({
            "candidate_id": "llmfit:x:Q4",
            "model_id": "x",
            "runtime": "llamacpp",
            "estimated_tps": 20,
            "runtime_evidence": {"status": "ignored"},
        }, task_id="A01-002")
        self.assertEqual(out["selection_reason"], "llmfit-estimate-fallback")
        self.assertIsNone(out["measured_tps"])

    def test_missing_runtime_is_rejected(self):
        with self.assertRaises(ValueError):
            build_selection_envelope({"model_id": "x"}, task_id="A01-003")


if __name__ == "__main__":
    unittest.main()
