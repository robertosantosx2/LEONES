#!/usr/bin/env python3
"""Small, dependency-free adapter for LLMFit JSON output.

LLMFit is optional. This module never treats estimated throughput as a
LEONES measurement. It normalizes the external result so the Router can
apply Atlas, evidence, CABE/RULA and measured-performance rules afterwards.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any


def _first(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def normalize_candidate(raw: dict[str, Any], *, observed_at: str | None = None) -> dict[str, Any]:
    """Normalize one LLMFit candidate without inventing measurements."""
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()
    return {
        "source": "llmfit",
        "observed_at": observed_at,
        "model_id": _first(raw, "model", "model_id", "name", "id"),
        "provider": raw.get("provider"),
        "params": _first(raw, "params", "parameters", "parameter_count"),
        "quantization": _first(raw, "quant", "quantization"),
        "context": _first(raw, "context", "context_length", "ctx"),
        "fit_level": _first(raw, "fit", "fit_level"),
        "estimated_tps": _first(raw, "tok_s", "tps", "estimated_tps", "tokens_per_second"),
        "measured_tps": None,
        "memory_required_gb": _first(raw, "memory_gb", "mem_gb", "memory_required_gb"),
        "run_mode": _first(raw, "mode", "run_mode"),
        "runtime": raw.get("runtime"),
        "quality_score": _first(raw, "score", "quality"),
        "estimate_basis": "llmfit-estimate",
        "raw": raw,
    }


def normalize(payload: Any, *, observed_at: str | None = None) -> dict[str, Any]:
    """Normalize common JSON shapes returned by LLMFit commands."""
    if isinstance(payload, list):
        candidates = payload
        system = None
    elif isinstance(payload, dict):
        system = payload.get("system") or payload.get("hardware")
        candidates = (
            payload.get("models")
            or payload.get("recommendations")
            or payload.get("results")
            or payload.get("data")
            or []
        )
        if isinstance(candidates, dict):
            candidates = candidates.get("models") or candidates.get("results") or []
    else:
        raise TypeError("LLMFit JSON must be an object or list")

    if not isinstance(candidates, list):
        raise ValueError("Could not locate a model list in LLMFit JSON")

    return {
        "source": "llmfit",
        "source_version": None,
        "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
        "hardware": system,
        "candidates": [normalize_candidate(item) for item in candidates if isinstance(item, dict)],
    }


def run_llmfit(args: list[str]) -> dict[str, Any]:
    """Run llmfit with JSON output and normalize it."""
    binary = shutil.which("llmfit")
    if not binary:
        raise FileNotFoundError("llmfit is not installed or not in PATH")
    command = [binary, *args]
    if "--json" not in command:
        command.append("--json")
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return normalize(json.loads(completed.stdout))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Read previously captured LLMFit JSON instead of executing llmfit")
    parser.add_argument("llmfit_args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()

    if ns.input:
        with open(ns.input, encoding="utf-8") as fh:
            payload = json.load(fh)
        result = normalize(payload)
    else:
        args = ns.llmfit_args or ["recommend"]
        result = run_llmfit(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
