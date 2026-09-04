from runtime_selection.user_selection import (
    SCHEMA_VERSION,
    choose_stack,
    create_selection,
    validate_selection,
)


def _decision():
    return {
        "schema_version": "model-decision.v1",
        "profile": "balanced",
        "recommended_model_id": "Qwen/Qwen3.5-0.8B",
        "candidates": [
            {
                "model_id": "Qwen/Qwen3.5-0.8B",
                "name": "Qwen3.5 0.8B Reasoning",
                "revision": "main",
                "quantization": "Q4_K_M",
            },
            {"model_id": "Qwen/Qwen3-0.6B", "name": "Qwen3 0.6B"},
        ],
    }


def test_model_choice_is_explicit_and_not_authorized():
    selection = create_selection(
        _decision(),
        "Qwen/Qwen3.5-0.8B",
        quantization="Q4_K_M",
        runtime="llama.cpp",
    )
    assert selection["schema_version"] == SCHEMA_VERSION
    assert selection["selected_model_id"] == "Qwen/Qwen3.5-0.8B"
    assert selection["user_choice_recorded"] is True
    assert selection["execution_authorized"] is False
    assert selection["measurement_authorized"] is False


def test_stack_choice_preserves_gate():
    selection = create_selection(_decision(), "Qwen/Qwen3.5-0.8B", quantization="Q4_K_M")
    selected = choose_stack(selection, "magnitude")
    validate_selection(selected)
    assert selected["stack"] == "magnitude"
    assert selected["execution_authorized"] is False
    assert selected["consent_required_before_execution"] is True


def test_ods_is_supported():
    selection = create_selection(_decision(), "Qwen/Qwen3.5-0.8B")
    selected = choose_stack(selection, "ods")
    validate_selection(selected)
    assert selected["stack"] == "ods"


def test_unknown_model_rejected():
    try:
        create_selection(_decision(), "unknown/model")
    except ValueError as exc:
        assert "not present" in str(exc)
    else:
        raise AssertionError("unknown model must be rejected")


def test_missing_stack_fails_validation():
    selection = create_selection(_decision(), "Qwen/Qwen3.5-0.8B")
    try:
        validate_selection(selection)
    except ValueError as exc:
        assert "stack choice" in str(exc)
    else:
        raise AssertionError("selection without stack must not pass")
