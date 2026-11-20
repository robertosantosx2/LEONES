import unittest

from adapters.buddy import normalize_result as normalize_buddy
from adapters.deepseek_harness import normalize_result as normalize_dsh
from adapters.llmfit import normalize_estimate
from adapters.magnitude import normalize_profile
from adapters.ods import normalize_result as normalize_ods


class AdapterContractTests(unittest.TestCase):
    def test_llmfit_is_explicitly_estimated(self):
        result = normalize_estimate({"fit": 0.9, "speed": 12})
        self.assertEqual(result["llmfit_fit"], 0.9)
        self.assertNotIn("tokens_per_second", result)

    def test_runtime_preserves_measurement(self):
        result = normalize_ods({"tokens_per_second": 11.2})
        self.assertEqual(result["tokens_per_second"], 11.2)

    def test_reference_sources_are_tagged(self):
        self.assertEqual(normalize_profile({})["source"], "magnitude")
        self.assertEqual(normalize_buddy({})["source"], "buddy")
        self.assertEqual(normalize_dsh({})["source"], "deepseek-harness")

    def test_unknown_values_remain_unknown(self):
        result = normalize_dsh({})
        self.assertIsNone(result["outcome"])
        self.assertEqual(result["artifacts"], [])


if __name__ == "__main__":
    unittest.main()
