#!/usr/bin/env python3
"""Canonical A01 grader: tool order, target model and artifact content."""
from __future__ import annotations

from pathlib import Path
from typing import Any

A01_GRADER_ID = "A01-grader"
A01_GRADER_VERSION = "1.0"
EXPECTED_TOOLS = ["lookup_model", "write_report"]
# Defaults preserve the deterministic fixture contract. Real runs may supply
# the selected model identity explicitly through grade_a01(...).
EXPECTED_MODEL_ID = "demo-2"
EXPECTED_MODEL_NAME = "Beta"


def grade_a01(
    *,
    tool_requests: list[dict[str, Any]],
    model: dict[str, Any],
    artifact_path: Path,
    expected_model_id: str = EXPECTED_MODEL_ID,
    expected_model_name: str = EXPECTED_MODEL_NAME,
) -> dict[str, Any]:
    """Grade A01 against the selected model, without hard-coding a real model.

    The defaults retain the V1 fixture behavior. A real runtime passes the
    selected model identity so the same grader contract can be reused.
    """
    tools = [item.get("tool") for item in tool_requests]
    requested_id = ((tool_requests[0].get("arguments") or {}).get("model_id") if tool_requests else None)
    artifact_exists = artifact_path.is_file()
    content = artifact_path.read_text(encoding="utf-8") if artifact_exists else ""
    checks = {
        "tool_order": tools == EXPECTED_TOOLS,
        "target_model": requested_id == expected_model_id,
        "lookup_result": model.get("name") == expected_model_name,
        "artifact_exists": artifact_exists,
        "artifact_contains_model": expected_model_name in content,
    }
    passed = all(checks.values())
    return {
        "id": A01_GRADER_ID,
        "version": A01_GRADER_VERSION,
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "checks": checks,
    }


__all__ = ["A01_GRADER_ID", "A01_GRADER_VERSION", "grade_a01"]
