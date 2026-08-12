from leones.router_hardware import HardwareLimits, filter_by_hardware
from leones.router_simple import Candidate


def test_hardware_filter_preserves_current_candidates():
    candidates = [Candidate("model-a", ("general",))]
    assert filter_by_hardware(candidates, HardwareLimits(16)) == candidates
