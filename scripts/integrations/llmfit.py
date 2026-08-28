"""Minimal boundary between LLMFit output and LEONES selection.

LLMFit is an external fit estimator. This module deliberately does not execute
LLMFit, detect hardware, or benchmark models. It only normalizes an already
captured LLMFit JSON result and preserves its provenance as an estimate.
"""

from __future__ import annotations

from typing import Any


SOURCE = "llmfit"
PROVENANCE_KIND = "estimated"


def normalize_result(data: dict[str, Any], *, source_version: str, observed_at: str) -> dict[str, Any]:
    """Normalize one LLMFit result without promoting estimates to measurements."""
    if not isinstance(data, dict):
        raise TypeError("LLMFit result must be an object")
    if not source_version:
        raise ValueError("source_version is required")
    if not observed_at:
        raise ValueError("observed_at is required")

    hardware = data.get("hardware")
    if not isinstance(hardware, dict):
        hardware = {}

    candidate = data.get("candidate")
    if not isinstance(candidate, dict):
        candidate = data

    return {
        "source": SOURCE,
        "source_version": source_version,
        "observed_at": observed_at,
        "hardware": hardware,
        "candidate": {
            "model_id": candidate.get("model_id") or candidate.get("id"),
            "model_name": candidate.get("model_name") or candidate.get("name"),
            "fit": candidate.get("fit"),
            "estimated_tps": candidate.get("estimated_tps") or candidate.get("estimated_speed"),
            "estimated_memory_gb": candidate.get("estimated_memory_gb") or candidate.get("memory_gb"),
            "context_tokens": candidate.get("context_tokens") or candidate.get("context"),
            "quantization": candidate.get("quantization") or candidate.get("quant"),
            "runtime": candidate.get("runtime"),
        },
        "provenance": {
            "kind": PROVENANCE_KIND,
            "raw_artifact_sha256": data.get("raw_artifact_sha256", ""),
        },
    }


def assert_not_measured(record: dict[str, Any]) -> None:
    """Fail closed if an upstream fit record is presented as a measurement."""
    if record.get("provenance", {}).get("kind") != PROVENANCE_KIND:
        raise ValueError("LLMFit records must remain estimated evidence")
    if "measured_tps" in record.get("candidate", {}):
        raise ValueError("LLMFit estimate cannot contain measured_tps")
