"""Common lifecycle contract for optional LEONES deployment/runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterContext:
    target: str
    version: str | None = None
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterResult:
    adapter: str
    operation: str
    status: str
    version: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class Adapter(Protocol):
    name: str

    def detect(self, context: AdapterContext) -> AdapterResult: ...
    def select(self, context: AdapterContext) -> AdapterResult: ...
    def pin(self, context: AdapterContext) -> AdapterResult: ...
    def install(self, context: AdapterContext) -> AdapterResult: ...
    def verify(self, context: AdapterContext) -> AdapterResult: ...
    def measure(self, context: AdapterContext) -> AdapterResult: ...
    def report(self, context: AdapterContext) -> AdapterResult: ...
    def cleanup(self, context: AdapterContext) -> AdapterResult: ...


def lifecycle(adapter: Adapter, context: AdapterContext) -> list[AdapterResult]:
    """Run the common lifecycle in a fixed order.

    Adapters remain responsible for their own idempotency and safety checks.
    """
    results: list[AdapterResult] = []
    for operation in (
        "detect",
        "select",
        "pin",
        "install",
        "verify",
        "measure",
        "report",
        "cleanup",
    ):
        result = getattr(adapter, operation)(context)
        results.append(result)
        if result.status not in {"ok", "skipped"}:
            break
    return results
