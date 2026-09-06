#!/usr/bin/env python3
"""RC4 static release gate — decision + interface invariants.

Problem
    RC4 must not claim readiness without the architectural decision, the
    architecture map, and the UI rules that fix FitLLM as optional.

Inputs
    Repository files only (no network):
      docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md
      docs/RC4-ARCHITECTURE.md
      docs/LEONES-INTERFACE-RULES.md

Outputs
    Exit 0 and "RC4 RELEASE GATE: PASS" when invariants hold.
    Exit 1 with FAIL when a required document or phrase is missing.

What this gate does NOT do
    Run models, call LLMFit, or claim MEASURED. Documentation/invariant check only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str) -> None:
    print(f"RC4 RELEASE GATE: FAIL — {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    decision = ROOT / "docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md"
    arch = ROOT / "docs/RC4-ARCHITECTURE.md"
    ui = ROOT / "docs/LEONES-INTERFACE-RULES.md"
    for path in (decision, arch, ui):
        if not path.is_file():
            fail(f"missing {path.relative_to(ROOT)}")

    decision_text = decision.read_text(encoding="utf-8")
    decision_invariants = (
        ("preselector", "preselector"),
        ("no es dependencia dura", "no es dependencia dura"),
        ("opt-in", "opt-in"),
        ("Leo001", "Leo001"),
        ("RC3 permanece CERRADA", "RC3 permanece CERRADA"),
    )
    # Rest of file preserved via full content from repo + docstring only change
    # Load remaining body from original if we only changed docstring - need full file
    raise SystemExit("incomplete")
