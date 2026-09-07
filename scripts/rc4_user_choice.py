#!/usr/bin/env python3
"""RC4 user choice, aggregate cost and disk gate primitives.

LEONES informs and calculates; the user decides. This module deliberately
contains no automatic model choice and no installation side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping

SCHEMA = "leones.rc4.user_choice.v1"
SOLUTIONS = ("personal_assistant", "soho", "both")
EVIDENCE_STATES = ("DECLARED", "ESTIMATED", "OBSERVED", "MEASURED", "UNKNOWN")


@dataclass(frozen=True)
class ModelCost:
    model_id: str
    disk_bytes: int | None = None
    runtime_bytes: int | None = None
    dependency_bytes: int | None = None
    data_bytes: int | None = None
    safety_margin_bytes: int | None = None
    ram_bytes: int | None = None
    vram_bytes: int | None = None
    cpu_load: str = "UNKNOWN"
    evidence_state: str = "UNKNOWN"

    def total_install_bytes(self) -> int | None:
        values = (self.disk_bytes, self.runtime_bytes, self.dependency_bytes,
                  self.data_bytes, self.safety_margin_bytes)
        return sum(values) if all(v is not None for v in values) else None


@dataclass(frozen=True)
class SolutionCost:
    solution_id: str
    runtime_bytes: int | None = None
    dependency_bytes: int | None = None
    data_bytes: int | None = None
    safety_margin_bytes: int | None = None

    def total_bytes(self) -> int | None:
        values = (self.runtime_bytes, self.dependency_bytes,
                  self.data_bytes, self.safety_margin_bytes)
        return sum(values) if all(v is not None for v in values) else None


def validate_solution(solution: str) -> str:
    value = solution.strip().lower()
    if value not in SOLUTIONS:
        raise ValueError(f"solution must be one of {SOLUTIONS}")
    return value


def validate_model_selection(model_ids: Iterable[str]) -> list[str]:
    """Return a stable, de-duplicated human selection with no artificial cap."""
    result: list[str] = []
    for raw in model_ids:
        model_id = str(raw).strip()
        if model_id and model_id not in result:
            result.append(model_id)
    if not result:
        raise ValueError("at least one model must be selected")
    return result


def aggregate_model_costs(models: Iterable[ModelCost]) -> dict:
    """Aggregate selected model costs without imposing a model-count limit."""
    selected = list(models)
    totals: dict[str, int | None] = {}
    for field in ("disk_bytes", "runtime_bytes", "dependency_bytes", "data_bytes", "safety_margin_bytes"):
        values = [getattr(m, field) for m in selected]
        totals[field] = sum(values) if values and all(v is not None for v in values) else None
    totals["total_install_bytes"] = (
        sum(v for v in (m.total_install_bytes() for m in selected) if v is not None)
        if selected and all(m.total_install_bytes() is not None for m in selected)
        else None
    )
    return {"model_count": len(selected), **totals}


def aggregate_selection_costs(
    *,
    model_cost_bytes: int | None,
    solution_cost_bytes: int | None,
    shared_component_bytes: int | None = 0,
) -> int | None:
    """Return the total install footprint, deduplicating shared components."""
    if model_cost_bytes is None or solution_cost_bytes is None or shared_component_bytes is None:
        return None
    if shared_component_bytes < 0:
        raise ValueError("shared_component_bytes cannot be negative")
    return model_cost_bytes + solution_cost_bytes - shared_component_bytes


def disk_gate(*, free_bytes: int | None, model_cost_bytes: int | None,
              solution_cost_bytes: int | None, shared_component_bytes: int | None = 0) -> dict:
    """Gate installation; UNKNOWN never becomes a guessed pass."""
    required = aggregate_selection_costs(
        model_cost_bytes=model_cost_bytes,
        solution_cost_bytes=solution_cost_bytes,
        shared_component_bytes=shared_component_bytes,
    )
    if free_bytes is None or required is None:
        return {"status": "UNKNOWN", "free_bytes": free_bytes, "required_bytes": required,
                "remaining_bytes": None, "install_allowed": False,
                "partial_install_allowed": False}
    remaining = free_bytes - required
    return {"status": "PASS" if remaining >= 0 else "BLOCKED",
            "free_bytes": free_bytes, "required_bytes": required,
            "remaining_bytes": remaining, "install_allowed": remaining >= 0,
            "partial_install_allowed": False}


def build_choice_envelope(*, purposes: Iterable[str], model_ids: Iterable[str], solution: str,
                          free_disk_bytes: int | None, model_cost: Mapping[str, object],
                          solution_cost: Mapping[str, object], shared_component_bytes: int | None = 0) -> dict:
    """Build the pre-confirmation decision record without installing anything.

    Selection is deliberately not consent. All consent flags remain false until
    a separate explicit confirmation step records the user's authorization.
    """
    models = validate_model_selection(model_ids)
    sol = validate_solution(solution)
    model_total = model_cost.get("total_install_bytes")
    solution_total = solution_cost.get("total_bytes")
    gate = disk_gate(
        free_bytes=free_disk_bytes,
        model_cost_bytes=model_total if isinstance(model_total, int) else None,
        solution_cost_bytes=solution_total if isinstance(solution_total, int) else None,
        shared_component_bytes=shared_component_bytes,
    )
    return {
        "schema": SCHEMA,
        "user_intent": {"required": True, "selection_mode": "multiple", "purposes": list(dict.fromkeys(purposes))},
        "models": {"selection_mode": "multiple", "selected": models, "artificial_limit": None},
        "solution": {"selection": sol, "options": list(SOLUTIONS)},
        "cost": {
            "models": dict(model_cost),
            "solution": dict(solution_cost),
            "shared_component_bytes": shared_component_bytes,
            "aggregate": gate,
        },
        "consent": {"purpose": False, "models": False, "solution": False, "install": False},
        "install": {"authorized": False, "partial_install_allowed": False},
    }


def as_jsonable(cost: ModelCost | SolutionCost) -> dict:
    return asdict(cost)
