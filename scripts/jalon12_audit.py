#!/usr/bin/env python3
"""Strict audit for the first human-facing LEONES V1 entry point.

The audit is intentionally simple: it checks that the user launcher and
preflight contract exist, that the front door delegates to the existing
canonical contracts, and that no benchmark or recommendation engine has been
quietly introduced here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/run_leones_v1.sh"
ENTRYPOINT = ROOT / "scripts/leones_v1.py"
SCHEMA = ROOT / "schemas/leones-v1-preflight.v1.json"
DOC = ROOT / "docs/V1-USER-GUIDE.md"

FORBIDDEN_CODE_PATTERNS = (
    r'^[ \t]*["\']tokens_per_second["\']\s*:',
    r'^[ \t]*["\']estimated_tps["\']\s*:',
    r'^[ \t]*["\']ranking_score["\']\s*:',
)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def main() -> int:
    print("LEONES — JALÓN 12 V1 USER ENTRYPOINT AUDIT")
    for path in (LAUNCHER, ENTRYPOINT, SCHEMA, DOC):
        if not path.is_file():
            fail(f"missing V1 component: {path.relative_to(ROOT)}")
    print("PASS: canonical V1 entrypoint components present")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if schema.get("$id") != "https://leones.local/schemas/leones-v1-preflight.v1.json":
        fail("unexpected preflight schema identity")
    if schema["properties"]["schema"].get("const") != "leones-v1-preflight.v1":
        fail("preflight schema does not fix its schema identifier")
    print("PASS: preflight contract is fixed")

    launcher = LAUNCHER.read_text(encoding="utf-8")
    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
    if "scripts/leones_v1.py preflight --pretty" not in launcher:
        fail("launcher does not delegate to canonical V1 entrypoint")
    if 'choices=("preflight",)' not in entrypoint:
        fail("V1 entrypoint exposes an unexpected operation")
    print("PASS: launcher delegates to the canonical preflight")

    # The explanatory documentation may mention forbidden concepts. The
    # invariant therefore inspects executable dictionary fields, not prose.
    for pattern in FORBIDDEN_CODE_PATTERNS:
        if re.search(pattern, entrypoint, flags=re.MULTILINE):
            fail("parallel scoring/measurement field found in V1 front door")
    print("PASS: no parallel benchmark/scoring engine introduced")

    documentation = DOC.read_text(encoding="utf-8")
    required_phrases = (
        "## Primer uso",
        "## Qué hace el primer comando",
        "## Cuándo hace falta la máquina física",
        "## Principio -strict-",
    )
    for phrase in required_phrases:
        if phrase not in documentation:
            fail(f"user documentation missing section: {phrase}")
    print("PASS: user-facing documentation explains how to use the entrypoint")

    print("JALON12_V1_ENTRYPOINT_CLOSE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
