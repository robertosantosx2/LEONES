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


def test_selector_preserves_freetoken_runtime_evidence():
    result = select([freetoken_row()], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1)
    candidate = result["candidates"][0]
    assert candidate["runtime"] == "FreeToken"
    assert candidate["model"]["total_params_b"] == 120.0
    assert candidate["model"]["quantized_weight_gb"] == 10.0
    assert candidate["moe"]["is_moe"] is True
    assert candidate["workload"]["agentic"] is True


def test_selector_to_runtime_selection_accepts_valid_freetoken_candidate():
    selection = select([freetoken_row()], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1)
    result = gate_selection(selection, available_runtimes={"FreeToken"}, hardware=measured_hardware())
    assert result["counts"] == {"plans": 1, "blocked": 0}
    plan = result["execution_plans"][0]
    assert plan["runtime"]["name"] == "FreeToken"
    assert plan["execution_authorized"] is False
    assert plan["measurement_required"] is True
    assert plan["benchmark_probe"] is True


def test_selector_to_runtime_selection_blocks_missing_moe_evidence():
    selection = select([freetoken_row(is_moe="false")], workload="agentic", hardware="contract-cpu", ram_gb=32, top_n=1)
    result = gate_selection(selection, available_runtimes={"FreeToken"}, hardware=measured_hardware())
    assert result["counts"] == {"plans": 0, "blocked": 1}
    assert "specialized for MoE" in result["blocked"][0]["reason"]
