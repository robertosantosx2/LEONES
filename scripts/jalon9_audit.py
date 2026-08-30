#!/usr/bin/env python3
"""JALÓN 9 declarative audit: recommendation contract and boundaries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(*args: str) -> None:
    result = subprocess.run(args, cwd=ROOT, text=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    required = [
        "docs/jalones/jalon9.md",
        "schemas/leones-recommendation.v1.json",
        "scripts/jalon9_recommend.py",
        "tests/test_jalon9_recommendation.py",
        "scripts/validate_recommendation_gate.py",
    ]
    for path in required:
        if not (ROOT / path).is_file():
            fail(f"missing canonical component: {path}")

    print("============================================================")
    print("LEONES — JALÓN 9 RECOMMENDATION AUDIT")
    print("============================================================")
    print(f"BRANCH: {subprocess.check_output(['git','branch','--show-current'], cwd=ROOT, text=True).strip()}")
    print("========== CONTRACT ==========")
    print("PASS: canonical recommendation contract present")
    print("========== RECOMMENDATION TESTS ==========")
    run(sys.executable, "-m", "pytest", "-q", "tests/test_jalon9_recommendation.py")
    print("PASS: recommendation contract validation")
    print("========== STATIC INVARIANTS ==========")
    schema = (ROOT / "schemas/leones-recommendation.v1.json").read_text(encoding="utf-8")
    validator = (ROOT / "scripts/jalon9_recommend.py").read_text(encoding="utf-8")
    for token in ("decision_ref", "evidence_refs", "minimum_evidence_met", "trace_ref"):
        if token not in schema:
            fail(f"missing recommendation contract field: {token}")
    for forbidden in ("ranking_score", "estimated_tps", "tokens_per_second_estimate"):
        if forbidden not in validator:
            # The validator must mention the boundary explicitly so drift is auditable.
            fail(f"missing forbidden-field invariant: {forbidden}")
    print("PASS: recommendation reuses decision/evidence and introduces no scoring engine")
    print("========== DIFF ==========")
    run("git", "diff", "--check")
    print("PASS: git diff --check")
    print("============================================================")
    print("JALÓN 9 — MACHINE-READABLE RESULT")
    print("CONTRACT_GATE=PASS")
    print("RECOMMENDATION_GATE=PASS")
    print("INVARIANT_GATE=PASS")
    print("DIFF_GATE=PASS")
    print("JALON9_RECOMMENDATION_CLOSE=PASS")
    print("AUDIT_EXIT_CODE=0")
    print("============================================================")


if __name__ == "__main__":
    main()
