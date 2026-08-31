#!/usr/bin/env python3
"""Deterministic RC2 beta-session state machine.

This module intentionally orchestrates contracts; it does not install software,
inspect hardware, or execute benchmarks. Those effects belong to adapters behind
explicit gates and user consent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATES = (
    "START",
    "HARDWARE_READY",
    "MODEL_SELECTED",
    "STACK_SELECTED",
    "READY_FOR_INSTALL",
    "CONSENT_REQUIRED",
    "INSTALLING",
    "READY_FOR_BENCHMARK",
    "BENCHMARK_CONSENT_REQUIRED",
    "EXECUTION_AUTHORIZED",
    "COMPLETE",
    "BLOCKED",
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

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "state": self.state,
            "gates": {
                "hardware_ready": self.state in STATES[1:],
                "model_selected": self.state in STATES[2:],
                "stack_selected": self.state in STATES[3:],
                "ready_for_install": self.state in STATES[4:],
                "ready_for_benchmark": self.state in STATES[7:],
                "execution_authorized": self.state in {"EXECUTION_AUTHORIZED", "COMPLETE"},
            },
            **self.data,
            "error": self.error,
        }


def main() -> int:
    session = BetaSession()
    print(session.snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
