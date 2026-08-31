from runtime_selection.rc2_candidates import to_selection_plan


def test_user_selection_reuses_candidate_facts_and_is_not_authorized():
    candidate = {
        "model_id": "qwen2.5:0.5b-instruct-q4_K_M",
        "name": "Qwen2.5 0.5B Instruct Q4_K_M",
        "rank": 1,
        "fit": 1.0,
        "estimated_tps": None,
        "evidence_level": "estimated",
    }
    hardware = {"ram_gb": 32, "source": "fixture"}
    stack = {"name": "ollama", "adapter": "ollama.v1"}
    plan = to_selection_plan(candidate, hardware, stack)
    assert plan["model_id"] == candidate["model_id"]
    assert plan["selection_rank"] == 1
    assert plan["fit_score"] == 1.0
    assert plan["hardware"] == hardware
    assert plan["runtime"] == stack
    assert plan["selection_status"] == "USER_SELECTED"
    assert plan["execution_authorized"] is False
    assert plan["measurement_required"] is True
