from pathlib import Path

import pytest

from a01_contract import A01Context, run_a01_tools, safe_workspace_path, validate_runtime_plan


def test_requires_execution_authorization():
    with pytest.raises(PermissionError):
        validate_runtime_plan({"model": {}, "runtime": {}, "hardware": {}})


def test_rejects_unknown_tool():
    with pytest.raises(PermissionError):
        validate_runtime_plan({
            "execution_authorized": True,
            "model": {"id": "demo-2"},
            "runtime": {"name": "test"},
            "hardware": {"ram_gb": 1},
            "tool_names": ["shell"],
        })


def test_workspace_cannot_escape(tmp_path: Path):
    with pytest.raises(PermissionError):
        safe_workspace_path(tmp_path, "../escape.txt")


def test_a01_tools_are_deterministic_and_sandboxed(tmp_path: Path):
    catalog = {"demo-2": {"id": "demo-2", "name": "Beta"}}

    def lookup_model(model_id: str):
        return catalog[model_id]

    def write_report(path: str, name: str):
        Path(path).write_text(f"Model: {name}\n", encoding="utf-8")
        return path

    ctx = A01Context(
        workspace=tmp_path,
        model={"id": "demo-2", "revision": "test"},
        runtime={"name": "test"},
        hardware={"ram_gb": 1},
    )
    model, artifact = run_a01_tools(ctx, lookup_model, write_report)
    assert model["name"] == "Beta"
    assert Path(artifact).read_text(encoding="utf-8").strip() == "Model: Beta"
