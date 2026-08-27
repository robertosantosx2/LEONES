#!/usr/bin/env python3
"""Canonical A01 grader: tool order, target model and artifact content."""
from __future__ import annotations

from pathlib import Path
from typing import Any

A01_GRADER_ID = "A01-grader"
A01_GRADER_VERSION = "1.1"
EXPECTED_TOOLS = ["lookup_model", "write_report"]


def grade_a01(*, tool_requests: list[dict[str, Any]], model: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
    """Grade A01 against the selected model rather than a fixture identity."""
    tools = [item.get("tool") for item in tool_requests]
    requested_id = ((tool_requests[0].get("arguments") or {}).get("model_id") if tool_requests else None)
    expected_id = str(model.get("id") or "")
    expected_name = str(model.get("name") or expected_id)
    artifact_exists = artifact_path.is_file()
    content = artifact_path.read_text(encoding="utf-8") if artifact_exists else ""
    checks = {
        "tool_order": tools == EXPECTED_TOOLS,
        "target_model": bool(expected_id) and requested_id == expected_id,
        "lookup_result": bool(expected_name) and model.get("name") == expected_name,
        "artifact_exists": artifact_exists,
        "artifact_contains_model": bool(expected_name) and expected_name in content,
    }
    passed = all(checks.values())
    return {"id": A01_GRADER_ID, "version": A01_GRADER_VERSION,
            "status": "passed" if passed else "failed", "score": 1.0 if passed else 0.0,
            "checks": checks}


__all__ = ["A01_GRADER_ID", "A01_GRADER_VERSION", "grade_a01"]
