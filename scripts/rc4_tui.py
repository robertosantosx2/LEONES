#!/usr/bin/env python3
"""LEONES RC4 retro TUI with visible install/uninstall activity."""
from __future__ import annotations

import curses
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "scripts" / "rc4_fitllm_recommend.py"
INV = ROOT / "scripts" / "rc4_component_inventory.py"
INS = ROOT / "install.sh"
UN = ROOT / "scripts" / "uninstall.sh"

# Make the repository root importable when this file is launched directly
# (``python3 scripts/rc4_tui.py``), not only as a module from the repo root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_selection.operation_progress import OperationPhase, OperationProgress, terminal_progress

PURPOSES = (("programming", "PROGRAMMING"), ("reasoning", "REASONING"), ("research", "RESEARCH"), ("chat", "CHAT"), ("multimodal", "MULTIMODAL"), ("embedding", "EMBEDDING"), ("general", "GENERAL"))


def inv() -> dict:
    try:
        return json.loads(subprocess.run([sys.executable, str(INV), "--json"], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout)
    except Exception:
        return {"components": [], "uninstall_offers": []}


def comp(inventory: dict, key: str) -> dict:
    return next((x for x in inventory.get("components", []) if x.get("component_id") == key), {})


def pctmem() -> int:
    try:
        data = {x.split(":", 1)[0]: int(x.split()[1]) for x in Path("/proc/meminfo").read_text().splitlines()}
        return round((data["MemTotal"] - data["MemAvailable"]) * 100 / data["MemTotal"])
    except Exception:
        return 0


def pctcpu() -> int:
    try:
        a = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        u1, n1, s1, i1 = map(int, a[:4])
        time.sleep(0.08)
        b = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        u2, n2, s2, i2 = map(int, b[:4])
        total = (u2 + n2 + s2 + i2) - (u1 + n1 + s1 + i1)
        idle = i2 - i1
        return round((total - idle) * 100 / total) if total else 0
    except Exception:
        return 0


def _run_operation(stdscr, argv: list[str], operation: str, phase: OperationPhase) -> int:
    """Run an install/uninstall command while keeping the TUI visibly active."""
    proc = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines: list[str] = []
    while True:
        rc = proc.poll()
        if proc.stdout is not None:
            line = proc.stdout.readline()
            if line:
                lines.append(line.rstrip())
                lines = lines[-5:]
        progress = OperationProgress(operation=operation, phase=phase, detail=lines[-1] if lines else None)
        stdscr.erase()
        stdscr.addstr(0, 0, "LEONES RC4 — OPERACIÓN")
        stdscr.addstr(2, 0, progress.render())
        for i, line in enumerate(lines, 4):
            stdscr.addnstr(i, 0, line, max(1, curses.COLS - 1))
        stdscr.refresh()
        if rc is not None:
            break
        time.sleep(0.08)
    result = terminal_progress(operation, success=(rc == 0))
    stdscr.addstr(11, 0, result.render())
    stdscr.refresh()
    time.sleep(0.8)
    return rc


def main() -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("LEONES RC4 TUI requiere un terminal interactivo")
        return 2

    def ui(stdscr):
        curses.curs_set(0)
        stdscr.clear()
        stdscr.addstr(0, 0, "LEONES RC4")
        stdscr.addstr(2, 0, "Estado de la máquina")
        stdscr.addstr(4, 0, f"RAM ocupada: {pctmem()}%")
        stdscr.addstr(5, 0, f"CPU:          {pctcpu()}%")
        stdscr.addstr(7, 0, "ESC / q: salir")
        stdscr.refresh()
        while True:
            key = stdscr.getch()
            if key in (27, ord("q"), ord("Q")):
                return 0
            if key in (ord("i"), ord("I")):
                return _run_operation(stdscr, [str(INS), "--dry-run"], "install", OperationPhase.PREPARING)
            if key in (ord("u"), ord("U")):
                return _run_operation(stdscr, [str(UN), "--dry-run", "--yes"], "uninstall", OperationPhase.REMOVING)

    return curses.wrapper(ui)


if __name__ == "__main__":
    raise SystemExit(main())
