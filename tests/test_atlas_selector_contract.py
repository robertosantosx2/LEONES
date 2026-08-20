from scripts.atlas_recommend_from_feed import recommend


def row(**extra):
    value = {
        "model_id": "org/model",
        "model_name": "Model",
        "workload": "chat",
        "hardware_id": "i5-1035G1",
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


def test_atlas_delegates_to_canonical_selector():
    result = recommend([row()], workload="chat", hardware="i5-1035G1", ram=8, vram=0, context=4096, top_n=1)
    assert result["selector"] == "LEONES-model-selection"
    assert result["selection_policy"]["price_in_score"] is False
    assert result["candidates"][0]["fit_score"] >= 0


def test_incompatible_model_is_rejected_by_selector():
    result = recommend([row(estimated_memory_gb="16")], workload="chat", hardware="i5-1035G1", ram=8, vram=0, context=4096, top_n=1)
    assert result["counts"]["rejected"] == 1
    assert result["candidates"] == []
