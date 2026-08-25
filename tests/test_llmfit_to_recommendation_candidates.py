import unittest

from scripts.llmfit_to_recommendation_candidates import build_candidates


class TestLLMFitToRecommendationCandidates(unittest.TestCase):
    def feed(self):
        return [{
            "model_id": "org/model",
            "model_name": "Model",
            "workload": "chat",
            "hardware_id": "i5",
            "technical_profile_level": "T2",
            "runtime": "llama.cpp",
            "quantization": "Q4_K_M",
            "estimated_memory_gb": "4",
            "context_tokens": "4096",
            "quality_score": "80",
            "tokens_per_second": "12",
            "jgb_level": "4",
        }]

    def test_estimate_is_preserved_and_measurement_stays_null(self):
        result = build_candidates(
            feed=self.feed(),
            llmfit_payload={"models": [{"id": "org/model", "tps": 31.5, "fit": "Perfect"}]},
            workload="chat", hardware="i5", ram_gb=8, context_tokens=4096, top_n=1,
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["llmfit"]["estimated_tps"], 31.5)
        self.assertEqual(candidate["llmfit_provenance"]["estimated_tps"], 31.5)
        self.assertIsNone(candidate["llmfit_provenance"]["measured_tps"])
        self.assertTrue(result["llmfit_provenance"]["estimate_only"])

    def test_llmfit_can_reject_when_required(self):
        result = build_candidates(
            feed=self.feed(),
            llmfit_payload={"models": [{"id": "org/model", "fit": "No"}]},
            workload="chat", hardware="i5", ram_gb=8, context_tokens=4096,
            top_n=1, require_llmfit_fit=True,
        )
        self.assertEqual(result["counts"]["eligible"], 0)
        self.assertEqual(result["counts"]["rejected"], 1)

    def test_external_estimate_never_becomes_measured_tps(self):
        result = build_candidates(
            feed=self.feed(),
            llmfit_payload={"models": [{"id": "org/model", "tokens_per_second": 99}]},
            workload="chat", hardware="i5", ram_gb=8, context_tokens=4096, top_n=1,
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["llmfit"]["estimated_tps"], 99)
        self.assertIsNone(candidate["llmfit_provenance"]["measured_tps"])


if __name__ == "__main__":
    unittest.main()
