"""Trusted V1.1 adapter for FreeToken."""
from __future__ import annotations
from typing import Any
from scripts.freetoken_runtime import evaluate_freetoken_candidate
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec
from scripts.runtime_registry import RuntimeEntry

class FreeTokenAdapter(RuntimeAdapter):
    runtime_id = "FreeToken"
    adapter_id = "freetoken.v1.1"

    def _eligibility(self, plan: dict[str, Any]) -> dict[str, Any]:
        return evaluate_freetoken_candidate({"model": plan.get("model") or {}, "hardware": plan.get("hardware") or {},
                                             "moe": plan.get("moe") or {}, "workload": plan.get("workload") or {}})

    def validate(self, plan: dict[str, Any], entry: RuntimeEntry) -> None:
        decision = self._eligibility(plan)
        if not decision["eligible"]:
            raise ValueError("FreeToken eligibility gate: " + "; ".join(decision["reasons"]))
        super().validate(plan, entry)

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        decision = self._eligibility(plan)
        return RuntimeExecutionSpec(self.runtime_id, self.adapter_id, plan["model_id"], tuple(entry.entrypoint["argv"]),
                                    {"entrypoint_kind": entry.entrypoint["kind"], "metrics": entry.metrics,
                                     "measurement_required": True, "runtime_eligibility": decision})

ADAPTER = FreeTokenAdapter()
