from scripts.freetoken_runtime import evaluate_freetoken_candidate


def _candidate(**overrides):
    value = {
        "model": {
            "total_params_b": 35.0,
            "quantized_weight_gb": 20.0,
        },
        "hardware": {
            "vram_gb": 8.0,
            "ram_gb": 32.0,
            "host_memory_bandwidth_gbps": 45.0,
            "pcie_h2d_bandwidth_gbps": 11.8,
            "cpu_moe_bandwidth_gbps": 47.5,
        },
        "moe": {"is_moe": True},
        "workload": {"agentic": True},
    }
    value.update(overrides)
    return value


def test_freetoken_requires_measured_bandwidth_signals():
    candidate = _candidate()
    candidate["hardware"].pop("pcie_h2d_bandwidth_gbps")
    decision = evaluate_freetoken_candidate(candidate)
    assert not decision["eligible"]
    assert "pcie_h2d_bandwidth_gbps" in decision["missing_signals"]


def test_freetoken_rejects_non_moe():
    decision = evaluate_freetoken_candidate(_candidate(moe={"is_moe": False}))
    assert not decision["eligible"]
    assert any("MoE" in reason for reason in decision["reasons"])


def test_freetoken_rejects_when_model_fits_in_vram():
    candidate = _candidate()
    candidate["model"]["quantized_weight_gb"] = 7.0
    decision = evaluate_freetoken_candidate(candidate)
    assert not decision["eligible"]
    assert any("already fits" in reason for reason in decision["reasons"])


def test_freetoken_accepts_edge_moe_profile():
    decision = evaluate_freetoken_candidate(_candidate())
    assert decision["eligible"]
    assert decision["runtime_class"] == "edge-moe-bandwidth-adaptive"
