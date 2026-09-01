import pytest

from scripts.rc2_beta_session import BetaSession


def _ready_for_benchmark() -> BetaSession:
    s = BetaSession()
    s.advance("HARDWARE_READY", hardware={"source": "fixture"})
    s.advance("MODEL_SELECTED", model_choice={"model_id": "fixture"})
    s.advance("STACK_SELECTED", stack={"name": "ods"})
    s.advance("CONSENT_REQUIRED", installation={"status": "plan_ready"})
    s.authorize_installation()
    s.installation_verified({"status": "fixture_verified", "real_installation": True})
    return s


def test_session_starts_without_authorization():
    s = BetaSession()
    snap = s.snapshot()
    assert snap["state"] == "START"
    assert snap["gates"]["execution_authorized"] is False


def test_arbitrary_state_skipping_is_rejected():
    s = BetaSession()
    with pytest.raises(RuntimeError, match="invalid RC2 transition"):
        s.advance("EXECUTION_AUTHORIZED")


def test_installation_requires_explicit_consent():
    s = BetaSession()
    s.advance("HARDWARE_READY")
    s.advance("MODEL_SELECTED")
    s.advance("STACK_SELECTED")
    s.advance("CONSENT_REQUIRED")
    with pytest.raises(RuntimeError, match="installation consent"):
        s.installation_verified({"real_installation": True})
    s.authorize_installation()
    assert s.snapshot()["state"] == "INSTALLING"


def test_real_installation_verification_is_required():
    s = BetaSession()
    s.advance("HARDWARE_READY")
    s.advance("MODEL_SELECTED")
    s.advance("STACK_SELECTED")
    s.advance("CONSENT_REQUIRED")
    s.authorize_installation()
    with pytest.raises(RuntimeError, match="real installation verification"):
        s.installation_verified({"status": "fixture_verified", "real_installation": False})


def test_benchmark_requires_verified_installation_and_creates_rc1_handoff():
    s = _ready_for_benchmark()
    benchmark = {"id": "LEONES-Agentic", "version": "1.0", "tasks": ["A01"]}
    s.request_benchmark_consent(benchmark)
    assert s.snapshot()["state"] == "BENCHMARK_CONSENT_REQUIRED"
    handoff = s.authorize_benchmark()
    assert handoff["status"] == "benchmark_authorized"
    assert handoff["execution_authorized"] is True
    assert handoff["installation_verified"] is True
    assert s.snapshot()["state"] == "EXECUTION_AUTHORIZED"


def test_declining_benchmark_does_not_authorize_execution():
    s = _ready_for_benchmark()
    s.request_benchmark_consent({"id": "LEONES-Agentic", "version": "1.0", "tasks": ["A01"]})
    s.decline_benchmark()
    assert s.snapshot()["state"] == "READY_FOR_BENCHMARK"
    assert s.snapshot()["gates"]["execution_authorized"] is False
