from runtime_selection.adapters import DeclarativeAdapter
from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan


def test_adapter_receives_plan_and_returns_execution_spec_without_measurement():
    plan = RuntimeSelectionPlan(
        runtime_id="reference", adapter_id="reference.v1", model_ref="demo",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )
    spec = DeclarativeAdapter().prepare(plan)
    assert spec.runtime_id == "reference"
    assert spec.adapter_id == "reference.v1"
    assert spec.model_ref == "demo"
    assert "tokens_per_second" not in spec.execution_metadata
    assert "measured_tps" not in spec.execution_metadata
