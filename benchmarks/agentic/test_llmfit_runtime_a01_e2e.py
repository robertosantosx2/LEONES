"""Integration proof: LLMFit candidate -> runtime-selection.v1 -> A01."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from atlas.llmfit_adapter import llmfit_candidate_to_atlas, to_runtime_selection
from benchmarks.agentic.adapters.llmserve_a01 import execute_a01


def test_llmfit_estimate_cannot_authorize_a01(tmp_path: Path) -> None:
    record = llmfit_candidate_to_atlas({
        "id": "demo-2",
        "name": "Demo-2",
        "parameters_b": 2,
        "memory_gb": 2.0,
        "fits_memory": True,
        "runtime": "fixture-runtime",
    })

    selection = to_runtime_selection(record, trusted_runtime_command=[sys.executable, "-c", "pass"])
    assert selection["schema"] == "runtime-selection.v1"
    assert selection["selection"]["evidence_level"] == "Estimated"
    assert selection["execution_authorized"] is False


def test_llmfit_verified_runtime_selection_reaches_a01(tmp_path: Path) -> None:
    record = llmfit_candidate_to_atlas({
        "id": "demo-2",
        "name": "Demo-2",
        "parameters_b": 2,
        "memory_gb": 2.0,
        "fits_memory": True,
        "runtime": "fixture-runtime",
        "context_length": 128,
    })

    # This is deliberately an explicit verification boundary, not an LLMFit claim.
    record["recommendation"]["rula"] = True
    record["recommendation"]["rula_status"] = "verified"
    fake_runtime = tmp_path / "fixture_runtime.py"
    fake_runtime.write_text(
        "import json; print(json.dumps({'tool':'lookup_model','arguments':{'model_id':'demo-2'}})); "
        "print(json.dumps({'tool':'write_report','arguments':{'path':'report.txt'}}))",
        encoding="utf-8",
    )
    selection = to_runtime_selection(record, trusted_runtime_command=[sys.executable, str(fake_runtime)])

    assert selection["execution_authorized"] is True
    assert selection["selection"]["evidence_level"] == "Estimated"

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def lookup_model(model_id: str) -> dict[str, str]:
        assert model_id == "demo-2"
        return {"id": "demo-2", "name": "Beta"}

    def write_report(path: str, model_name: str) -> str:
        target = Path(path)
        target.write_text(f"Model: {model_name}\n", encoding="utf-8")
        return str(target)

    result = execute_a01(
        selection,
        prompt="A01 fixture prompt",
        workspace=workspace,
        lookup_model=lookup_model,
        write_report=write_report,
    )

    assert result["outcome"]["status"] == "success"
    assert result["outcome"]["score"] == 1.0
    assert result["evidence_type"] == "measured"
    assert result["metrics"]["tool_calls"] == 2
    assert result["metrics"]["runtime_wall_seconds"] >= 0
    assert (workspace / "report.txt").read_text(encoding="utf-8") == "Model: Beta\n"
