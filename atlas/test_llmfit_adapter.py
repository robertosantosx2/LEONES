from llmfit_adapter import llmfit_candidate_to_atlas, to_runtime_selection


def test_llmfit_stays_estimated_and_does_not_authorize_runtime():
    record = llmfit_candidate_to_atlas({
        "id": "demo-llmfit",
        "name": "Demo LLMFit",
        "parameters_b": 7,
        "quantization": "Q4_K_M",
        "memory_gb": 4.5,
        "fits_memory": True,
        "runtime": "llama.cpp",
        "uncertainty": 0.35,
    })
    assert record["evidence"]["evidence_type"] == "external"
    assert record["recommendation"]["cabe_status"] == "estimated"
    assert record["recommendation"]["rula_status"] == "unknown"
    assert record["recommendation"]["performance_score"] is None
    selection = to_runtime_selection(record)
    assert selection["schema"] == "runtime-selection.v1"
    assert selection["execution_authorized"] is False
    assert selection["selection"]["evidence_level"] == "Estimated"


def test_only_verified_rula_and_trusted_command_can_authorize():
    record = llmfit_candidate_to_atlas({"id": "demo"})
    record["recommendation"]["rula"] = True
    record["recommendation"]["rula_status"] = "verified"
    selection = to_runtime_selection(record, trusted_runtime_command=["fixture-runtime"])
    assert selection["execution_authorized"] is True
    assert selection["runtime"]["command"] == ["fixture-runtime"]
