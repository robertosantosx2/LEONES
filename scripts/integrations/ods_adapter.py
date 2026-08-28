"""Safe ODS adapter skeleton.

The adapter never installs ODS implicitly. Installation/lifecycle remain ODS
responsibilities; LEONES only invokes explicitly supplied, fixed commands.
"""

from __future__ import annotations
from dataclasses import dataclass
import platform
from .external_stack import PreflightResult


@dataclass(frozen=True)
class ODSAdapter:
    expected_ref: str

    def evidence(self):
        from .external_stack import EvidenceResult
        return EvidenceResult(
            state="REPORTED",
            product="ODS",
            version=self.expected_ref,
            source="fixed_ref",
        )

    def preflight(self) -> PreflightResult:
        return PreflightResult(
            status="PASS",
            os=platform.system().lower(),
            architecture=platform.machine().lower(),
            checks={"expected_ref": self.expected_ref, "install": "not_run"},
        )
