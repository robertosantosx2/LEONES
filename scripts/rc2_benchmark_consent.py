"""RC2 benchmark-consent bridge.

The user decision is explicit. Declining leaves the session ready without
execution; granting creates the only RC1 handoff that carries authorization.
"""
from __future__ import annotations
from typing import Any
from scripts.rc2_beta_session import BetaSession


def request_and_decide(session: BetaSession, benchmark: dict[str, Any], consent: bool) -> dict[str, Any]:
    session.request_benchmark_consent(benchmark)
    if not consent:
        session.decline_benchmark()
        return {"state": session.state, "execution_authorized": False, "rc1_handoff": None}
    handoff = session.authorize_benchmark()
    return {"state": session.state, "execution_authorized": True, "rc1_handoff": handoff}
