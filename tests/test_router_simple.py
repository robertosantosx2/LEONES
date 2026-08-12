import pytest

from leones.router_simple import Candidate, route


def test_router_prefers_matching_capability():
    candidates = [
        Candidate("general", ("general",)),
        Candidate("coder", ("coding",)),
    ]
    assert route("write Python code", candidates).model_id == "coder"


def test_router_uses_declared_order_when_general():
    candidates = [Candidate("first", ("general",)), Candidate("second", ("general",))]
    assert route("tell me a joke", candidates).model_id == "first"


def test_router_reports_no_match():
    with pytest.raises(ValueError):
        route("write Python code", [Candidate("general", ("general",))])
