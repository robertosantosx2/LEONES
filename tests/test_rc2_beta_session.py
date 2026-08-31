from scripts.rc2_beta_session import BetaSession


def test_session_starts_without_authorization():
    s = BetaSession()
    snap = s.snapshot()
    assert snap["state"] == "START"
    assert snap["gates"]["execution_authorized"] is False


def test_authorization_only_after_explicit_execution_state():
    s = BetaSession()
    s.advance("READY_FOR_BENCHMARK")
    assert s.snapshot()["gates"]["execution_authorized"] is False
    s.advance("EXECUTION_AUTHORIZED", execution_id="test-execution")
    snap = s.snapshot()
    assert snap["gates"]["execution_authorized"] is True
    assert snap["execution_id"] == "test-execution"


def test_block_is_actionable_and_clears_previous_error():
    s = BetaSession()
    s.block("MISSING_REQUIREMENT", "A required component is unavailable")
    assert s.snapshot()["state"] == "BLOCKED"
    assert s.snapshot()["error"]["code"] == "MISSING_REQUIREMENT"
    s.advance("HARDWARE_READY")
    assert s.snapshot()["error"] is None
