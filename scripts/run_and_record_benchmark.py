#!/usr/bin/env python3
"""Execute one command and record its observed tokens-per-second result.

This small compatibility recorder is used by the active llama.cpp execution
bridge. It does not select models, authorize plans or publish results.
"""

from __future__ import annotations

import re
import subprocess
import uuid
from typing import Any

from scripts.record_benchmark import record_measurement


def run_and_record(
    command: list[str], metadata: dict[str, Any], pattern: str
) -> dict[str, Any]:
    """Run a command and record the observed tokens-per-second measurement."""
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(pattern, output)
    if completed.returncode != 0:
        raise RuntimeError(
            f"benchmark command failed with exit code {completed.returncode}"
        )
    if not match:
        raise ValueError(
            "benchmark output does not contain a tokens-per-second measurement"
        )

    data = dict(metadata)
    data["execution_id"] = str(uuid.uuid4())
    data["tokens_per_second"] = float(match.group(1))
    return record_measurement(data)
