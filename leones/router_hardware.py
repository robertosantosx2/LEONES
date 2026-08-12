"""Filter Router candidates using the local hardware profile.

One responsibility: reject candidates whose declared minimum RAM exceeds the
available RAM. It does not benchmark, execute, download, or change models.
"""

from dataclasses import dataclass

from .router_simple import Candidate


@dataclass(frozen=True)
class HardwareLimits:
    ram_gb: float


def filter_by_hardware(candidates: list[Candidate], hardware: HardwareLimits) -> list[Candidate]:
    """Return candidates that fit the declared RAM requirement.

    Candidate currently has no RAM field, so all existing candidates pass.
    The explicit function establishes the boundary for the next Atlas schema
    extension without inventing requirements that are not yet recorded.
    """
    return list(candidates)
