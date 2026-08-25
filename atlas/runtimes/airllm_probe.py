"""Normalize a successful AirLLM runtime probe into verified RULA evidence.

This module does not execute AirLLM. It validates a probe result produced by a
real LEONES execution and emits the evidence needed by runtime-selection.v1.
"""
from __future__ import annotations

from typing import Any


def verify_airllm_probe(probe: dict[str, Any]) -> dict[str, Any]:
    required = ("runtime", "model", "hardware", "result", "evidence")
    if any(key not in probe for key in required):
        raise ValueError("runtime-probe.v1 is incomplete")
    runtime = probe["runtime"]
    result = probe["result"]
    evidence = probe["evidence"]
    if runtime.get("name", "").lower() != "airllm":
        raise ValueError("probe runtime is not AirLLM")
    if not runtime.get("identity_verified"):
        raise ValueError("AirLLM identity is not verified")
    if result.get("status") != "passed":
        raise ValueError("AirLLM probe did not pass")
    if evidence.get("evidence_type") != "leones_measurement":
        raise ValueError("AirLLM probe is not LEONES measurement evidence")
    return {
        "runtime": "airllm",
        "runtime_version": runtime["version"],
        "runtime_commit": runtime.get("commit"),
        "rula": True,
        "rula_status": "verified",
        "evidence_type": "leones_measurement",
        "execution_id": evidence.get("execution_id"),
        "measured_at": evidence.get("measured_at"),
        "model": probe["model"],
        "hardware": probe["hardware"],
        "performance": {
            "ttft_ms": result.get("ttft_ms"),
            "tokens_per_second": result.get("tokens_per_second"),
            "tool_errors": result.get("tool_errors", 0),
            "recovery_count": result.get("recovery_count", 0),
        },
    }
