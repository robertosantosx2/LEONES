import unittest

from scripts.model_selector import select
from scripts.runtime_gate import gate_selection


def freetoken_row(**extra):
    row = {
        "model_id": "example/freetoken-moe",
        "model_name": "example/freetoken-moe",
        "runtime": "FreeToken",
        "quantization": "Q4_K_M",
        "hardware_id": "contract-cpu",
        "workload": "agentic",
        "jgb_level": "4",
        "quality_score": "80",
        "tokens_per_second": "0",
        "estimated_memory_gb": "10",
        "weight_memory_gb": "10",
        "parameters_total_b": "120",
        "technical_profile_level": "T3",
        "context_tokens": "4096",
        "is_moe": "true",
        "agentic": "true",
    }
    row.update(extra)
    return row


def measured_hardware():
    return {
        "ram_gb": 32,
        "vram_gb": 8,
        "host_memory_bandwidth_gbps": 80,
        "pcie_h2d_bandwidth_gbps": 12,
        "cpu_moe_bandwidth_gbps": 40,
    }


class RuntimeSelectionContractTests(unittest.TestCase):
    def test_selector_preserves_freetoken_runtime_evidence(self):
        result = select([freetoken_row()], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1, required_runtime="FreeToken")
        candidate = result["candidates"][0]
        self.assertEqual(candidate["runtime"], "FreeToken")
        self.assertEqual(candidate["model"]["total_params_b"], 120.0)
        self.assertEqual(candidate["model"]["quantized_weight_gb"], 10.0)
        self.assertIs(candidate["moe"]["is_moe"], True)
        self.assertIs(candidate["workload"]["agentic"], True)

    def test_selector_to_runtime_selection_accepts_valid_freetoken_candidate(self):
        selection = select([freetoken_row()], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1, required_runtime="FreeToken")
        result = gate_selection(selection, available_runtimes={"FreeToken"}, hardware=measured_hardware())
        self.assertEqual(result["counts"], {"plans": 1, "blocked": 0})
        plan = result["execution_plans"][0]
        self.assertEqual(plan["runtime"]["name"], "FreeToken")
        self.assertFalse(plan["execution_authorized"])
        self.assertTrue(plan["measurement_required"])
        self.assertTrue(plan["benchmark_probe"])

    def test_selector_to_runtime_selection_blocks_missing_moe_evidence(self):
        selection = select([freetoken_row(is_moe="false")], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1, required_runtime="FreeToken")
        result = gate_selection(selection, available_runtimes={"FreeToken"}, hardware=measured_hardware())
        self.assertEqual(result["counts"], {"plans": 0, "blocked": 1})
        self.assertIn("specialized for MoE", result["blocked"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
