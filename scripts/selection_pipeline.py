#!/usr/bin/env python3
"""Build the smallest traceable LEONES model-selection decision.

The pipeline answers one question: **given this workload, observed hardware,
fit evidence and chosen runtime, what should LEONES test next?**

Order is contractual:

    workload → hardware → inference config → model candidates → fit reduction
    → runtime gate → authorized execution plan

The script may use LLMFit and other external fit sources as *estimation*.
Those signals are never treated as physical measurements. A later runtime
runner owns execution, and the evidence layer owns measurement acceptance.

Inputs are local JSON/CSV files plus the selected runtime. Output is one JSON
selection artifact. The script does not download models, execute inference,
benchmark hardware or publish results.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from scripts.fit_consensus import (
    CATEGORIES,
    build_consensus,
    reduce_estimator_outputs,
)
from scripts.hardware_profile import profile as probe_hardware
from scripts.inference_config import resolve_inference_configuration
from scripts.model_selector import DEFAULT_FEED, select
from scripts.runtime_gate import gate_selection


def load_rows(path: Path) -> list[dict[str, str]]:
    """Load a UTF-8 CSV feed without changing its values or provenance."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _norm(value: object) -> str:
    """Normalize identifiers only for comparison; preserve original values."""
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _representative_ids(reduction: dict) -> set[str]:
    """Return normalized model IDs selected by the fit consensus."""
    return {
        _norm(item.get("model_id"))
        for category in CATEGORIES
        for item in reduction.get("selected", {}).get(category, [])
    }


def enrich_external_fit(selection: dict, fit_sources: dict | None) -> dict:
    """Keep the agreed fit-consensus representatives and provenance.

    Six estimator outputs are required by the current selection contract. The
    reduction produces three representatives per category. Their role is to
    reduce the search space before physical execution; it is not a benchmark.
    """
    if not fit_sources:
        raise ValueError(
            "six fit estimator outputs are required before model valuation"
        )

    reduction = reduce_estimator_outputs(fit_sources)
    selection["fit_cross_validation"] = reduction
    selected_ids = _representative_ids(reduction)

    for candidate in selection.get("candidates", []):
        model_id = candidate.get("model_id") or candidate.get("model_name")
        candidate["fit_cross_validation"] = build_consensus(
            model_id, fit_sources
        )
        candidate["parameter_representative"] = _norm(model_id) in selected_ids

    # Only consensus representatives continue. The original selection data
    # remains embedded in the artifact, so this is a reduction, not a rewrite.
    selection["candidates"] = [
        candidate
        for candidate in selection.get("candidates", [])
        if candidate.get("parameter_representative")
    ]
    selection["counts"]["fit_representatives"] = len(selection["candidates"])
    selection["counts"]["fit_representatives_expected"] = 9
    return selection


def build_pipeline(
    *,
    workload: str,
    feed: Path,
    context: int,
    top_n: int,
    runtime: str,
    optimizations: list[str],
    llmfit: dict | None = None,
    fit_sources: dict | None = None,
    hardware: dict | None = None,
    runtime_commands: dict[str, list[str]] | None = None,
) -> dict:
    """Build selection, inference configuration and runtime authorization."""
    if not runtime:
        raise ValueError("inference runtime must be decided before model evaluation")

    # Hardware can be injected by tests or a trusted caller. Otherwise this is
    # the single observation boundary: selection never invents host facts.
    host = hardware or probe_hardware()
    memory = host.get("memory", {})
    available_bytes = memory.get("available_bytes") or memory.get("total_bytes")
    if available_bytes is None:
        raise ValueError("hardware profile has no usable memory measurement")

    ram_gb = float(available_bytes) / (1024**3)
    hardware_label = host.get("cpu", {}).get("model") or "unknown-cpu"
    gpus = host.get("gpu") or []
    vram_gb = float(host.get("vram_gb") or 0)
    hardware_v1 = {
        "ram_gb": ram_gb,
        "os": host.get("platform", {}).get("system", "unknown"),
        "cpu": hardware_label,
        "gpu": gpus[0].get("description") if gpus else None,
        "vram_gb": vram_gb,
    }

    measurements = host.get("measurements") or host.get("measurement") or {}
    hardware_v1.update(
        {
            "host_memory_bandwidth_gbps": host.get("host_memory_bandwidth_gbps")
            or measurements.get("memory_bandwidth_gbps"),
            "pcie_h2d_bandwidth_gbps": host.get("pcie_h2d_bandwidth_gbps")
            or measurements.get("pcie_h2d_bandwidth_gbps"),
            "cpu_moe_bandwidth_gbps": host.get("cpu_moe_bandwidth_gbps")
            or measurements.get("cpu_moe_bandwidth_gbps"),
        }
    )

    # Fix inference conditions before comparing models. Otherwise the selector
    # could rank candidates under a context/runtime configuration that later
    # changes at execution time.
    inference = resolve_inference_configuration(
        workload=workload,
        hardware=hardware_v1,
        runtime=runtime,
        optimizations=optimizations,
        context_tokens=context,
    )

    selection = select(
        load_rows(feed),
        workload=workload,
        hardware=hardware_label,
        ram_gb=ram_gb,
        vram_gb=vram_gb,
        context_tokens=context,
        top_n=top_n,
        llmfit=llmfit,
        required_runtime=runtime,
        optimization_families=optimizations,
    )
    selection["inference_configuration"] = inference
    selection = enrich_external_fit(selection, fit_sources)

    # The runtime gate is the last decision boundary. It can authorize an
    # execution plan; it cannot execute the runtime or claim measured output.
    gate = gate_selection(
        selection,
        runtime_commands=runtime_commands,
        hardware=hardware_v1,
    )
    return {
        "schema_version": "1.0",
        "pipeline": "LEONES-selection-pipeline",
        "inference_configuration": inference,
        "hardware": hardware_v1,
        "selection": selection,
        "runtime_selection": gate,
    }


def main() -> int:
    """Run the pipeline from explicit input files and write one JSON artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--optimization", action="append", default=[])
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--llmfit", type=Path, required=True)
    parser.add_argument("--fit-sources", type=Path, required=True)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--top-n", type=int, default=9)
    parser.add_argument("--runtime-commands", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8"))
    fit_sources = json.loads(args.fit_sources.read_text(encoding="utf-8"))
    commands = (
        json.loads(args.runtime_commands.read_text(encoding="utf-8"))
        if args.runtime_commands
        else None
    )

    result = build_pipeline(
        workload=args.workload,
        feed=args.feed,
        context=args.context,
        top_n=args.top_n,
        runtime=args.runtime,
        optimizations=args.optimization,
        llmfit=llmfit,
        fit_sources=fit_sources,
        runtime_commands=commands,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"selection={result['selection']['counts']} "
        f"runtime_plans={result['runtime_selection']['counts']['plans']} "
        f"-> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
