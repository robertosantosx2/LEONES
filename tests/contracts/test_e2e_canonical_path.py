import unittest

from benchmarks.evidence.runtime_selection_evidence import build_runtime_feedback
from scripts.model_selector import select


class CanonicalE2EContractTests(unittest.TestCase):
    def test_measured_feedback_returns_to_selector(self):
        row = {
            "model_id": "demo/model",
            "model_name": "demo/model",
            "runtime": "FreeToken",
            "quantization": "Q4_K_M",
            "hardware_id": "contract-cpu",
            "workload": "agentic",
            "jgb_level": "4",
            "quality_score": "80",
            "tokens_per_second": "2",
            "estimated_memory_gb": "10",
            "weight_memory_gb": "10",
            "technical_profile_level": "T3",
            "context_tokens": "4096",
            "is_moe": "true",
            "agentic": "true",
        }
        selected = select(
            [row],
            workload="agentic",
            hardware="contract-cpu",
            ram_gb=32,
            top_n=1,
            required_runtime="FreeToken",
        )
        candidate = selected["candidates"][0]

        measured = build_runtime_feedback(
            {
                "evidence": {
                    "evidence_type": "measured",
                    "execution_id": "exec-e2e-001",
                    "source": "A01",
                    "measured_at": "2026-08-24T00:00:00Z",
                },
                "model": {"id": candidate["model_id"], "revision": "r1"},
                "hardware": {"ram_gb": 32},
                "agentic": {
                    "runtime": {"name": candidate["runtime"]},
                    "metrics": {
                        "measured_tps": 14.0,
                        "runtime_wall_seconds": 3.0,
                    },
                },
            }
        )

        self.assertEqual(measured["evidence_type"], "measured")
        self.assertTrue(measured["selector_feedback"]["replace_estimate"])
        self.assertEqual(measured["execution_id"], "exec-e2e-001")


if __name__ == "__main__":
    unittest.main()
