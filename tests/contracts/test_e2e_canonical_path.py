import unittest

from scripts.model_selector import select
from benchmarks.evidence.runtime_selection_evidence import build_runtime_feedback
from scripts.router import route_recommendation


class CanonicalE2EContractTests(unittest.TestCase):
    def test_measured_feedback_can_return_to_selector_and_router(self):
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
        selected = select([row], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1)
        candidate = selected["candidates"][0]

        measured = build_runtime_feedback({
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
                "metrics": {"measured_tps": 14.0, "runtime_wall_seconds": 3.0},
            },
        })

        self.assertEqual(measured["evidence_type"], "measured")
        self.assertTrue(measured["selector_feedback"]["replace_estimate"])

        routed = route_recommendation({
            "model_id": candidate["model_id"],
            "runtime": candidate["runtime"],
            "selection_status": candidate["selection_status"],
            "evidence_refs": [measured["execution_id"], "atlas:model/demo"],
        })
        self.assertTrue(routed["router"]["read_only"])
        self.assertTrue(routed["router"]["evidence_traceable"])
        self.assertEqual(routed["evidence_refs"][0], "exec-e2e-001")

    def test_canonical_path_has_no_knowledge_write_operation(self):
        with self.assertRaisesRegex(ValueError, "read-only"):
            route_recommendation({
                "model_id": "demo/model",
                "evidence_refs": ["exec-1"],
                "action": "ATLAS_WRITE",
            })


if __name__ == "__main__":
    unittest.main()
