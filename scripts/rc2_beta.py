#!/usr/bin/env python3
"""Minimal RC2 beta-user flow orchestrator.

RC2-A intentionally orchestrates existing contracts only. It does not install
software, execute runtimes, or create a second benchmark runner.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ODS_FEATURES = [
    "local inference", "Open WebUI", "gateway", "RAG/search", "voice",
    "agents/workflows", "image generation", "privacy", "observability",
]
MAGNITUDE_FEATURES = [
    "local agent", "local models", "hardware profiling", "model recommendation",
    "download/configuration", "local execution", "skills", "OpenAI-compatible endpoints",
]


def load_selection(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("selection must be a JSON object")
    return data


def selection_candidates(selection: dict) -> list[dict]:
    """Read the canonical RC1 candidate list, with legacy-plan compatibility."""
    candidates = selection.get("candidates")
    if isinstance(candidates, list):
        return [item for item in candidates if isinstance(item, dict)]
    plans = selection.get("execution_plans")
    if isinstance(plans, list):
        return [item for item in plans if isinstance(item, dict)]
    return []


def candidate_model_id(candidate: dict) -> str:
    model_id = candidate.get("model_id") or candidate.get("model_name")
    if model_id:
        return str(model_id)
    model = candidate.get("model")
    if isinstance(model, dict):
        return str(model.get("id") or model.get("name") or "unknown")
    if model:
        return str(model)
    return "unknown"


def show_hardware() -> None:
    print("\n[2/7] HARDWARE")
    print(f"  OS:           {platform.system()} {platform.release()}")
    print(f"  Architecture: {platform.machine()}")
    print("  CPU/RAM/GPU:  observed by the selected profiler in the next RC2 phase")
    print("  Unknown data is preserved as unknown/null; nothing is invented.")


def show_stack_choice() -> None:
    print("\n[5/7] ODS / MAGNITUDE — INFORMED CHOICE")
    print("  ODS capabilities:")
    for item in ODS_FEATURES:
        print(f"    - {item}")
    print("  Magnitude capabilities:")
    for item in MAGNITUDE_FEATURES:
        print(f"    - {item}")
    print("  These are capability categories; availability is version/ref dependent.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEONES RC2 beta user flow (RC2-A)")
    parser.add_argument("--selection", type=Path, help="validated selection JSON")
    parser.add_argument("--stack", choices=("ods", "magnitude"), help="preselect the stack")
    parser.add_argument("--benchmark", choices=("yes", "no"), help="benchmark decision")
    args = parser.parse_args(argv)

    print("LEONES — RC2 BETA USER FLOW")
    print("RC2-A: orchestration only; no installation or runtime execution")
    print("\n[1/7] PREFLIGHT")
    print("  ✓ LEONES flow bootstrap")
    show_hardware()
    print("\n[3/7] PROFILING")
    print("  → ODS/Magnitude integration is selected later; no third profiler is created.")
    print("\n[4/7] MODEL CANDIDATES")
    if args.selection:
        try:
            selection = load_selection(args.selection)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"  ERROR: cannot read selection: {exc}", file=sys.stderr)
            return 2
        candidates = selection_candidates(selection)
        print(f"  ✓ loaded {len(candidates)} candidate(s)")
        for candidate in candidates:
            print(f"    - {candidate_model_id(candidate)}")
    else:
        print("  → candidate presentation is wired in the next RC2 phase")
    show_stack_choice()
    if args.stack:
        print(f"  User choice: {args.stack}")
    else:
        print("  User choice: pending")
    print("\n[6/7] PREPARATION")
    print("  → installation/consent/health-check orchestration is RC2-E")
    print("\n[7/7] BENCHMARK")
    decision = args.benchmark or "pending"
    print(f"  User decision: {decision}")
    if decision == "yes":
        print("  → canonical runner/evidence path will be used; no RC2 runner is created")
    elif decision == "no":
        print("  → finish after preparation")
    print("\nRC2-A flow bootstrap: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
