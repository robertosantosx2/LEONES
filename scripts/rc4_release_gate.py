#!/usr/bin/env python3
"""RC4 static release gate — decision + interface invariants."""
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
    for needle in (
        "recomendador",
        "no es dependencia dura",
        "opt-in",
        "Leo001",
        "RC3 permanece CERRADA",
    ):
        if needle not in decision_text:
            fail(f"decision missing invariant: {needle}")

    arch_text = arch.read_text(encoding="utf-8")
    if "FitLLM" not in arch_text or "ESTIMATED" not in arch_text:
        fail("architecture missing FitLLM/ESTIMATED")

    ui_text = ui.read_text(encoding="utf-8")
    for needle in ("es", "en", "zh", "ja", "desinstalar", "RAM en ejecución", "daemon"):
        if needle not in ui_text:
            fail(f"interface rules missing: {needle}")
    if "日本語" not in ui_text and "japonés" not in ui_text.lower():
        fail("interface rules must list Japanese")

    rec = ROOT / "scripts/rc4_fitllm_recommend.py"
    cost = ROOT / "scripts/rc4_component_cost.py"
    life = ROOT / "scripts/rc4_install_lifecycle.py"
    for path in (rec, cost, life):
        if not path.is_file():
            fail(f"missing implementation skeleton {path.relative_to(ROOT)}")

    rec_src = rec.read_text(encoding="utf-8")
    for inv in (
        'execution_authorized": False',
        'measurement_authorized": False',
        'measured": False',
        "fitllm_required_for_boot",
    ):
        if inv not in rec_src:
            fail(f"recommender missing invariant: {inv}")

    life_src = life.read_text(encoding="utf-8")
    for comp in ("fitllm", "hermes", "omh", "magnitude", "ods"):
        if comp not in life_src:
            fail(f"lifecycle missing component {comp}")

    print("RC4 RELEASE GATE: PASS")
    print("  decision + architecture + UI rules: PASS")
    print("  FitLLM recommender soft-dep invariants: PASS")
    print("  install/uninstall component set: PASS")
    print("  physical MEASURED: NOT CLAIMED")


if __name__ == "__main__":
    main()
