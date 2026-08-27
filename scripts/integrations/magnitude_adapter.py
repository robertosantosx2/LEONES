"""Safe Magnitude adapter skeleton.

No CLI is executed implicitly. Runtime discovery and execution are explicit
integration steps so CI can exercise the adapter without Magnitude installed.
"""

from __future__ import annotations
from dataclasses import dataclass
import platform
from .external_stack import PreflightResult


@dataclass(frozen=True)
class MagnitudeAdapter:
    expected_ref: str

    def preflight(self) -> PreflightResult:
        return PreflightResult(
            status="PASS",
            os=platform.system().lower(),
            architecture=platform.machine().lower(),
            checks={"expected_ref": self.expected_ref, "install": "not_run"},
        )
