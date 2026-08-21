import unittest

from automation.evidence.runtime_benchmark import promote


class TestRuntimeBenchmarkEvidence(unittest.TestCase):
    def test_estimate_never_becomes_measured(self):
        result = promote({
            "schema_version": "leones.runtime-benchmark.v1",
            "selected": {"model_id": "x", "estimated_tps": 20, "best_quant": "Q4"},
            "benchmark": {"status": "not_run", "evidence_status": "unknown"},
        })
        self.assertEqual(result["evidence_status"], "unknown")
        self.assertEqual(result["tokens_per_second"], None)

    def test_physical_generation_becomes_measured(self):
        result = promote({
            "schema_version": "leones.runtime-benchmark.v1",
            "selected": {"model_id": "x", "estimated_tps": 20, "best_quant": "Q4"},
            "benchmark": {
                "status": "measured", "evidence_status": "measured",
                "runtime": "airllm", "model": "x",
                "result": {
                    "observed_at": "2026-08-21T00:00:00+00:00",
                    "tokens_per_second": 12.5,
                    "generated_tokens": 32,
                    "generation_seconds": 2.56,
                    "measurement_scope": "single local generation"
                }
            }
        })
        self.assertEqual(result["evidence_status"], "measured")
        self.assertEqual(result["tokens_per_second"], 12.5)
        self.assertEqual(result["provenance"]["llmfit_estimate"], 20)

    def test_failed_run_is_not_measurement(self):
        result = promote({
            "benchmark": {"status": "failed", "evidence_status": "unknown"}
        })
        self.assertEqual(result["evidence_status"], "failed")


if __name__ == "__main__":
    unittest.main()
