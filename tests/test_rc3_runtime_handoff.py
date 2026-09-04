from runtime_selection.runtime_handoff import build_runtime_plan
from runtime_selection.user_selection import create_selection


def _decision():
    return {
        "profile": "balanced",
        "recommended_model_id": "Qwen/Qwen3.5-0.8B",
        "candidates": [{
            "model_id": "Qwen/Qwen3.5-0.8B",
            "name": "Qwen3.5 0.8B Reasoning",
            "quantization": "Q4_K_M",
        }],
    }


def _hardware():
    return {"schema": "hardware-profile.v1", "architecture": "x86_64"}


def test_user_choice_handoffs_to_declarative_runtime_plan():
    selection = create_selection(
        _decision(), "Qwen/Qwen3.5-0.8B", quantization="Q4_K_M", stack="magnitude"
    )
    plan = build_runtime_plan(selection, _hardware())
    payload = plan.to_dict()
    assert payload["runtime_id"] == "llama.cpp"
    assert payload["adapter_id"] == "llama_cpp.v1"
    assert payload["model_ref"] == "Qwen/Qwen3.5-0.8B"
    assert payload["constraints"]["execution_authorized"] is False


def test_handoff_never_authorizes_measurement():
    selection = create_selection(
        _decision(), "Qwen/Qwen3.5-0.8B", quantization="Q4_K_M", stack="ods"
    )
    plan = build_runtime_plan(selection, _hardware())
    assert plan.constraints["measurement_authorized"] is False
    assert plan.constraints["consent_required_before_execution"] is True


def test_handoff_preserves_selected_stack():
    selection = create_selection(
        _decision(), "Qwen/Qwen3.5-0.8B", quantization="Q4_K_M", stack="ods"
    )
    plan = build_runtime_plan(selection, _hardware())
    assert plan.selection_metadata["stack"] == "ods"


def test_handoff_rejects_missing_explicit_stack():
    selection = create_selection(_decision(), "Qwen/Qwen3.5-0.8B", quantization="Q4_K_M")
    try:
        build_runtime_plan(selection, _hardware())
    except ValueError as exc:
        assert "stack" in str(exc)
    else:
        raise AssertionError("missing stack must be rejected")
