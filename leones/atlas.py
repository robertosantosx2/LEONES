"""Leones Atlas interface.

The first implementation exposes a small repository-agnostic interface so the
Router can later consume the canonical Atlas database without changing its API.
"""

from dataclasses import dataclass
from typing import Protocol

from .core.contracts import HardwareProfile, ModelCandidate


@dataclass(frozen=True)
class AtlasRecord:
    model: ModelCandidate
    supported_hardware: tuple[str, ...] = ()
    evidence_status: str = "reported"


class Atlas(Protocol):
    def candidates(self, hardware: HardwareProfile) -> list[ModelCandidate]:
        ...


class InMemoryAtlas:
    """Minimal Atlas implementation for tests and early experiments."""

    def __init__(self, records: list[AtlasRecord] | None = None) -> None:
        self.records = records or []

    def candidates(self, hardware: HardwareProfile) -> list[ModelCandidate]:
        return [record.model for record in self.records]
