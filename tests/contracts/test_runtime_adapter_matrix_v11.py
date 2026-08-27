import pytest

from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan
from runtime_selection.extended import ADAPTERS, prepare


@pytest.mark.parametrize("runtime_id,adapter_id", ADAPTERS.items())
def test_extended_adapters_preserve_declarative_boundary(runtime_id, adapter_id):
    plan = RuntimeSelectionPlan(
        runtime_id=runtime_id,
        adapter_id=adapter_id,
        model_ref="fixture/model",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )
    spec = prepare(plan)
    assert spec.runtime_id == runtime_id
    assert spec.adapter_id == adapter_id
    assert spec.model_ref == "fixture/model"
    assert not {"command", "argv", "shell", "tokens_per_second", "measured_tps"} & spec.execution_metadata.keys()
