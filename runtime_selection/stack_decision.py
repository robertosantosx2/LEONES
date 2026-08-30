"""Minimal LEONES -> ODS/Magnitude stack decision contract.

This module is deliberately deterministic and dependency-free. It decides only
which stack path is authorized; the existing runner remains the execution path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Stack = Literal["none", "ods", "magnitude", "ods+magnitude"]


@dataclass(frozen=True)
class StackDecision:
    stack: Stack
    reason: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack": self.stack,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }


def decide_stack(*, needs_deployment: bool = False,
                 needs_agent: bool = False,
                 direct_runtime_supported: bool = False,
                 evidence_refs: tuple[str, ...] = ()) -> StackDecision:
    """Return the only stack decision implied by the declared requirements."""
    if direct_runtime_supported and not needs_deployment and not needs_agent:
        return StackDecision("none", "direct LEONES runtime is sufficient", evidence_refs)
    if needs_deployment and needs_agent:
        return StackDecision("ods+magnitude", "deployment/service layer plus agent execution is required", evidence_refs)
    if needs_deployment:
        return StackDecision("ods", "local deployment/service stack is required", evidence_refs)
    if needs_agent:
        return StackDecision("magnitude", "agent execution is required", evidence_refs)
    return StackDecision("none", "no ODS or Magnitude capability is required", evidence_refs)
