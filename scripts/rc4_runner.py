#!/usr/bin/env python3
"""LEONES RC4 default runner.

Collects the mandatory multi-purpose user intent before any recommendation and
then delegates to the canonical RC4 FitLLM/LLMFit recommender. This runner is
proposal-only: it never authorizes execution or measurement.

The historical RC2 wizard remains available explicitly through ``--rc2``.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
RC2_WIZARD = ROOT / "scripts" / "rc2_wizard.py"

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
    print("\nLEONES RC4 — ¿para qué quieres usar la IA?")
    print("Selecciona uno o varios números separados por comas.\n")
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
        "--purpose",
        action="append",
        dest="purposes",
        help="non-interactive purpose; repeatable",
    )
    args = parser.parse_args(argv)

    if args.rc2:
        return subprocess.run(
            [sys.executable, str(RC2_WIZARD)],
            cwd=ROOT,
            check=False,
        ).returncode

    purposes = list(dict.fromkeys(args.purposes or choose_purposes()))
    command = [sys.executable, str(RECOMMENDER)]
    for purpose in purposes:
        command.extend(["--purpose", purpose])
    if args.json:
        command.append("--json")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
