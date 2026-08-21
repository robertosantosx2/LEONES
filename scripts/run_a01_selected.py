#!/usr/bin/env python3
"""Execute A01 from selector output through runtime-selection.v1.

This is the first concrete bridge from model selection to a real agentic run.
Runtime commands are supplied as trusted argv lists; the script never builds a
shell command from model output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.runtime_gate import gate_selection
from benchmarks.agentic.adapters.llmserve_a01 import execute_a01


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_selected(selection: dict, *, runtime_commands: dict[str, list[str]], workspace: Path,
                 prompt: str, output_path: str = "report.txt", timeout_seconds: float = 60.0) -> dict:
    gate = gate_selection(selection, runtime_commands=runtime_commands)
    executable = [p for p in gate["execution_plans"] if p.get("execution_authorized")]
    if not executable:
        raise RuntimeError("runtime-selection.v1 produced no executable plan; trusted runtime command is required")
    plan = executable[0]
    workspace.mkdir(parents=True, exist_ok=True)
    result = execute_a01(plan, prompt=prompt, workspace=workspace,
                         lookup_model=lambda model_id: {"id": model_id, "name": "Beta"} if model_id == "demo-2" else {},
                         write_report=lambda path, name: (Path(path).write_text(f"Model: {name}\n", encoding="utf-8") or path),
                         output_path=output_path, timeout_seconds=timeout_seconds)
    result["runtime_selection"] = gate
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--runtime-commands", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt", default="Execute A01. Return only JSONL tool calls.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run_selected(_load(args.selection), runtime_commands=_load(args.runtime_commands),
                          workspace=args.workspace, prompt=args.prompt)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"A01 status={result['agentic']['outcome']['status']} evidence={result['evidence']['evidence_type']} -> {args.out}")
    return 0 if result["agentic"]["outcome"]["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
