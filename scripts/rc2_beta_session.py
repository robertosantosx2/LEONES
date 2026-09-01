#!/usr/bin/env python3
"""Deterministic RC2 beta-session state machine.

The session is the authorization boundary for RC2. Installation and benchmark
execution are explicit gates; callers cannot skip physical verification or
benchmark consent by assigning a later state directly.
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

_TRANSITIONS = {
    "START": {"HARDWARE_READY", "BLOCKED"},
    "HARDWARE_READY": {"MODEL_SELECTED", "BLOCKED"},
    "MODEL_SELECTED": {"STACK_SELECTED", "BLOCKED"},
    "STACK_SELECTED": {"READY_FOR_INSTALL", "CONSENT_REQUIRED", "BLOCKED"},
    "READY_FOR_INSTALL": {"CONSENT_REQUIRED", "BLOCKED"},
    "CONSENT_REQUIRED": {"INSTALLING", "BLOCKED"},
    "INSTALLING": {"READY_FOR_BENCHMARK", "BLOCKED"},
    "READY_FOR_BENCHMARK": {"BENCHMARK_CONSENT_REQUIRED", "BLOCKED"},
    "BENCHMARK_CONSENT_REQUIRED": {"READY_FOR_BENCHMARK", "EXECUTION_AUTHORIZED", "BLOCKED"},
    "EXECUTION_AUTHORIZED": {"COMPLETE", "BLOCKED"},
    "COMPLETE": set(),
    "BLOCKED": {"HARDWARE_READY", "BLOCKED"},
}


@dataclass
class BetaSession:
    state: str = "START"
    data: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def advance(self, state: str, **data: Any) -> None:
        if state not in STATES:
            raise ValueError(f"unknown RC2 state: {state}")
        if state != "BLOCKED" and state not in _TRANSITIONS[self.state]:
            raise RuntimeError(f"invalid RC2 transition: {self.state} -> {state}")
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
        if self.state == "CONSENT_REQUIRED":
            raise RuntimeError("installation consent is required before verification")
        if self.state != "INSTALLING":
            raise RuntimeError("installation is not in progress")
        verification = verification or {"status": "verified"}
        if verification.get("real_installation") is False:
            raise RuntimeError("real installation verification is required")
        self.advance("READY_FOR_BENCHMARK", installation_verification=verification)

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
        verification = self.data.get("installation_verification") or {}
        if verification.get("real_installation") is False:
            raise RuntimeError("real installation verification is required")
        handoff = {
            "schema_version": "1.0",
            "status": "benchmark_authorized",
            "benchmark": benchmark,
            "execution_authorized": True,
            "installation_verified": True,
        }
        self.advance("EXECUTION_AUTHORIZED", benchmark_consent="granted", rc1_handoff=handoff)
        return handoff

    def complete(self, execution_id: str) -> None:
        if self.state != "EXECUTION_AUTHORIZED":
            raise RuntimeError("RC1 execution has not been authorized")
        self.advance("COMPLETE", execution_id=execution_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "state": self.state,
            "gates": {
                "hardware_ready": self.state in {
                    "HARDWARE_READY", "MODEL_SELECTED", "STACK_SELECTED",
                    "READY_FOR_INSTALL", "CONSENT_REQUIRED", "INSTALLING",
                    "READY_FOR_BENCHMARK", "BENCHMARK_CONSENT_REQUIRED",
                    "EXECUTION_AUTHORIZED", "COMPLETE",
                },
                "model_selected": self.state in {
                    "MODEL_SELECTED", "STACK_SELECTED", "READY_FOR_INSTALL",
                    "CONSENT_REQUIRED", "INSTALLING", "READY_FOR_BENCHMARK",
                    "BENCHMARK_CONSENT_REQUIRED", "EXECUTION_AUTHORIZED", "COMPLETE",
                },
                "stack_selected": self.state in {
                    "STACK_SELECTED", "READY_FOR_INSTALL", "CONSENT_REQUIRED",
                    "INSTALLING", "READY_FOR_BENCHMARK", "BENCHMARK_CONSENT_REQUIRED",
                    "EXECUTION_AUTHORIZED", "COMPLETE",
                },
                "ready_for_install": self.state in {
                    "READY_FOR_INSTALL", "CONSENT_REQUIRED", "INSTALLING",
                    "READY_FOR_BENCHMARK", "BENCHMARK_CONSENT_REQUIRED",
                    "EXECUTION_AUTHORIZED", "COMPLETE",
                },
                "ready_for_benchmark": self.state in {
                    "READY_FOR_BENCHMARK", "BENCHMARK_CONSENT_REQUIRED",
                    "EXECUTION_AUTHORIZED", "COMPLETE",
                },
                "execution_authorized": self.state in {"EXECUTION_AUTHORIZED", "COMPLETE"},
            },
            **self.data,
            "error": self.error,
        }


def main() -> int:
    print(BetaSession().snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
