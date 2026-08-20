import unittest

from llmfit_adapter import attach_provenance, normalize_candidate, normalize_response


class LLMFitAdapterTests(unittest.TestCase):
    def test_normalize_candidate_preserves_estimates(self):
        candidate = normalize_candidate({"name": "example", "score": 87, "estimated_tps": 12.5, "quant": "Q4_K_M"})
        self.assertEqual(candidate.model, "example")
        self.assertEqual(candidate.llmfit_score, 87)
        self.assertEqual(candidate.llmfit_speed_estimate, 12.5)
        self.assertEqual(candidate.llmfit_quantization, "Q4_K_M")

    def test_normalize_response(self):
        result = normalize_response({"models": [{"model": "a"}, {"name": "b"}]})
        self.assertEqual([item["model"] for item in result], ["a", "b"])

    def test_provenance_marks_values_as_estimated(self):
        result = attach_provenance([{"model": "a"}], "test-version")
        self.assertEqual(result[0]["llmfit_source_version"], "test-version")
        self.assertEqual(result[0]["estimate_status"], "estimated")


if __name__ == "__main__":
    unittest.main()
