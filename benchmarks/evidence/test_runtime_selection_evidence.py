import pytest

from runtime_selection_evidence import build_runtime_feedback


def result(evidence_type="measured", measured_tps=11.5):
    evidence = {
        "evidence_type": evidence_type,
        "source": "fixture-runtime",
        "execution_id": "exec-001",
        "measured_at": "2026-08-24T00:00:00+00:00",
    }
    return {
        "evidence": evidence,
        "model": {"id": "demo/model", "revision": "r1"},
        "hardware": {"ram_gb": 32},
        "agentic": {
            "execution_id": "exec-001",
            "runtime": {"name": "FreeToken"},
            "metrics": {"measured_tps": measured_tps, "runtime_wall_seconds": 4.0,
                         "tool_calls": 2, "tool_errors": 0, "recovery_count": 0},
        },
    }


def test_measured_result_becomes_selector_feedback():
    feedback = build_runtime_feedback(result())
    assert feedback["evidence_type"] == "measured"
    assert feedback["metrics"]["measured_tps"] == 11.5
    assert feedback["selector_feedback"]["usable_for_runtime_comparison"] is True
    assert feedback["selector_feedback"]["replace_estimate"] is True
    assert feedback["selector_feedback"]["usable_as_verified_claim"] is False


def test_reported_result_does_not_replace_measurement():
    feedback = build_runtime_feedback(result("reported", 11.5))
    assert feedback["selector_feedback"]["usable_for_runtime_comparison"] is False
    assert feedback["selector_feedback"]["replace_estimate"] is False


def test_verified_result_is_not_created_by_runner():
    with pytest.raises(ValueError, match="independent verifier"):
        build_runtime_feedback(result("verified", 11.5))


def test_measured_result_requires_execution_id():
    payload = result()
    del payload["evidence"]["execution_id"]
    del payload["agentic"]["execution_id"]
    with pytest.raises(ValueError, match="execution_id"):
        build_runtime_feedback(payload)
