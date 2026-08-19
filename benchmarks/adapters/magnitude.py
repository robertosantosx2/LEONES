"""Safe Magnitude adapter boundary.

The adapter records the intended runtime contract but does not launch an
external agent implicitly. A real benchmark run must explicitly opt in and
supply a pinned executable/environment.
"""

from __future__ import annotations

import shutil

from .contract import AdapterContext, AdapterResult


class MagnitudeAdapter:
    name = "magnitude"

    def detect(self, context: AdapterContext) -> AdapterResult:
        executable = shutil.which("magnitude")
        return AdapterResult(
            self.name,
            "detect",
            "ok" if executable else "skipped",
            details={"executable": executable, "target": context.target},
        )

    def select(self, context: AdapterContext) -> AdapterResult:
        return AdapterResult(self.name, "select", "ok", version=context.version, details={"target": context.target})

    def pin(self, context: AdapterContext) -> AdapterResult:
        if not context.version:
            return AdapterResult(self.name, "pin", "skipped", details={"reason": "no version requested"})
        return AdapterResult(self.name, "pin", "ok", version=context.version)

    def install(self, context: AdapterContext) -> AdapterResult:
        if context.dry_run:
            return AdapterResult(self.name, "install", "skipped", details={"reason": "dry_run"})
        return AdapterResult(self.name, "install", "skipped", details={"reason": "installer not yet enabled"})

    def verify(self, context: AdapterContext) -> AdapterResult:
        return AdapterResult(self.name, "verify", "skipped", details={"reason": "no installation performed"})

    def measure(self, context: AdapterContext) -> AdapterResult:
        return AdapterResult(self.name, "measure", "skipped", details={"reason": "no live agent"})

    def report(self, context: AdapterContext) -> AdapterResult:
        return AdapterResult(self.name, "report", "ok", details={"provenance_only": True})

    def cleanup(self, context: AdapterContext) -> AdapterResult:
        return AdapterResult(self.name, "cleanup", "ok", details={"changed": False})
