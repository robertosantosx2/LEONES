#!/usr/bin/env python3
"""LEONES RC4 default runner.

Normative TUI contract: docs/TUI_RULES_RC4.md
Privilege authorization is rendered by the TUI bottom action panel; no modal
sudo dialog is allowed to replace or overlay the persistent three-panel frame.
"""
from __future__ import annotations
import argparse, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
RECOMMENDER=ROOT/"scripts/rc4_fitllm_recommend.py";RC2_WIZARD=ROOT/"scripts/rc2_wizard.py"
PURPOSES=(("programming","Programación / código"),("reasoning","Razonamiento"),("research","Investigación / análisis"),("chat","Chat / asistente"),("multimodal","Multimodal"),("embedding","Embeddings / búsqueda semántica"),("general","Uso general"))
def choose_purposes():
    print("\nLEONES RC4 · INTENCIÓN DE USO\nElige uno o varios números separados por comas.\n")
    for i,(_,label) in enumerate(PURPOSES,1):print(f"  [{i}] {label}")
    while True:
        try:idx=[int(x.strip()) for x in input("LEONES> ").split(",") if x.strip()]
        except ValueError:idx=[]
        out=[]
        for i in idx:
            if 1<=i<=len(PURPOSES) and PURPOSES[i-1][0] not in out:out.append(PURPOSES[i-1][0])
        if out:return out
        print("  ! Debes seleccionar al menos un propósito.")
def run_tui():
    from scripts import rc4_tui as tui
    # The TUI itself owns both acceptance and privilege states.  Keeping this
    # hook here preserves the runner as the single launcher without reintroducing
    # an external/modal privilege dialog.
    return tui.main()
def main(argv=None):
    p=argparse.ArgumentParser(description="LEONES RC4 default runner");p.add_argument("--rc2",action="store_true");p.add_argument("--json",action="store_true");p.add_argument("--inventory",action="store_true");p.add_argument("--purpose",action="append",dest="purposes");a=p.parse_args(argv)
    if a.inventory:return subprocess.run([sys.executable,str(ROOT/"scripts/rc4_component_inventory.py")],cwd=ROOT,check=False).returncode
    if a.rc2:return subprocess.run([sys.executable,str(RC2_WIZARD)],cwd=ROOT,check=False).returncode
    if a.purposes is None and not a.json and sys.stdin.isatty() and sys.stdout.isatty():return run_tui()
    ps=list(dict.fromkeys(a.purposes or choose_purposes()));cmd=[sys.executable,str(RECOMMENDER)];[cmd.extend(("--purpose",x)) for x in ps]
    if a.json:cmd.append("--json")
    return subprocess.run(cmd,cwd=ROOT,check=False).returncode
if __name__=="__main__":raise SystemExit(main())
