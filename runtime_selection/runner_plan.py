"""Minimal bridge from runtime selection to the existing canonical runner.

The bridge enriches an already validated runtime plan with the ODS/Magnitude
stack decision. It does not execute, measure, install, or create another runner.
"""
from __future__ import annotations

from typing import Any

from .contract import validate_plan
from .stack_decision import StackDecision, decide_stack


def attach_stack_decision(
    plan: dict[str, Any],
    *,
    needs_deployment: bool = False,
    needs_agent: bool = False,
    direct_runtime_supported: bool = False,
    evidence_refs: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return a runner-consumable plan with one explicit stack decision."""
    validate_plan(plan)
    decision: StackDecision = decide_stack(
        needs_deployment=needs_deployment,
        needs_agent=needs_agent,
        direct_runtime_supported=direct_runtime_supported,
        evidence_refs=evidence_refs,
    )
    enriched = dict(plan)
    enriched["stack_decision"] = decision.to_dict()
    return enriched


def attach_stack_from_workload(plan: dict[str, Any]) -> dict[str, Any]:
    """Derive stack requirements only from declared workload requirements."""
    workload = plan.get("workload") or {}
    return attach_stack_decision(
        plan,
        needs_deployment=bool(workload.get("needs_deployment", False)),
        needs_agent=bool(workload.get("needs_agent", False)),
        direct_runtime_supported=bool(workload.get("direct_runtime_supported", False)),
        evidence_refs=tuple(workload.get("evidence_refs") or ()),
    )
