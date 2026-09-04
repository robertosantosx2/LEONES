from runtime_selection.candidate_set import build_candidate_set, validate_candidate_set


def test_build_candidate_set_preserves_provenance_and_blocks_execution():
    hardware = {"schema": "hardware-profile.v1", "verification": "detected"}
    payload = build_candidate_set(
        hardware,
        [
            {
                "id": "Qwen/Qwen3-0.6B",
                "name": "Qwen3 0.6B",
                "rank": 1,
                "fit": 0.91,
                "estimated_tps": 40.0,
                "quantization": "Q4_K_M",
                "source": "hermes",
                "source_version": "0.21.0",
            },
            {"name": "invalid without id"},
        ],
    )

    validate_candidate_set(payload)
    assert payload["candidate_count"] == 1
    candidate = payload["candidates"][0]
    assert candidate["model_id"] == "Qwen/Qwen3-0.6B"
    assert candidate["evidence_level"] == "estimated"
    assert candidate["selection_status"] == "CANDIDATE"
    assert candidate["execution_authorized"] is False
    assert candidate["measurement_required"] is True
    assert payload["selection"]["user_choice_required"] is True
    assert payload["selection"]["selected_model_id"] is None
    assert payload["measurement"]["measured"] is False


def test_candidate_set_rejects_measurement_or_execution_leakage():
    payload = build_candidate_set({}, [{"model_id": "m"}])
    payload["candidates"][0]["measured_tps"] = 12.3
    try:
        validate_candidate_set(payload)
    except ValueError as exc:
        assert "measurement" in str(exc)
    else:
        raise AssertionError("measurement leakage was not rejected")
