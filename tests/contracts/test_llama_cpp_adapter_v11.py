from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan
from runtime_selection.llama_cpp import ADAPTER_ID, prepare


def test_llama_cpp_is_canonical_adapter_and_has_no_measurement():
    plan = RuntimeSelectionPlan(
        runtime_id="llama.cpp", adapter_id=ADAPTER_ID, model_ref="TheBloke/test-GGUF",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )
    spec = prepare(plan)
    assert spec.runtime_id == "llama.cpp"
    assert spec.adapter_id == ADAPTER_ID
    assert spec.execution_metadata["runner"] == "llama.cpp"
    assert "estimated_tps" not in spec.execution_metadata
    assert "measured_tps" not in spec.execution_metadata
