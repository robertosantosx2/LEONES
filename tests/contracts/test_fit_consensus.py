import unittest

from scripts.fit_consensus import build_consensus


class FitConsensusTests(unittest.TestCase):
    def test_agreement_is_external_and_not_measurement(self):
        sources = {
            "llmfit": {"candidates": [{"model_id": "m", "fit_level": "Good"}]},
            "canirun_ai": {"candidates": [{"model_id": "m", "fit": True}]},
            "localmodel_run": {"candidates": [{"model_id": "m", "verdict": "compatible"}]},
        }
        result = build_consensus("m", sources)
        self.assertEqual(result["fit_consensus"], "fit")
        self.assertEqual(result["disagreement"], "AGREE_FIT")
        self.assertEqual(result["measurement"], "not_measured")

    def test_disagreement_is_not_resolved_by_average(self):
        sources = {
            "llmfit": {"candidates": [{"model_id": "m", "fit_level": "Good"}]},
            "canirun_ai": {"candidates": [{"model_id": "m", "fit": False}]},
        }
        result = build_consensus("m", sources)
        self.assertEqual(result["fit_consensus"], "disagreement")
        self.assertEqual(result["disagreement"], "FIT_DISAGREEMENT")
        self.assertEqual(result["measurement"], "not_measured")


if __name__ == "__main__":
    unittest.main()
