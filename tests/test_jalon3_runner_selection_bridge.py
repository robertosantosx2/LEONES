from benchmarks.agentic.runner import Trace, execute_selected_runtime
from runtime_selection.adapters import ExecutionSpec
from runtime_selection.contract import CapabilityMatch, RuntimeSelectionPlan


class FakeAdapter:
    adapter_id = "fake.v1"

    def prepare(self, plan):
        return ExecutionSpec(
            runtime_id=plan.runtime_id,
            adapter_id=self.adapter_id,
            model_ref=plan.model_ref,
            execution_metadata={"prepared": True},
        )


def plan():
    return RuntimeSelectionPlan(
        runtime_id="fake",
        adapter_id="fake.v1",
        model_ref="example/model",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )


def test_runner_materializes_selection_and_executes_once():
    trace = Trace()
    calls = []

    result = execute_selected_runtime(
        trace,
        plan(),
        FakeAdapter(),
        lambda spec: calls.append(spec.model_ref) or {"tokens_per_second": 12.5},
    )

    assert result["tokens_per_second"] == 12.5
    assert calls == ["example/model"]
    assert [event.status for event in trace.events] == ["selected", "prepared", "completed"]


def test_runner_rejects_adapter_mismatch_before_execution():
    trace = Trace()
    bad = RuntimeSelectionPlan(
        runtime_id="fake",
        adapter_id="other.v1",
        model_ref="example/model",
        capability_match=CapabilityMatch(True, True, True, True, True),
    )

    try:
        execute_selected_runtime(trace, bad, FakeAdapter(), lambda _: None)
    except ValueError as exc:
        assert "adapter mismatch" in str(exc)
    else:
        raise AssertionError("adapter mismatch must be rejected")

    assert len(trace.events) == 0
