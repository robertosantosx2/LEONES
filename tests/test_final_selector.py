import unittest
from datetime import datetime, timezone

from automation.router.final_selector import select


class TestFinalSelector(unittest.TestCase):
    def test_measured_candidate_wins_without_rewriting_estimate(self):
        candidates = [
            {"model_id": "a", "fit_level": "good", "runtime_available": True, "score": 90, "estimated_tps": 40},
            {"model_id": "b", "fit_level": "good", "runtime_available": True, "score": 80, "estimated_tps": 20},
        ]
        evidence = {
            "b": {"evidence_status": "measured", "tokens_per_second": 15,
                  "observed_at": datetime.now(timezone.utc).isoformat()}
        }
        result = select(candidates, evidence)
        self.assertEqual(result["model_id"], "b")
        self.assertEqual(result["estimated_tps"], 20)
        self.assertEqual(result["measured_tps"], 15)

    def test_without_measurements_falls_back_to_llmfit(self):
        result = select([
            {"model_id": "a", "fit_level": "good", "runtime_available": True, "score": 90, "estimated_tps": 40},
            {"model_id": "b", "fit_level": "good", "runtime_available": True, "score": 80, "estimated_tps": 20},
        ])
        self.assertEqual(result["model_id"], "a")
        self.assertIsNone(result["measured_tps"])

    def test_rejects_unusable_candidates(self):
        self.assertIsNone(select([
            {"model_id": "x", "fit_level": "marginal", "runtime_available": True},
            {"model_id": "y", "fit_level": "good", "runtime_available": False},
        ]))


if __name__ == "__main__":
    unittest.main()
