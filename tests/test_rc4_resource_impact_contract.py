from runtime_selection.resource_impact import evaluate_resource_impact


def test_resource_impact_is_always_present_and_separates_estimate_from_measurement():
    result = evaluate_resource_impact(
        model_evidence={
            "hf": {
                "parameters_b": 7.0,
                "used_storage_bytes": 7 * 1024**3,
                "context_window_tokens": 8192,
            }
        },
        hardware={"ram_gb": 16, "vram_gb": 8},
        fit={"bits_per_weight": 4.5},
        context_tokens=8192,
    )

    assert result["always_present"] is True
    assert result["install"]["artifact_size_gb"] == 7.0
    assert result["install"]["disk_space_required_gb"] > 7.0
    assert result["runtime"]["measured"] is False
    assert result["runtime"]["estimated_peak_memory_gb"] is not None
    assert result["consumption"]["cpu_utilization_percent"] is None
    assert result["consumption"]["gpu_utilization_percent"] is None
    assert result["consumption"]["power_watts"] is None


def test_resource_impact_does_not_invent_unknown_values():
    result = evaluate_resource_impact(
        model_evidence={"hf": {}},
        hardware={},
        fit={},
    )

    assert result["install"]["artifact_size_gb"] is None
    assert result["install"]["disk_space_required_gb"] is None
    assert result["runtime"]["estimated_peak_memory_gb"] is None
    assert result["hardware_capacity"]["ram_available_gb"] is None
    assert result["hardware_capacity"]["vram_available_gb"] is None
    assert result["decision"] == "resource_data_incomplete"
