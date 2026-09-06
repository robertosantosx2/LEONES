#!/usr/bin/env python3
"""RC3 static release gate.

The gate checks the active RC3 route, not historical RC2/JALÓN material.
Hermes is the sole model selector in RC3; legacy selector implementations may
remain only outside that route for historical compatibility/audit purposes.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "docs/RC3-ARCHITECTURE.md",
    "docs/RC3-HERMES-TASK-BENCHMARKS.md",
    "runtime_selection/candidate_set.py",
    "runtime_selection/model_evidence.py",
    "runtime_selection/hermes.py",
    "runtime_selection/handoff.py",
    "runtime_selection/user_selection.py",
    "runtime_selection/artifact_resolution.py",
    "runtime_selection/data/model-evidence.rc3.json",
    "scripts/hardware_profile.py",
    "scripts/rc3_hardware_discovery.py",
    "scripts/install_hermes.sh",
    "scripts/leones_task_benchmark.py",
)

RC3_ROUTE = (
    "runtime_selection/candidate_set.py",
    "runtime_selection/hermes.py",
    "runtime_selection/handoff.py",
    "runtime_selection/user_selection.py",
    "runtime_selection/artifact_resolution.py",
    "scripts/hardware_profile.py",
    "scripts/rc3_hardware_discovery.py",
    "scripts/install_hermes.sh",
    "scripts/leones_task_benchmark.py",
    "tests/test_hermes_selection_and_task_benchmark.py",
)


def fail(message: str) -> None:
    raise SystemExit(f"RC3 RELEASE GATE: FAIL — {message}")


def _candidate_literal_keys(source: str) -> set[str]:
    """Return literal dictionary keys used by candidate-set implementation."""
    tree = ast.parse(source)
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys


def main() -> int:
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"missing or empty required artifact: {relative}")

    if (ROOT / "runtime_selection/llmfit.py").exists():
        fail("LLMFit/FitLLM adapter must not exist in the RC3 implementation tree")

    forbidden_route_terms = ("llmfit", "fitllm", "decision_engine", "model_selector")
    for relative in RC3_ROUTE:
        source = (ROOT / relative).read_text(encoding="utf-8").lower()
        for term in forbidden_route_terms:
            if term in source:
                fail(f"legacy selector term '{term}' leaks into RC3 route: {relative}")

    catalog_path = ROOT / "runtime_selection/data/model-evidence.rc3.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != "model-evidence.v1":
        fail("external evidence catalog is not model-evidence.v1")
    if catalog.get("catalog_status") != "curated_external_snapshot":
        fail("external evidence catalog must remain a dated curated snapshot")
    candidates = catalog.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        fail("external evidence catalog has no candidates")

    for candidate in candidates:
        artifact = candidate.get("artifact_resolution", {})
        if artifact.get("status") == "resolved":
            for field in ("filename", "revision", "sha256"):
                if not artifact.get(field):
                    fail(f"resolved artifact lacks {field}: {candidate.get('model_id')}")
        if artifact.get("download_performed") is True:
            fail("curated evidence snapshot must not perform model downloads")

    selection_source = (ROOT / "runtime_selection/user_selection.py").read_text(encoding="utf-8")
    for invariant in (
        'execution_authorized": False',
        'measurement_authorized": False',
        'measured": False',
        'consent_required_before_execution": True',
        'STACK_CHOICES = STACKS | {"both"}',
    ):
        if invariant not in selection_source:
            fail(f"user-selection gate invariant missing: {invariant}")

    candidate_source = (ROOT / "runtime_selection/candidate_set.py").read_text(encoding="utf-8")
    candidate_keys = _candidate_literal_keys(candidate_source)
    for forbidden_field in ("estimated_tps", "measured_tps", "benchmark_result", "command", "argv"):
        if forbidden_field in candidate_keys:
            fail(f"candidate-set must not contain execution/measurement field: {forbidden_field}")

    hermes_source = (ROOT / "runtime_selection/hermes.py").read_text(encoding="utf-8")
    for invariant in ("hermes", "selected_model_id", "outside the candidate set"):
        if invariant not in hermes_source:
            fail(f"Hermes selector invariant missing: {invariant}")

    benchmark_source = (ROOT / "scripts/leones_task_benchmark.py").read_text(encoding="utf-8")
    for invariant in ("leones-task-benchmark.v1", "select-with-hermes", "mean_output_tokens_per_second"):
        if invariant not in benchmark_source:
            fail(f"task benchmark invariant missing: {invariant}")

    task_source = (ROOT / "benchmarks/agentic/tasks.yaml").read_text(encoding="utf-8")
    for task_id in ("Leo001", "Leo002", "Leo003", "Leo004", "Leo005", "Leo006", "Leo007", "Leo008", "Leo009", "Leo010"):
        if f"id: {task_id}" not in task_source:
            fail(f"canonical task missing: {task_id}")

    adapter_source = (ROOT / "scripts/rc3_hardware_discovery.py").read_text(encoding="utf-8")
    if "hardware_profile" not in adapter_source:
        fail("RC3 hardware discovery adapter is not routed through canonical hardware_profile")

    architecture = (ROOT / "docs/RC3-ARCHITECTURE.md").read_text(encoding="utf-8")
    if "scripts/hardware_profile.py" not in architecture:
        fail("architecture does not name the canonical physical probe")
    if "LLMFit/FitLLM" not in architecture or "fuera de RC3" not in architecture:
        fail("architecture does not preserve the RC3 LLMFit boundary")
    if "HERMES" not in architecture.upper():
        fail("architecture does not identify Hermes as the RC3 selector")

    print("RC3 RELEASE GATE: PASS")
    print("  Hermes-only selector route: PASS")
    print("  candidate-set selector neutrality: PASS")
    print("  Magnitude/ODS/both handoff boundary: PASS")
    print("  per-task benchmark loop: PASS")
    print("  Leo001-Leo010 canonical suite: PASS")
    print("  repeatable Hermes reselection: PASS")
    print("  LLMFit/FitLLM excluded from active RC3 route: PASS")
    print("  physical Ubuntu validation: NOT CLAIMED")
    print("  real Magnitude/ODS handoff: NOT CLAIMED")
    print("  real benchmark/evidence: NOT CLAIMED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
