#!/usr/bin/env python3
"""One-command dry-run from observed hardware to executable model plans."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.hardware_profile import profile as probe_hardware
from scripts.model_selector import DEFAULT_FEED, select
from scripts.runtime_gate import gate_selection


def load_rows(path: Path) -> list[dict[str, str]]:
    import csv
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def build_pipeline(*, workload: str, feed: Path, context: int, top_n: int,
                   llmfit: dict | None = None, hardware: dict | None = None) -> dict:
    host = hardware or probe_hardware()
    memory = host.get("memory", {})
    available_bytes = memory.get("available_bytes") or memory.get("total_bytes")
    if available_bytes is None:
        raise ValueError("hardware profile has no usable memory measurement")
    ram_gb = float(available_bytes) / (1024 ** 3)
    hardware_label = host.get("cpu", {}).get("model") or "unknown-cpu"
    selection = select(load_rows(feed), workload=workload, hardware=hardware_label,
                       ram_gb=ram_gb, vram_gb=0, context_tokens=context,
                       top_n=top_n, llmfit=llmfit)
    gate = gate_selection(selection)
    return {
        "schema_version": "1.0",
        "pipeline": "LEONES-selection-pipeline",
        "hardware": {"cpu_model": hardware_label, "available_ram_gb": ram_gb},
        "selection": selection,
        "runtime_gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--llmfit", type=Path)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8")) if args.llmfit else None
    result = build_pipeline(workload=args.workload, feed=args.feed,
                            context=args.context, top_n=args.top_n, llmfit=llmfit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"selection={result['selection']['counts']} runtime_plans={result['runtime_gate']['counts']['plans']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
