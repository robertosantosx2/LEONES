from scripts.rc2_beta_session import BetaSession
from scripts.rc2_benchmark_consent import request_and_decide


def ready_session():
    s = BetaSession()
    s.advance("READY_FOR_BENCHMARK", model="fixture", stack="fixture")
    return s


def test_decline_never_authorizes_execution():
    s = ready_session()
    result = request_and_decide(s, {"id": "A01", "version": "1.0"}, False)
    assert result["state"] == "READY_FOR_BENCHMARK"
    assert result["execution_authorized"] is False
    assert result["rc1_handoff"] is None


def test_grant_creates_explicit_rc1_handoff():
    s = ready_session()
    result = request_and_decide(s, {"id": "A01", "version": "1.0"}, True)
    assert result["state"] == "EXECUTION_AUTHORIZED"
    assert result["execution_authorized"] is True
    assert result["rc1_handoff"]["execution_authorized"] is True
    assert result["rc1_handoff"]["benchmark"]["id"] == "A01"
