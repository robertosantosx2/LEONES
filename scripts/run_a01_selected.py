#!/usr/bin/env python3
"""Execute A01 from selector output through runtime-selection.v1.

This is the first concrete bridge from model selection to a real agentic run.
Runtime commands are supplied as trusted argv lists; the script never builds a
shell command from model output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# When executed as ``python scripts/run_a01_selected.py`` Python puts only the
# scripts/ directory on sys.path. Bootstrap the repository root so the CLI is
# usable from a clean shell without requiring PYTHONPATH=.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.runtime_gate import gate_selection
from scripts.hardware_profile import profile as probe_hardware
from benchmarks.agentic.adapters.llmserve_a01 import execute_a01


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_report(path: str, name: str) -> str:
    target = Path(path)
    target.write_text(f"Model: {name}\n", encoding="utf-8")
    return str(target)


def run_selected(
    selection: dict,
    *,
    runtime_commands: dict[str, list[str]],
    workspace: Path,
    prompt: str,
    output_path: str = "report.txt",
    timeout_seconds: float = 60.0,
) -> dict:
    # Capture the real host profile at execution time so measured A01
    # evidence preserves the hardware on which the runtime actually ran.
    host = probe_hardware()
    memory = host.get("memory", {})
    total_bytes = memory.get("total_bytes")
    ram_gb = (
        round(float(total_bytes) / (1024**3), 1)
        if total_bytes is not None
        else 0
    )
    cpu_info = host.get("cpu") or {}
    hardware = {
        "ram_gb": ram_gb,
        "os": host.get("platform", {}).get("system", "unknown"),
        "cpu": cpu_info.get("model"),
        "gpu": (
            (host.get("gpu") or [{}])[0].get("description")
            if host.get("gpu")
            else None
        ),
        "vram_gb": host.get("vram_gb"),
        "host_memory_bandwidth_gbps": host.get("host_memory_bandwidth_gbps")
        or (host.get("measurements") or {}).get("memory_bandwidth_gbps"),
        "pcie_h2d_bandwidth_gbps": host.get("pcie_h2d_bandwidth_gbps")
        or (host.get("measurements") or {}).get("pcie_h2d_bandwidth_gbps"),
        "cpu_moe_bandwidth_gbps": host.get("cpu_moe_bandwidth_gbps")
        or (host.get("measurements") or {}).get("cpu_moe_bandwidth_gbps"),
    }

    gate = gate_selection(
        selection,
        runtime_commands=runtime_commands,
        hardware=hardware,
    )
    executable = [
        p for p in gate["execution_plans"] if p.get("execution_authorized")
    ]
    if not executable:
        raise RuntimeError(
            "runtime-selection.v1 produced no executable plan; "
            "trusted runtime command is required"
        )
    plan = executable[0]
    workspace.mkdir(parents=True, exist_ok=True)
    selected_model = plan.get("model", {})
    selected_model_id = str(plan.get("model_id") or selected_model.get("id") or "")
    selected_model_name = str(selected_model.get("name") or selected_model_id)

    def lookup_model(model_id: str) -> dict[str, str]:
        if model_id != selected_model_id:
            return {}
        return {"id": selected_model_id, "name": selected_model_name}

    result = execute_a01(
        plan,
        prompt=prompt,
        workspace=workspace,
        lookup_model=lookup_model,
        write_report=_write_report,
        output_path=output_path,
        timeout_seconds=timeout_seconds,
    )
    result["runtime_selection"] = gate
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--runtime-commands", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--prompt", default="Execute A01. Return only JSONL tool calls."
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run_selected(
        _load(args.selection),
        runtime_commands=_load(args.runtime_commands),
        workspace=args.workspace,
        prompt=args.prompt,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    status = result["agentic"]["outcome"]["status"]
    evidence_type = result["evidence"]["evidence_type"]
    print(f"A01 status={status} evidence={evidence_type} -> {args.out}")
    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
