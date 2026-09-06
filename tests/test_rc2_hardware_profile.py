from runtime_selection.hardware_profile import normalize_hardware, normalize_candidates, reconcile_hardware


def test_unknown_hardware_is_not_fabricated():
    p = normalize_hardware({"source": "fixture"})
    assert p["cpu"] is None
    assert p["ram_gb"] is None
    assert p["gpu"] is None
    assert p["source"] == "fixture"


def test_candidate_normalization_preserves_llmfit_provenance():
    candidates = normalize_candidates(
        [
            {"id": "model-a", "fit": 0.91, "estimated_tps": 12.5, "source_version": "fixture-1"}
        ],
        source="llmfit",
    )
    assert candidates[0]["model_id"] == "model-a"
    assert candidates[0]["fit"] == 0.91
    assert candidates[0]["estimated_tps"] == 12.5
    assert candidates[0]["source"] == "llmfit"


def test_detected_hardware_wins_but_discrepancy_is_preserved():
    p = reconcile_hardware(
        {"ram_gb": 16, "source": "user"},
        {"ram_gb": 32, "source": "local-detection", "verification": "detected"},
    )
    assert p["ram_gb"] == 32
    assert p["verification"] == "discrepancy"
    assert p["discrepancies"]["ram_gb"] == {"declared": 16, "detected": 32}
