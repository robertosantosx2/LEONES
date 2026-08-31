import pytest

from scripts.rc2_beta_session import BetaSession


def ready_session():
    s = BetaSession()
    s.advance("HARDWARE_READY", hardware={"source": "test"})
    s.advance("MODEL_SELECTED", model_choice="qwen2.5:0.5b-instruct-q4_K_M")
    s.advance("STACK_SELECTED", stack="ods")
    s.advance("READY_FOR_INSTALL")
    s.advance("CONSENT_REQUIRED")
    return s


def test_install_requires_explicit_consent():
    s = ready_session()
    with pytest.raises(RuntimeError):
        s.installation_verified()
    s.authorize_installation()
    assert s.state == "INSTALLING"


def test_benchmark_requires_verified_installation_and_explicit_consent():
    s = ready_session()
    s.authorize_installation()
    s.installation_verified()
    s.request_benchmark_consent({"id": "LEONES-Agentic", "version": "1.0", "tasks": ["A01"]})
    assert s.snapshot()["gates"]["execution_authorized"] is False
    handoff = s.authorize_benchmark()
    assert s.state == "EXECUTION_AUTHORIZED"
    assert handoff["execution_authorized"] is True
    assert handoff["status"] == "benchmark_authorized"


def test_declined_benchmark_never_authorizes_execution():
    s = ready_session()
    s.authorize_installation()
    s.installation_verified()
    s.request_benchmark_consent({"id": "LEONES-Agentic", "version": "1.0", "tasks": ["A01"]})
    s.decline_benchmark()
    assert s.state == "READY_FOR_BENCHMARK"
    assert s.snapshot()["gates"]["execution_authorized"] is False
