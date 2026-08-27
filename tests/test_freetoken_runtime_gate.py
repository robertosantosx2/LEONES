from scripts.runtime_gate import gate_selection, resolve_runtime


def candidate():
    return {
        "model_id": "qwen/qwen3.6-35b-a3b",
        "model_name": "Qwen3.6-35B-A3B",
        "runtime": "FreeToken",
        "quantization": "NVFP4",
        "selection_status": "BENCHMARK_REQUIRED",
        "optimization_families": [],
        "model": {
            "id": "qwen/qwen3.6-35b-a3b",
            "name": "Qwen3.6-35B-A3B",
            "total_params_b": 35.0,
            "quantized_weight_gb": 20.0,
        },
        "hardware": {
            "ram_gb": 32.0,
            "os": "linux",
            "gpu": "RTX 4060 Laptop",
            "vram_gb": 8.0,
            "host_memory_bandwidth_gbps": 45.0,
            "pcie_h2d_bandwidth_gbps": 11.8,
            "cpu_moe_bandwidth_gbps": 47.5,
        },
        "moe": {"is_moe": True},
        "workload": {"agentic": True},
    }


def test_freetoken_gate_accepts_measured_edge_moe_profile():
    value = candidate()
    plan = resolve_runtime(value, runtime_commands={"FreeToken": ["freetoken"]}, hardware=value["hardware"])
    assert plan["execution_authorized"] is True
    assert plan["benchmark_probe"] is True
    assert plan["hardware"]["pcie_h2d_bandwidth_gbps"] == 11.8


def test_freetoken_gate_blocks_missing_pcie_measurement():
    value = candidate()
    value["hardware"].pop("pcie_h2d_bandwidth_gbps")
    result = gate_selection({"candidates": [value]}, runtime_commands={"FreeToken": ["freetoken"]}, hardware=value["hardware"])
    assert result["counts"] == {"plans": 0, "blocked": 1}
    assert "required measured bandwidth signals are missing" in result["blocked"][0]["reason"]


def test_freetoken_gate_blocks_when_model_fits_in_vram():
    value = candidate()
    value["model"]["quantized_weight_gb"] = 7.0
    result = gate_selection({"candidates": [value]}, runtime_commands={"FreeToken": ["freetoken"]}, hardware=value["hardware"])
    assert result["counts"] == {"plans": 0, "blocked": 1}
    assert "already fits" in result["blocked"][0]["reason"]
