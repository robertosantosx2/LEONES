import unittest

from leones_router import Candidate, rank_candidates, select


class RouterTests(unittest.TestCase):
    def test_measured_performance_beats_estimate(self):
        estimated = Candidate(
            "model-estimated", evidence_ok=True, task_fit=True,
            llmfit_fit=99, runtime_ok=True,
        )
        measured = Candidate(
            "model-measured", evidence_ok=True, task_fit=True,
            llmfit_fit=50, observed_tokens_per_second=20, runtime_ok=True,
        )
        self.assertEqual(select([estimated, measured]).model_id, "model-measured")

    def test_hard_constraints_gate_candidates(self):
        blocked = Candidate(
            "blocked", hard_fit=False, evidence_ok=True, task_fit=True,
            llmfit_fit=100, observed_tokens_per_second=1000, runtime_ok=True,
        )
        viable = Candidate(
            "viable", evidence_ok=True, task_fit=True,
            llmfit_fit=10, runtime_ok=True,
        )
        self.assertEqual(select([blocked, viable]).model_id, "viable")

    def test_missing_measurement_is_not_zero(self):
        unknown = Candidate(
            "unknown", evidence_ok=True, task_fit=True,
            llmfit_fit=90, runtime_ok=True,
        )
        measured = Candidate(
            "measured", evidence_ok=True, task_fit=True,
            llmfit_fit=10, observed_tokens_per_second=1, runtime_ok=True,
        )
        ranked = rank_candidates([unknown, measured])
        self.assertEqual(ranked[0].model_id, "measured")

    def test_empty_selection(self):
        self.assertIsNone(select([]))


if __name__ == "__main__":
    unittest.main()
