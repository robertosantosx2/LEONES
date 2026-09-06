from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime_selection.handoff import build_handoffs
from runtime_selection.hermes import _extract_json
from runtime_selection.user_selection import create_selection, validate_selection


def _decision() -> dict:
    return {
        "profile": "balanced",
        "recommended_model_id": "model-a",
        "candidates": [
            {"model_id": "model-a", "name": "A", "quantization": "Q4_K_M"},
            {"model_id": "model-b", "name": "B", "quantization": "Q4_K_M"},
        ],
    }


def test_hermes_json_parser_accepts_clean_and_fencedish_json() -> None:
    assert _extract_json('{"selected_model_id":"model-a"}')['selected_model_id'] == 'model-a'
    assert _extract_json('answer\n{"selected_model_id":"model-b"}\n')['selected_model_id'] == 'model-b'


def test_both_stacks_produce_two_declarative_handoffs() -> None:
    selection = create_selection(_decision(), "model-a", stack="both")
    validate_selection(selection)
    plans = build_handoffs(selection)
    assert {plan.runtime_id for plan in plans} == {"magnitude", "ods"}
    assert all(plan.model_ref == "model-a" for plan in plans)
    assert all(plan.selection_metadata["selector"] == "hermes" for plan in plans)


def test_selection_never_authorizes_execution() -> None:
    selection = create_selection(_decision(), "model-b", stack="magnitude")
    assert selection["execution_authorized"] is False
    assert selection["measurement_authorized"] is False
    assert selection["measured"] is False


def test_task_catalog_has_ten_canonical_tasks() -> None:
    text = Path("benchmarks/agentic/tasks.yaml").read_text(encoding="utf-8")
    assert text.count("- id:") == 10
