import unittest
from datetime import datetime, timezone, timedelta

from automation.router.runtime_evidence import ranking_signal, rank_candidates


class TestRuntimeEvidenceRouter(unittest.TestCase):
    def test_estimated_evidence_is_ignored(self):
        signal = ranking_signal({"evidence_status": "estimated", "tokens_per_second": 100})
        self.assertEqual(signal["status"], "ignored")
        self.assertEqual(signal["score"], 0.0)

    def test_measured_evidence_gets_freshness_weight(self):
        observed = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        signal = ranking_signal({
            "evidence_status": "measured",
            "tokens_per_second": 20,
            "observed_at": observed,
        })
        self.assertEqual(signal["status"], "measured")
        self.assertGreater(signal["score"], 0.0)
        self.assertLess(signal["score"], 1.0)

    def test_ranking_keeps_estimate_and_measured_separate(self):
        observed = datetime.now(timezone.utc).isoformat()
        ranked = rank_candidates(
            [{"model_id": "a", "estimated_tps": 50}],
            {"a": {"evidence_status": "measured", "tokens_per_second": 8, "observed_at": observed}},
        )
        self.assertEqual(ranked[0]["estimated_tps"], 50)
        self.assertEqual(ranked[0]["measured_tps"], 8)


if __name__ == "__main__":
    unittest.main()
