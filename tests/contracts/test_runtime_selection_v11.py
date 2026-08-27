from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan, validate_plan
from runtime_selection.registry import RuntimeDescriptor, RuntimeRegistry


def request():
    from runtime_selection.contract import RuntimeSelectionRequest
    return RuntimeSelectionRequest(
        model={"id": "demo", "architecture": "llama", "format": "gguf", "quantization": "q4"},
        hardware={"memory_gb": 16, "accelerators": ["cpu"]},
        workload={"context_length": 4096, "execution_mode": "local"},
    )


def test_registry_matches_capabilities_without_commands():
    registry = RuntimeRegistry([RuntimeDescriptor(
        runtime_id="reference", adapter_id="reference.v1",
        supported_architectures=frozenset({"llama"}),
        supported_model_formats=frozenset({"gguf"}),
        supported_quantizations=frozenset({"q4"}),
        hardware=frozenset({"cpu"}), min_memory_gb=8,
        execution_modes=frozenset({"local"}), max_context=8192,
    )])
    matches = registry.match(request())
    assert len(matches) == 1
    assert matches[0][1].compatible


def test_incompatible_capability_is_not_matched():
    registry = RuntimeRegistry([RuntimeDescriptor(
        runtime_id="gpu-only", adapter_id="gpu-only.v1", hardware=frozenset({"cuda"})
    )])
    assert registry.match(request()) == []


def test_selection_plan_is_declarative():
    plan = RuntimeSelectionPlan(
        runtime_id="reference", adapter_id="reference.v1", model_ref="demo",
        capability_match=CapabilityMatch(True, True, True, True, True),
    ).to_dict()
    validate_plan(plan)
    assert "command" not in plan
    assert "measured_tps" not in plan


def test_selection_rejects_execution_and_measurement_fields():
    plan = RuntimeSelectionPlan(
        runtime_id="reference", adapter_id="reference.v1", model_ref="demo",
        capability_match=CapabilityMatch(True, True, True, True, True),
    ).to_dict()
    plan["command"] = ["unsafe"]
    try:
        validate_plan(plan)
    except ValueError as exc:
        assert "execution/measurement" in str(exc)
    else:
        raise AssertionError("command leaked into selection contract")
