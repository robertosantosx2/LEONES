import pytest

from scripts.freetoken_runtime import evaluate_freetoken_candidate
from scripts.runtime_gate import resolve_runtime, gate_selection


HARDWARE = {
    "ram_gb": 32,
    "vram_gb": 8,
    "host_memory_bandwidth_gbps": 50.0,
    "pcie_h2d_bandwidth_gbps": 12.0,
    "cpu_moe_bandwidth_gbps": 35.0,
}


def freetoken_candidate(**extra):
    value = {
        "model_id": "example/moe-32b",
        "model_name": "Example MoE 32B",
        "runtime": "FreeToken",
        "quantization": "Q4_K_M",
        "selection_status": "TOP_N",
        "rank": 1,
        "fit_score": 0.9,
        "evidence_level": "T3",
        "optimization_families": [],
        "model": {"total_params_b": 32, "quantized_weight_gb": 18},
        "moe": {"is_moe": True},
        "workload": {"agentic": True},
    }
    value.update(extra)
    return value


def test_freetoken_accepts_only_measured_moe_agentic_case():
    decision = evaluate_freetoken_candidate({
        "model": {"total_params_b": 32, "quantized_weight_gb": 18},
        "hardware": HARDWARE,
        "moe": {"is_moe": True},
        "workload": {"agentic": True},
    })
    assert decision["eligible"] is True
    assert decision["missing_signals"] == []


def test_freetoken_resolver_fails_closed_when_bandwidth_evidence_is_missing():
    with pytest.raises(ValueError, match="required measured bandwidth signals are missing"):
        resolve_runtime(freetoken_candidate(), hardware={"ram_gb": 32, "vram_gb": 8})


def test_freetoken_gate_blocks_missing_signals():
    result = gate_selection({"candidates": [freetoken_candidate()]}, hardware={"ram_gb": 32, "vram_gb": 8})
    assert result["counts"] == {"plans": 0, "blocked": 1}
    assert "required measured bandwidth signals are missing" in result["blocked"][0]["reason"]


def test_freetoken_plan_preserves_runtime_eligibility_evidence():
    plan = resolve_runtime(freetoken_candidate(), hardware=HARDWARE, runtime_commands={"FreeToken": ["trusted-freetoken"]})
    assert plan["runtime"]["name"] == "FreeToken"
    assert plan["runtime_eligibility"]["eligible"] is True
    assert plan["execution_authorized"] is True
    assert plan["measured_tps"] is None
