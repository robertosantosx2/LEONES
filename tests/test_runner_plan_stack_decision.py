import pytest

from runtime_selection.runner_plan import attach_stack_decision, attach_stack_from_workload


def base_plan():
    return {
        "schema_version": "runtime-selection.v1.1",
        "runtime_id": "llama.cpp",
        "adapter_id": "llama_cpp.v1",
        "model_ref": "Qwen3-0.6B",
    }


def test_direct_runtime_wins_when_no_extra_stack_is_needed():
    plan = attach_stack_decision(base_plan(), direct_runtime_supported=True)
    assert plan["stack_decision"]["stack"] == "none"


def test_deployment_and_agent_are_composed():
    plan = attach_stack_decision(base_plan(), needs_deployment=True, needs_agent=True)
    assert plan["stack_decision"]["stack"] == "ods+magnitude"


def test_workload_fields_are_the_only_inputs_to_workload_bridge():
    plan = dict(base_plan(), workload={"needs_agent": True})
    enriched = attach_stack_from_workload(plan)
    assert enriched["stack_decision"]["stack"] == "magnitude"


def test_invalid_selection_plan_is_rejected_before_stack_decision():
    invalid = dict(base_plan(), measured_tps=43.6)
    with pytest.raises(ValueError, match="execution/measurement"):
        attach_stack_decision(invalid)
