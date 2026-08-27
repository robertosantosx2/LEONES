from scripts.select_from_hardware_profile import available_memory_gb, select_from_profile


def profile():
    return {
        "cpu": {"model": "Intel Core i5-1035G1"},
        "memory": {"available_bytes": 7 * 1024**3, "total_bytes": 8 * 1024**3},
    }


def row(**extra):
    value = {
        "model_id": "org/model",
        "model_name": "Model",
        "workload": "chat",
        "hardware_id": "",
        "technical_profile_level": "T3",
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
        "estimated_memory_gb": "4",
        "context_tokens": "4096",
        "quality_score": "80",
        "tokens_per_second": "10",
        "jgb_level": "4",
    }
    value.update(extra)
    return value


def test_available_memory_is_observed_not_invented():
    assert round(available_memory_gb(profile()), 1) == 7.0


def test_profile_feeds_canonical_selector():
    result = select_from_profile(profile(), [row()], workload="chat", required_runtime="llama.cpp")
    assert result["selector"] == "LEONES-model-selection"
    assert result["selection_policy"]["ram_gb"] == 7.0
    assert result["counts"]["eligible"] == 1


def test_model_over_available_memory_is_rejected():
    result = select_from_profile(profile(), [row(estimated_memory_gb="8")], workload="chat", required_runtime="llama.cpp")
    assert result["counts"]["rejected"] == 1
