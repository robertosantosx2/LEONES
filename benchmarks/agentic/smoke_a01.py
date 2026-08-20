#!/usr/bin/env python3
"""Deterministic A01 smoke run for the Agentic Benchmark V1 instrumentation.

This is a harness test, not a model benchmark: it proves that task/tool/trace/
grader/result plumbing works before a real model adapter is connected.
"""
from __future__ import annotations

from pathlib import Path

from runner import RunConfig, Trace, build_result, execute_tool


CATALOG = [
    {"id": "demo-1", "name": "Alpha"},
    {"id": "demo-2", "name": "Beta"},
]


def lookup_model(model_id: str) -> dict[str, str]:
    for model in CATALOG:
        if model["id"] == model_id:
            return model
    raise KeyError(model_id)


def write_report(path: str, name: str) -> str:
    Path(path).write_text(f"Model: {name}\n", encoding="utf-8")
    return path


def run_smoke(output_path: str = "/tmp/leones-a01-report.txt") -> dict:
    trace = Trace()
    config = RunConfig("LEONES-Agentic", "1.0", "A01", "1.0", max_tool_calls=2)

    trace.add("model", name="deterministic-smoke-agent", status="started")
    model = execute_tool(trace, "lookup_model", lookup_model, model_id="demo-2", tool_calls_so_far=0, max_tool_calls=2)
    artifact = execute_tool(
        trace,
        "write_report",
        write_report,
        path=output_path,
        name=model["name"],
        tool_calls_so_far=1,
        max_tool_calls=2,
    )
    content = Path(artifact).read_text(encoding="utf-8")
    success = model["name"] == "Beta" and "Beta" in content
    trace.add("artifact", name="report.txt", status="verified", details={"contains_beta": "Beta" in content})
    trace.add("grader", name="A01-grader", status="passed" if success else "failed")

    return build_result(
        config,
        trace,
        model={"name": "deterministic-smoke-agent", "revision": "smoke"},
        hardware={"ram_gb": 1, "os": "test"},
        inference={},
        outcome={"status": "success" if success else "failed", "score": 1.0 if success else 0.0},
        metrics={"tool_calls": 2, "tool_errors": 0, "recovery_count": 0},
        runtime={"name": "smoke"},
        scaffold={"name": "A01-smoke"},
        environment={"mode": "deterministic"},
        tools=[{"name": "lookup_model"}, {"name": "write_report"}],
        grader={"id": "A01-grader", "version": "1.0", "status": "passed" if success else "failed"},
        evidence_type="measured",
        evidence_source="A01-deterministic-smoke",
    )


if __name__ == "__main__":
    import json
    print(json.dumps(run_smoke(), ensure_ascii=False, indent=2))
