#!/usr/bin/env python3
"""RC4 human-choice flow: purposes -> models -> solution -> costs -> consent.

This TUI informs and calculates. It never installs anything. Model choice is
uncapped; installation remains unauthorized until an explicit confirmation.
"""
from __future__ import annotations

import curses
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
CATALOG = ROOT / "catalogs" / "rc4_solutions.json"
PURPOSES = (("programming", "PROGRAMMING"), ("reasoning", "REASONING"), ("research", "RESEARCH"), ("chat", "CHAT"), ("multimodal", "MULTIMODAL"), ("embedding", "EMBEDDING"), ("general", "GENERAL"))
SOLUTIONS = (("personal_assistant", "PERSONAL AI ASSISTANT"), ("soho", "FULL SOHO"), ("both", "BOTH"))


def human_bytes(value: int | None) -> str:
    if value is None: return "UNKNOWN"
    n = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB": return f"{n:.1f} {unit}"
        n /= 1024
    return "UNKNOWN"


def disk_free() -> int | None:
    try: return shutil.disk_usage(ROOT).free
    except OSError: return None


def run_recommendation(purposes: list[str]) -> dict:
    cmd = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes: cmd += ["--purpose", purpose]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False, timeout=90)
        return json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"status": "unavailable", "recommendations": [], "message": "Recommendation unavailable."}


def model_cost(row: dict) -> tuple[int | None, dict]:
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    candidates = (raw.get("size_bytes"), raw.get("disk_bytes"), raw.get("size"), raw.get("disk_size_bytes"))
    size = next((v for v in candidates if isinstance(v, int) and v >= 0), None)
    return size, {"artifact_bytes": size, "runtime_dependencies": None, "data": None, "margin": None, "state": "ESTIMATED" if size is not None else "UNKNOWN"}


def aggregate(selected: list[dict], solution: str) -> tuple[int | None, list[dict]]:
    details = []
    known = True; total = 0
    for row in selected:
        size, detail = model_cost(row); details.append(detail)
        if size is None: known = False
        else: total += size
    try: catalog = json.loads(CATALOG.read_text())
    except (OSError, json.JSONDecodeError): catalog = {"solutions": {}}
    keys = ["personal_assistant", "soho"] if solution == "both" else [solution]
    shared = 0
    for key in keys:
        value = catalog.get("solutions", {}).get(key, {}).get("disk_bytes")
        if not isinstance(value, int): known = False
        else: total += value
    return (total if known else None), details


def draw(stdscr, phase: int, purposes: list[str], models: list[dict], selected: set[int], solution: str, gate: str, language: str = "es"):
    stdscr.erase(); h, w = stdscr.getmaxyx();
    if h < 25 or w < 92:
        stdscr.addstr(1, 2, "LEONES RC4 -- terminal demasiado pequeña")
        stdscr.addstr(3, 2, "mínimo 92x25"); stdscr.refresh(); return
    title = "LEONES // AI OPERATING SYSTEM v4"
    stdscr.addstr(0, max(2, (w-len(title))//2), title)
    stdscr.addstr(2, 3, "+" + "-"*(w-8) + "+")
    labels = ["1 PROPÓSITOS", "2 MODELOS", "3 SOLUCIÓN", "4 COSTES", "5 CONFIRMACIÓN"]
    stdscr.addstr(3, 5, "  ".join((">" if i == phase else " ") + x for i,x in enumerate(labels)))
    stdscr.addstr(5, 4, "USUARIO DECIDE · LEONES INFORMA / CALCULA · SIN INSTALACIÓN AUTOMÁTICA")
    row = 7
    if phase == 0:
        stdscr.addstr(row, 4, "Selecciona uno o varios propósitos:"); row += 2
        for i, (_, name) in enumerate(PURPOSES): stdscr.addstr(row+i, 6, ("[x] " if PURPOSES[i][0] in purposes else "[ ] ") + name)
        stdscr.addstr(row+len(PURPOSES)+2, 4, "↑/↓ mover · ESPACIO seleccionar · ENTER continuar")
    elif phase == 1:
        stdscr.addstr(row, 4, "Modelos compatibles / recomendados. Selección múltiple, sin límite artificial:"); row += 2
        if not models: stdscr.addstr(row, 6, "Sin candidatos disponibles; puedes volver y cambiar propósitos.")
        for i, m in enumerate(models):
            mark = "[x]" if i in selected else "[ ]"; size, _ = model_cost(m)
            stdscr.addstr(row+i, 6, f"{mark} {i+1:>2} {str(m.get('model_id','?'))[:48]}  DISCO={human_bytes(size)}  ESTIMATED")
        stdscr.addstr(row+max(8,len(models))+1, 4, "↑/↓ mover · ESPACIO seleccionar · ENTER continuar · R recalcular")
    elif phase == 2:
        stdscr.addstr(row, 4, "¿Qué quieres instalar?"); row += 2
        for i, (_, name) in enumerate(SOLUTIONS): stdscr.addstr(row+i, 6, ("> " if ((solution == SOLUTIONS[i][0])) else "  ") + name)
        stdscr.addstr(row+5, 4, "↑/↓ elegir · ENTER continuar")
    elif phase == 3:
        required, _ = aggregate([models[i] for i in sorted(selected)], solution)
        free = disk_free(); status = gate if required is None or free is None else ("SUFICIENTE" if free >= required else "INSUFICIENTE")
        stdscr.addstr(row, 4, "COSTE DE LA SELECCIÓN"); row += 2
        for i in sorted(selected):
            size, _ = model_cost(models[i]); stdscr.addstr(row, 6, f"{models[i].get('model_id','?')}: artefacto {human_bytes(size)}  [ESTIMATED/UNKNOWN]"); row += 1
        stdscr.addstr(row+1, 4, f"MODELOS + SOLUCIÓN: {human_bytes(required)}"); row += 2
        stdscr.addstr(row, 4, f"DISCO LIBRE ACTUAL: {human_bytes(free)}"); row += 1
        stdscr.addstr(row, 4, f"GATE DISCO: {status}  ·  instalación autorizada: NO"); row += 2
        stdscr.addstr(row, 4, "Nota: UNKNOWN no pasa el gate. No se instala parcialmente por defecto.")
        stdscr.addstr(row+2, 4, "ENTER continuar · B volver")
    else:
        required, _ = aggregate([models[i] for i in sorted(selected)], solution); free = disk_free()
        status = "SUFICIENTE" if required is not None and free is not None and free >= required else ("UNKNOWN" if required is None or free is None else "INSUFICIENTE")
        stdscr.addstr(row, 4, "CONFIRMACIÓN EXPLÍCITA"); row += 2
        stdscr.addstr(row, 6, f"Propósitos: {', '.join(purposes)}"); row += 1
        stdscr.addstr(row, 6, f"Modelos: {len(selected)} seleccionado(s), sin límite artificial"); row += 1
        stdscr.addstr(row, 6, f"Solución: {solution.upper()}"); row += 1
        stdscr.addstr(row, 6, f"Disco: {status} · requerido={human_bytes(required)} · libre={human_bytes(free)}"); row += 2
        stdscr.addstr(row, 6, "[ENTER] CONFIRMAR INSTALACIÓN  ·  [B] volver  ·  [Q] salir"); row += 2
        stdscr.addstr(row, 6, "La confirmación aún NO ejecuta aquí: esta capa registra consentimiento y delega al instalador autorizado.")
    stdscr.addstr(h-2, 3, "TAB navegación · B volver · Q salir")
    stdscr.refresh()


def main() -> int:
    def app(stdscr):
        curses.curs_set(0); stdscr.keypad(True); phase=0; purposes=[]; models=[]; selected=set(); solution="personal_assistant"; cursor=0; gate="UNKNOWN"
        while True:
            draw(stdscr, phase, purposes, models, selected, solution, gate)
            key=stdscr.getch()
            if key in (ord('q'),ord('Q')): return
            if phase==0:
                if key in (curses.KEY_UP,ord('k')): cursor=(cursor-1)%len(PURPOSES)
                elif key in (curses.KEY_DOWN,ord('j')): cursor=(cursor+1)%len(PURPOSES)
                elif key==ord(' '):
                    p=PURPOSES[cursor][0]; purposes.remove(p) if p in purposes else purposes.append(p)
                elif key in (10,13) and purposes:
                    result=run_recommendation(purposes); models=result.get('recommendations') or []; selected=set(); cursor=0; phase=1
            elif phase==1:
                if models:
                    if key in (curses.KEY_UP,ord('k')): cursor=(cursor-1)%len(models)
                    elif key in (curses.KEY_DOWN,ord('j')): cursor=(cursor+1)%len(models)
                    elif key==ord(' '): selected.remove(cursor) if cursor in selected else selected.add(cursor)
                    elif key in (ord('r'),ord('R')): models=run_recommendation(purposes).get('recommendations') or []; selected=set(); cursor=0
                    elif key in (10,13) and selected: phase=2; cursor=0
                elif key in (ord('b'),ord('B')): phase=0; cursor=0
            elif phase==2:
                if key in (curses.KEY_UP,ord('k'),curses.KEY_DOWN,ord('j')): solution=SOLUTIONS[(SOLUTIONS.index((solution,next(n for k,n in SOLUTIONS if k==solution))) + (1 if key in (curses.KEY_DOWN,ord('j')) else -1)) % 3][0]
                elif key in (10,13): phase=3
                elif key in (ord('b'),ord('B')): phase=1
            elif phase==3:
                if key in (ord('b'),ord('B')): phase=2
                elif key in (10,13): phase=4
            else:
                if key in (ord('b'),ord('B')): phase=3
                elif key in (10,13):
                    # Deliberately no installer call in this milestone.
                    phase=4
    curses.wrapper(app); return 0

if __name__ == '__main__': raise SystemExit(main())
