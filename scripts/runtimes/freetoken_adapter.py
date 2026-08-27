"""Trusted V1.1 adapter for FreeToken.

The FreeToken eligibility gate remains authoritative; claims from external
sources never become LEONES measurements.
"""
from __future__ import annotations
from typing import Any
from scripts.freetoken_runtime import evaluate_freetoken_candidate
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec
from scripts.runtime_registry import RuntimeEntry


class FreeTokenAdapter(RuntimeAdapter):
    runtime_id = "FreeToken"
    adapter_id = "freetoken.v1.1"

    def validate(self, plan: dict[str, Any], entry: RuntimeEntry) -> None:
        super().validate(plan, entry)
        decision = evaluate_freetoken_candidate({
            "model": plan.get("model") or {},
            "hardware": plan.get("hardware") or {},
            "moe": plan.get("moe") or {},
            "workload": plan.get("workload") or {},
        })
        if not decision["eligible"]:
            raise ValueError("FreeToken eligibility gate: " + "; ".join(decision["reasons"]))

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(self.runtime_id, self.adapter_id, plan["model_id"],
                                    tuple(entry.entrypoint["argv"]),
                                    {"entrypoint_kind": entry.entrypoint["kind"], "metrics": entry.metrics,
                                     "measurement_required": True})

ADAPTER = FreeTokenAdapter()
