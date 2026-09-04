from runtime_selection.decision_engine import decide_models


def _enriched():
    return {
        "hardware": {"ram": {"total_gb": 7.03, "available_gb": 2.20}},
        "candidates": [
            {"model_id": "small", "parameters_b": .9, "quantization_bits": 4,
             "external_evidence": {"hugging_face": {"status": "weights_available"}, "artificial_analysis": {"intelligence_index": 1, "context_tokens": 32000, "reasoning": True}}},
            {"model_id": "strong", "parameters_b": 3.836, "quantization_bits": 4,
             "external_evidence": {"hugging_face": {"status": "weights_available"}, "artificial_analysis": {"intelligence_index": 6, "context_tokens": 128000, "reasoning": False}}},
        ]
    }


def test_balanced_prefers_fit_on_low_available_ram():
    result = decide_models(_enriched(), "balanced")
    assert result["recommended_model_id"] == "small"
    assert result["candidates"][0]["local_fit_estimate"]["status"] == "fit"
    assert result["candidates"][1]["local_fit_estimate"]["status"] == "insufficient"
    assert result["user_choice_required"] is True
    assert result["execution_authorized"] is False
    assert result["measured"] is False


def test_quality_profile_can_prefer_stronger_external_model():
    result = decide_models(_enriched(), "quality")
    assert result["recommended_model_id"] == "strong"


def test_ranking_is_deterministic_and_explainable():
    first = decide_models(_enriched(), "balanced")
    second = decide_models(_enriched(), "balanced")
    assert [c["model_id"] for c in first["candidates"]] == [c["model_id"] for c in second["candidates"]]
    assert all("decision_factors" in c for c in first["candidates"])
    assert all("measured_tps" not in c for c in first["candidates"])
