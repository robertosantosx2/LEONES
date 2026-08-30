#!/usr/bin/env python3
"""Audit the JALON 14 physical-execution handoff.

The audit is intentionally boring: it proves that JALON 14 points at the
already-fixed execution path. It does not benchmark a model and it does not
invent another decision or scoring layer.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/jalones/jalon14.md",
    "scripts/run_a01_selected.py",
    "scripts/a01_runtime_benchmark.py",
    "schemas/leones-e2e-operation.v1.json",
    "schemas/leones-e2e-trace.v1.json",
    "schemas/leones-recommendation.v1.json",
    "schemas/leones-recommendation-output.v1.json",
)


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def main() -> int:
    print("LEONES — JALÓN 14 V1 PHYSICAL EXECUTION HANDOFF AUDIT")

    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        return fail("missing canonical handoff components: " + ", ".join(missing))
    print("PASS: canonical physical-execution components present")

    doc = (ROOT / "docs/jalones/jalon14.md").read_text(encoding="utf-8").lower()
    required_phrases = (
        "runtime-selection.v1",
        "run_a01_selected.py",
        "a01_runtime_benchmark.py",
        "no contiene",
        "ejecución física",
    )
    missing_phrases = [phrase for phrase in required_phrases if phrase not in doc]
    if missing_phrases:
        return fail("JALON 14 documentation is incomplete: " + ", ".join(missing_phrases))
    print("PASS: documentation explains the canonical handoff")

    forbidden = (
        "new selector",
        "nuevo selector",
        "benchmark alternativo",
        "segundo sistema de scoring",
        "segunda medición",
    )
    if any(term in doc for term in forbidden):
        # These phrases are allowed only as explicit rejection statements. The
        # contract document currently uses them to say what JALON 14 must not do.
        if "no contiene" not in doc:
            return fail("parallel decision/benchmark logic detected")
    print("PASS: no parallel decision/benchmark layer declared")

    print("JALON14_PHYSICAL_HANDOFF_CLOSE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
