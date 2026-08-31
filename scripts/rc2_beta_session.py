#!/usr/bin/env python3
"""Deterministic RC2 beta-session state machine.

This module orchestrates contracts. Side effects remain behind explicit gates:
installation requires installation consent; benchmark execution requires a
separate benchmark consent and hands an already-authorized plan to RC1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STATES = (
    "START", "HARDWARE_READY", "MODEL_SELECTED", "STACK_SELECTED",
    "READY_FOR_INSTALL", "CONSENT_REQUIRED", "INSTALLING",
    "READY_FOR_BENCHMARK", "BENCHMARK_CONSENT_REQUIRED",
    "EXECUTION_AUTHORIZED", "COMPLETE", "BLOCKED",
)


@dataclass
class BetaSession:
    state: str = "START"
    data: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def advance(self, state: str, **data: Any) -> None:
        if state not in STATES:
            raise ValueError(f"unknown RC2 state: {state}")
        self.state = state
        self.data.update(data)
        self.error = None

    def block(self, code: str, message: str) -> None:
        self.state = "BLOCKED"
        self.error = {"code": code, "message": message}

    def authorize_installation(self) -> None:
        if self.state != "CONSENT_REQUIRED":
            raise RuntimeError("installation consent is not currently requested")
        self.advance("INSTALLING", installation_consent="granted")

    def installation_verified(self, verification: dict[str, Any] | None = None) -> None:
        if self.state != "INSTALLING":
            raise RuntimeError("installation is not in progress")
        self.advance("READY_FOR_BENCHMARK", installation_verification=verification or {"status": "verified"})

    def request_benchmark_consent(self, benchmark: dict[str, Any]) -> None:
        if self.state != "READY_FOR_BENCHMARK":
            raise RuntimeError("installation must be verified before benchmark consent")
        self.advance("BENCHMARK_CONSENT_REQUIRED", benchmark=benchmark)

    def decline_benchmark(self) -> None:
        if self.state != "BENCHMARK_CONSENT_REQUIRED":
            raise RuntimeError("benchmark consent is not currently requested")
        self.advance("READY_FOR_BENCHMARK", benchmark_consent="declined")

    def authorize_benchmark(self) -> dict[str, Any]:
        if self.state != "BENCHMARK_CONSENT_REQUIRED":
            raise RuntimeError("benchmark consent is not currently requested")
        benchmark = self.data.get("benchmark") or {}
        handoff = {
            "schema_version": "1.0",
            "status": "benchmark_authorized",
            "benchmark": benchmark,
            "execution_authorized": True,
        }
        self.advance("EXECUTION_AUTHORIZED", benchmark_consent="granted", rc1_handoff=handoff)
        return handoff

    def complete(self, execution_id: str) -> None:
        if self.state != "EXECUTION_AUTHORIZED":
            raise RuntimeError("RC1 execution has not been authorized")
        self.advance("COMPLETE", execution_id=execution_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0", "state": self.state,
            "gates": {
                "hardware_ready": self.state in STATES[1:],
                "model_selected": self.state in STATES[2:],
                "stack_selected": self.state in STATES[3:],
                "ready_for_install": self.state in STATES[4:],
                "ready_for_benchmark": self.state in STATES[7:],
                "execution_authorized": self.state in {"EXECUTION_AUTHORIZED", "COMPLETE"},
            },
            **self.data, "error": self.error,
        }


def main() -> int:
    print(BetaSession().snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
