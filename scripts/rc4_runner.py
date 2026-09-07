#!/usr/bin/env python3
"""LEONES RC4 default runner.

The interactive path opens the full human-choice TUI. Recommendation, choice,
consent, installation, verification and measurement remain separate phases.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
RC2_WIZARD = ROOT / "scripts" / "rc2_wizard.py"
TUI = ROOT / "scripts" / "rc4_choice_flow_tui.py"
PURPOSES = (("programming", "Programación / código"), ("reasoning", "Razonamiento"), ("research", "Investigación / análisis"), ("chat", "Chat / asistente"), ("multimodal", "Multimodal"), ("embedding", "Embeddings / búsqueda semántica"), ("general", "Uso general"))

def choose_purposes() -> list[str]:
    print("\nLEONES RC4 · INTENCIÓN DE USO\nElige uno o varios números separados por comas.\nSin intención no hay recomendación.\n")
    for index, (_, label) in enumerate(PURPOSES, 1): print(f"  [{index}] {label}")
    while True:
        answer = input("LEONES> ").strip(); selected=[]
        try: indexes=[int(x.strip()) for x in answer.split(",") if x.strip()]
        except ValueError: indexes=[]
        for index in indexes:
            if 1 <= index <= len(PURPOSES) and PURPOSES[index-1][0] not in selected: selected.append(PURPOSES[index-1][0])
        if selected: return selected
        print("  ! Debes seleccionar al menos un propósito.")

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="LEONES RC4 default runner")
    parser.add_argument("--rc2", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--purpose", action="append", dest="purposes")
    args=parser.parse_args(argv)
    if args.inventory:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "rc4_component_inventory.py")], cwd=ROOT, check=False).returncode
    if args.rc2:
        return subprocess.run([sys.executable, str(RC2_WIZARD)], cwd=ROOT, check=False).returncode
    if args.purposes is None and not args.json and sys.stdin.isatty() and sys.stdout.isatty():
        return subprocess.run([sys.executable, str(TUI)], cwd=ROOT, check=False).returncode
    purposes=list(dict.fromkeys(args.purposes or choose_purposes()))
    command=[sys.executable, str(RECOMMENDER)]
    for purpose in purposes: command.extend(["--purpose", purpose])
    if args.json: command.append("--json")
    return subprocess.run(command, cwd=ROOT, check=False).returncode

if __name__ == "__main__": raise SystemExit(main())
