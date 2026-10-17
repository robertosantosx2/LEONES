from benchmarks.agentic.adapters.runtime import from_runtime_plan


def test_runtime_plan_handoff_requires_authorization_and_measurement():
    plan = {
        "model_id": "org/model",
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
        "selection_status": "TOP_N",
        "execution_authorized": True,
        "measurement_required": True,
        "estimated_tps": 12.5,
    }
    normalized = from_runtime_plan(plan)
    assert normalized.model_id == "org/model"
    assert normalized.runtime == "llama.cpp"
    assert normalized.measurement_required is True


def test_runtime_plan_cannot_bypass_measurement():
    plan = {
        "model_id": "org/model",
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
        "selection_status": "TOP_N",
        "execution_authorized": True,
        "measurement_required": False,
    }
    try:
        from_runtime_plan(plan)
    except ValueError as exc:
        assert "measurement" in str(exc)
    else:
        raise AssertionError("non-measured execution plan was accepted")
