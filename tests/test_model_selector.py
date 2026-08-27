import unittest

from scripts.model_selector import SELECTION_STATES, eligibility, select


BASE = {
    "model_id": "example/model",
    "model_name": "Example Model",
    "workload": "general",
    "hardware_id": "Intel i5-1035G1 7GB",
    "estimated_memory_gb": "3.0",
    "weight_memory_gb": "2.5",
    "context_tokens": "8192",
    "runtime": "llama.cpp",
    "quantization": "Q4_K_M",
    "technical_profile_level": "T2",
    "quality_score": "80",
    "tokens_per_second": "12",
    "jgb_level": "4",
}


class TestModelSelector(unittest.TestCase):
    def test_memory_is_hard_gate(self):
        row = dict(BASE, estimated_memory_gb="9")
        ok, reasons, _ = eligibility(row, workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7)
        self.assertFalse(ok)
        self.assertIn("exceeds available", reasons[0])

    def test_evidence_level_is_hard_gate(self):
        row = dict(BASE, technical_profile_level="T1")
        ok, reasons, _ = eligibility(row, workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7)
        self.assertFalse(ok)
        self.assertIn("below T2", reasons[0])

    def test_llmfit_estimate_never_becomes_measurement(self):
        llmfit = {"candidates": [{"model_id": "example/model", "fit_level": "Good", "estimated_tps": 30}]}
        result = select([BASE], workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7,
                        llmfit=llmfit, top_n=1, required_runtime="llama.cpp")
        item = result["candidates"][0]
        self.assertEqual(item["llmfit"]["estimated_tps"], 30)
        self.assertNotIn("measured_tps", item["llmfit"])
        self.assertTrue(result["selection_policy"]["measured_performance_required_for_final_claim"])

    def test_missing_llmfit_marks_top_candidate_for_benchmark(self):
        result = select([BASE], workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7, top_n=1, required_runtime="llama.cpp")
        self.assertEqual(result["candidates"][0]["selection_status"], "BENCHMARK_REQUIRED")

    def test_price_cannot_change_score(self):
        first = select([BASE], workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7, top_n=1, required_runtime="llama.cpp")
        altered = dict(BASE, hardware_price_eur="999999")
        second = select([altered], workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7, top_n=1, required_runtime="llama.cpp")
        self.assertEqual(first["candidates"][0]["fit_score"], second["candidates"][0]["fit_score"])

    def test_rejections_are_explainable_and_states_are_closed(self):
        result = select([dict(BASE, model_id="bad", technical_profile_level="unknown")],
                        workload="general", hardware="Intel i5-1035G1 7GB", ram_gb=7,
                        required_runtime="llama.cpp")
        self.assertEqual(result["rejected"][0]["selection_status"], "REJECTED")
        self.assertTrue(result["rejected"][0]["reasons"])
        self.assertIn(result["rejected"][0]["selection_status"], SELECTION_STATES)


if __name__ == "__main__":
    unittest.main()
