from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan
from runtime_selection.registry import build_default_registry
from scripts.runtimes.ollama_adapter import ADAPTER_ID, prepare


def test_ollama_is_in_canonical_registry():
    registry = build_default_registry()
    runtime = registry.get("ollama")

    assert runtime.runtime_id == "ollama"
    assert runtime.adapter_id == ADAPTER_ID
    assert runtime.metadata["entrypoint_ref"] == "trusted://ollama/a01"


def test_ollama_adapter_preserves_declarative_boundary():
    plan = RuntimeSelectionPlan(
        runtime_id="ollama",
        adapter_id=ADAPTER_ID,
        model_ref="fixture/model",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )

    spec = prepare(plan)

    assert spec.runtime_id == "ollama"
    assert spec.adapter_id == ADAPTER_ID
    assert spec.model_ref == "fixture/model"

    assert "command" not in spec.execution_metadata
    assert "argv" not in spec.execution_metadata
    assert "shell" not in spec.execution_metadata
    assert "tokens_per_second" not in spec.execution_metadata
    assert "measured_tps" not in spec.execution_metadata
    assert spec.execution_metadata["runner"] == "ollama"


def test_ollama_adapter_rejects_other_runtime():
    plan = RuntimeSelectionPlan(
        runtime_id="llama.cpp",
        adapter_id=ADAPTER_ID,
        model_ref="fixture/model",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )

    try:
        prepare(plan)
    except ValueError as exc:
        assert "unsupported runtime" in str(exc)
    else:
        raise AssertionError("Ollama adapter accepted another runtime")
