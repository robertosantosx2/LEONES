#!/usr/bin/env python3
"""One-command Selector de LLM -> runtime-selection.v1 pipeline.

External fit sources are preserved as evidence/estimates only. They never become
measurements and never authorize execution by themselves.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from scripts.hardware_profile import profile as probe_hardware
from scripts.model_selector import DEFAULT_FEED, select
from scripts.fit_consensus import build_consensus
from scripts.runtime_gate import gate_selection


def load_rows(path: Path) -> list[dict[str, str]]:
    import csv
    with path.open(encoding="utf-8-sig", newline="") as fh: return list(csv.DictReader(fh))


def enrich_external_fit(selection: dict, fit_sources: dict | None) -> dict:
    """Attach cross-validation evidence without changing the selector score."""
    if not fit_sources:
        return selection
    for candidate in selection.get("candidates", []):
        model_id = candidate.get("model_id") or candidate.get("model_name")
        candidate["fit_cross_validation"] = build_consensus(model_id, fit_sources)
    return selection


def build_pipeline(*, workload: str, feed: Path, context: int, top_n: int,
                   llmfit: dict | None = None, fit_sources: dict | None = None,
                   hardware: dict | None = None,
                   runtime_commands: dict[str, list[str]] | None = None) -> dict:
    host = hardware or probe_hardware()
    memory = host.get("memory", {})
    available_bytes = memory.get("available_bytes") or memory.get("total_bytes")
    if available_bytes is None: raise ValueError("hardware profile has no usable memory measurement")
    ram_gb = float(available_bytes) / (1024 ** 3)
    hardware_label = host.get("cpu", {}).get("model") or "unknown-cpu"
    selection = select(load_rows(feed), workload=workload, hardware=hardware_label,
                       ram_gb=ram_gb, vram_gb=0, context_tokens=context, top_n=top_n, llmfit=llmfit)
    selection = enrich_external_fit(selection, fit_sources)
    gpus = host.get("gpu") or []
    measurements = host.get("measurements") or host.get("measurement") or {}
    hardware_v1 = {
        "ram_gb": ram_gb,
        "os": host.get("platform", {}).get("system", "unknown"),
        "cpu": hardware_label,
        "gpu": gpus[0].get("description") if gpus else None,
        "vram_gb": host.get("vram_gb"),
        "host_memory_bandwidth_gbps": host.get("host_memory_bandwidth_gbps") or measurements.get("memory_bandwidth_gbps"),
        "pcie_h2d_bandwidth_gbps": host.get("pcie_h2d_bandwidth_gbps") or measurements.get("pcie_h2d_bandwidth_gbps"),
        "cpu_moe_bandwidth_gbps": host.get("cpu_moe_bandwidth_gbps") or measurements.get("cpu_moe_bandwidth_gbps"),
    }
    gate = gate_selection(selection, runtime_commands=runtime_commands, hardware=hardware_v1)
    return {"schema_version": "1.0", "pipeline": "LEONES-selection-pipeline",
            "hardware": {"cpu_model": hardware_label, "available_ram_gb": ram_gb},
            "selection": selection, "runtime_selection": gate}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", required=True); parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--llmfit", type=Path); parser.add_argument("--fit-sources", type=Path)
    parser.add_argument("--context", type=int, default=4096); parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--runtime-commands", type=Path); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8")) if args.llmfit else None
    fit_sources = json.loads(args.fit_sources.read_text(encoding="utf-8")) if args.fit_sources else None
    commands = json.loads(args.runtime_commands.read_text(encoding="utf-8")) if args.runtime_commands else None
    result = build_pipeline(workload=args.workload, feed=args.feed, context=args.context, top_n=args.top_n,
                            llmfit=llmfit, fit_sources=fit_sources, runtime_commands=commands)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"selection={result['selection']['counts']} runtime_plans={result['runtime_selection']['counts']['plans']} -> {args.out}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
