#!/usr/bin/env python3
"""Normalize runtime-reported measurements without inventing benchmark data."""
from __future__ import annotations

import json
import re
from typing import Any

_TPS_KEYS = ("measured_tps", "tokens_per_second", "tok_s", "tokens_sec")
_TPS_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]+(?:\.[0-9]+)?)\s*(?:tok/s|tokens?/s|tokens?\s+per\s+second)\b", re.I)


def extract_measured_tps(output: str) -> float | None:
    """Extract an explicitly reported throughput value; return None otherwise."""
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            value = None
        if isinstance(value, dict):
            for key in _TPS_KEYS:
                candidate = value.get(key)
                if isinstance(candidate, (int, float)) and candidate >= 0:
                    return float(candidate)
        match = _TPS_RE.search(line)
        if match:
            return float(match.group(1))
    return None


def build_measurement(*, elapsed_seconds: float, output: str, source: str) -> dict[str, Any]:
    """Build evidence while keeping unknown measurements explicitly null."""
    return {
        "evidence_type": "measured",
        "source": source,
        "wall_seconds": round(elapsed_seconds, 6),
        "measured_tps": extract_measured_tps(output),
        "measurement_status": "reported_by_runtime" if extract_measured_tps(output) is not None else "runtime_value_not_reported",
    }
