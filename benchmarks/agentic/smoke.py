"""Deterministic smoke execution for Agentic Benchmark V1.

This validates the benchmark machinery itself, not model intelligence. It is
safe to run locally and is deliberately excluded from official benchmark
aggregates.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from graders import grade_text_equals
from runner import RunConfig, Trace, build_result, execute_tool, write_result
from tools import Sandbox


def run_smoke(output: str | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="leones-agentic-") as directory:
        sandbox = Sandbox(Path(directory))
        trace = Trace()
        execute_tool(trace, "filesystem.write_text", sandbox.write_text, relative="answer.txt", content="42")
        grade = grade_text_equals(sandbox.root, "answer.txt", "42")
        result = build_result(
            RunConfig("leones-agentic-smoke", "1.0", "A03-001", "1.0"),
            trace,
            model={"name": "benchmark-harness-smoke"},
            hardware={"ram_gb": 0, "os": "smoke"},
            inference={},
            outcome={"status": grade.status, "score": grade.score, "details": ";".join(grade.checks)},
            metrics={"tool_calls": 1, "tool_errors": 0, "recovery_count": 0},
            runtime={"name": "harness"},
            scaffold={"name": "agentic-v1-smoke"},
            environment={"network": "disabled", "demo": "true"},
            tools=[{"name": "filesystem.write_text"}],
            grader={"name": "text-equals", "version": "1"},
        )
        result["demo"] = True
        if output:
            write_result(result, output)
        return result


if __name__ == "__main__":
    result = run_smoke()
    print(result["agentic"]["outcome"])
