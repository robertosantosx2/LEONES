#!/usr/bin/env python3
"""Canonical A01 grader: tool order, target model and artifact content."""
from __future__ import annotations

from pathlib import Path
from typing import Any

A01_GRADER_ID = "A01-grader"
A01_GRADER_VERSION = "1.0"
EXPECTED_TOOLS = ["lookup_model", "write_report"]
EXPECTED_MODEL_ID = "demo-2"
EXPECTED_MODEL_NAME = "Beta"


def grade_a01(*, tool_requests: list[dict[str, Any]], model: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
    tools = [item.get("tool") for item in tool_requests]
    requested_id = ((tool_requests[0].get("arguments") or {}).get("model_id") if tool_requests else None)
    artifact_exists = artifact_path.is_file()
    content = artifact_path.read_text(encoding="utf-8") if artifact_exists else ""
    checks = {
        "tool_order": tools == EXPECTED_TOOLS,
        "target_model": requested_id == EXPECTED_MODEL_ID,
        "lookup_result": model.get("name") == EXPECTED_MODEL_NAME,
        "artifact_exists": artifact_exists,
        "artifact_contains_model": EXPECTED_MODEL_NAME in content,
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
