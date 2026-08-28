from __future__ import annotations
import json
from pathlib import Path
import pytest
from scripts.validate_e2e_trace import validate


def base():
    names = ["hardware", "selection", "runtime", "execution", "measurement", "evidence", "decision", "validation", "promotion", "publication", "recommendation"]
    return {"schema": "leones-e2e-trace.v1", "trace_id": "t-001", "status": "planned", "stages": [{"name": n, "status": "pending"} for n in names]}


def test_planned_trace_is_valid():
    validate(base())


def test_complete_stage_requires_reference():
    payload = base(); payload["stages"][0] = {"name": "hardware", "status": "complete"}
    with pytest.raises(ValueError, match="requires ref"):
        validate(payload)


def test_measured_trace_requires_evidence_chain():
    payload = base(); payload["status"] = "measured"
    for stage in payload["stages"]:
        if stage["name"] in {"execution", "measurement"}:
            stage.update(status="complete", ref=f"ref-{stage['name']}")
    with pytest.raises(ValueError, match="requires execution"):
        validate(payload)


def test_published_trace_requires_publication_chain():
    payload = base(); payload["status"] = "published"
    for stage in payload["stages"]:
        if stage["name"] in {"validation", "promotion"}:
            stage.update(status="complete", ref=f"ref-{stage['name']}")
    with pytest.raises(ValueError, match="requires validation"):
        validate(payload)
