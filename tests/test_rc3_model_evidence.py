from runtime_selection.model_evidence import enrich_candidates


def test_external_evidence_informs_but_does_not_measure_or_authorize():
    hardware = {"ram": {"available_gb": 2.2}}
    candidates = [
        {"model_id": "small", "name": "Small"},
        {"model_id": "strong", "name": "Strong"},
    ]
    evidence = [
        {"model_id": "small", "parameters_b": 0.8, "artificial_analysis": {"intelligence_index": 1}},
        {"model_id": "strong", "parameters_b": 3.8, "artificial_analysis": {"intelligence_index": 6}},
    ]
    result = enrich_candidates(hardware, candidates, evidence)
    assert result["recommended_model_id"] == "small"
    assert result["user_choice_required"] is True
    assert result["execution_authorized"] is False
    assert result["measured"] is False
    assert all(item["evidence_status"] == "external_only" for item in result["candidates"])


def test_external_hosted_speed_is_not_local_measurement():
    result = enrich_candidates(
        {"ram": {"available_gb": 8}},
        [{"model_id": "phi"}],
        [{"model_id": "phi", "parameters_b": 3.8,
          "artificial_analysis": {"intelligence_index": 6, "hosted_output_tps": 43.7}}],
    )
    item = result["candidates"][0]
    assert item["external_evidence"]["artificial_analysis"]["hosted_output_tps"] == 43.7
    assert "measured_tps" not in item
