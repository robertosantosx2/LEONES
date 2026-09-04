#!/usr/bin/env python3
"""RC3 static release gate.

This gate validates the implementation boundary that can be checked in CI.
It deliberately does not claim physical Ubuntu validation, model download,
stack installation, runtime execution, or measured throughput.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "docs/RC3-ARCHITECTURE.md",
    "runtime_selection/candidate_set.py",
    "runtime_selection/decision_engine.py",
    "runtime_selection/model_evidence.py",
    "runtime_selection/user_selection.py",
    "runtime_selection/artifact_resolution.py",
    "runtime_selection/data/model-evidence.rc3.json",
    "scripts/hardware_profile.py",
    "scripts/rc3_hardware_discovery.py",
)


def fail(message: str) -> None:
    raise SystemExit(f"RC3 RELEASE GATE: FAIL — {message}")


def main() -> int:
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"missing or empty required artifact: {relative}")

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
        status = artifact.get("status")
        if status == "resolved":
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
    ):
        if invariant not in selection_source:
            fail(f"user-selection gate invariant missing: {invariant}")

    adapter_source = (ROOT / "scripts/rc3_hardware_discovery.py").read_text(encoding="utf-8")
    if "hardware_profile" not in adapter_source:
        fail("RC3 hardware discovery adapter is not routed through canonical hardware_profile")

    architecture = (ROOT / "docs/RC3-ARCHITECTURE.md").read_text(encoding="utf-8")
    if "scripts/hardware_profile.py" not in architecture:
        fail("architecture does not name the canonical physical probe")
    if "LLMFit/FitLLM" not in architecture or "fuera de RC3" not in architecture:
        fail("architecture does not preserve the RC3 LLMFit boundary")

    print("RC3 RELEASE GATE: PASS")
    print("  static contracts: PASS")
    print("  candidate/evidence boundary: PASS")
    print("  user-selection boundary: PASS")
    print("  canonical hardware probe boundary: PASS")
    print("  physical Ubuntu validation: NOT CLAIMED")
    print("  real Magnitude/ODS handoff: NOT CLAIMED")
    print("  real benchmark/evidence: NOT CLAIMED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
