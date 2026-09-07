#!/usr/bin/env python3
"""LEONES RC4 default runner (also wired from ./leones).

The normal terminal path opens the dependency-free retro ASCII TUI. The TUI
collects mandatory multi-purpose USER_INTENT[] and delegates recommendation
to the canonical RC4 recommender. Non-interactive flags remain available for
CI, capture and automation.

What this runner does NOT do:
    Authorize execution or measurement. Install stacks. Treat FitLLM as a hard
    boot dependency. Hermes/OMH are not consulted for model selection.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
RC2_WIZARD = ROOT / "scripts" / "rc2_wizard.py"
TUI = ROOT / "scripts" / "rc4_tui.py"

PURPOSES = (
    ("programming", "Programación / código"),
    ("reasoning", "Razonamiento"),
    ("research", "Investigación / análisis"),
    ("chat", "Chat / asistente"),
    ("multimodal", "Multimodal"),
    ("embedding", "Embeddings / búsqueda semántica"),
    ("general", "Uso general"),
)


def choose_purposes() -> list[str]:
    """Keep a plain-input fallback for pipes and non-TTY environments."""
    print(
        """
LEONES RC4 · INTENCIÓN DE USO
Elige uno o varios números separados por comas.
Sin intención no hay recomendación.
"""
    )
    for index, (_, label) in enumerate(PURPOSES, 1):
        print(f"  [{index}] {label}")
    while True:
        answer = input("LEONES> ").strip()
        selected: list[str] = []
        try:
            indexes = [int(x.strip()) for x in answer.split(",") if x.strip()]
        except ValueError:
            indexes = []
        for index in indexes:
            if 1 <= index <= len(PURPOSES):
                purpose = PURPOSES[index - 1][0]
                if purpose not in selected:
                    selected.append(purpose)
        if selected:
            return selected
        print("  ! Debes seleccionar al menos un propósito.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEONES RC4 default runner")
    parser.add_argument("--rc2", action="store_true", help="run the historical RC2 wizard")
    parser.add_argument("--json", action="store_true", help="emit recommender JSON")
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="show component inventory and uninstall offers, then exit",
    )
    parser.add_argument(
        "--purpose",
        action="append",
        dest="purposes",
        help="non-interactive purpose; repeatable",
    )
    args = parser.parse_args(argv)

    if args.inventory:
        inv = ROOT / "scripts" / "rc4_component_inventory.py"
        return subprocess.run([sys.executable, str(inv)], cwd=ROOT, check=False).returncode

    if args.rc2:
        return subprocess.run(
            [sys.executable, str(RC2_WIZARD)],
            cwd=ROOT,
            check=False,
        ).returncode

    # A real terminal gets the RC4 TUI. Explicit purposes keep automation
    # deterministic and bypass presentation entirely.
    if args.purposes is None and not args.json and sys.stdin.isatty() and sys.stdout.isatty():
        return subprocess.run([sys.executable, str(TUI)], cwd=ROOT, check=False).returncode

    purposes = list(dict.fromkeys(args.purposes or choose_purposes()))
    command = [sys.executable, str(RECOMMENDER)]
    for purpose in purposes:
        command.extend(["--purpose", purpose])
    if args.json:
        command.append("--json")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
