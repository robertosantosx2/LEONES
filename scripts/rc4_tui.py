#!/usr/bin/env python3
"""LEONES RC4 retro TUI.

Startup flow:
    language -> machine state -> optional maintenance -> TUI.

The TUI remains presentation-only for recommendation/execution boundaries.
"""
from __future__ import annotations

import curses
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
INVENTORY = ROOT / "scripts" / "rc4_component_inventory.py"

PURPOSES = (
    ("programming", "PROGRAMMING"),
    ("reasoning", "REASONING"),
    ("research", "RESEARCH"),
    ("chat", "CHAT"),
    ("multimodal", "MULTIMODAL"),
    ("embedding", "EMBEDDING"),
    ("general", "GENERAL"),
)


def memory_stats() -> tuple[int, int, int]:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0])
        total = values["MemTotal"]
        available = values["MemAvailable"]
        used = total - available
        return used, total, round(used * 100 / total)
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return 0, 0, 0


def memory_percent() -> int:
    return memory_stats()[2]


def cpu_percent() -> int:
    try:
        load = os.getloadavg()[0]
        cpus = os.cpu_count() or 1
        return min(100, round(load * 100 / cpus))
    except OSError:
        return 0


def disk_stats() -> tuple[int, int, int]:
    try:
        usage = shutil.disk_usage(ROOT)
        return usage.used, usage.total, round(usage.used * 100 / usage.total)
    except OSError:
        return 0, 0, 0


def human_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def machine_hardware() -> list[str]:
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    cores = os.cpu_count() or 1
    gpu = "not detected"
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, check=False, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                gpu = out.stdout.strip().replace("\n", "; ")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return [f"CPU     {cpu} ({cores} logical CPUs)", f"GPU     {gpu}"]


def load_inventory() -> dict:
    try:
        completed = subprocess.run([sys.executable, str(INVENTORY), "--json"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=20)
        return json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"components": []}


def agent_names() -> list[str]:
    candidates = [ROOT / "agents", ROOT / ".leones" / "agents"]
    names: list[str] = []
    for directory in candidates:
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if child.name.startswith("."):
                    continue
                if child.is_dir() or child.suffix in {".py", ".sh", ".json", ".yaml", ".yml"}:
                    names.append(child.stem if child.is_file() else child.name)
    return list(dict.fromkeys(names))


def add_box(stdscr, y: int, x: int, h: int, w: int, title: str) -> None:
    if h < 3 or w < 4:
        return
    stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
    for row in range(y + 1, y + h - 1):
        stdscr.addstr(row, x, "|")
        stdscr.addstr(row, x + w - 1, "|")
    stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
    label = "[ " + title + " ]"
    if len(label) < w - 4:
        stdscr.addstr(y, x + 2, label)


def put(stdscr, y: int, x: int, text: str, width: int) -> None:
    if width > 0 and 0 <= y < stdscr.getmaxyx()[0]:
        try:
            stdscr.addstr(y, x, text[:width])
        except curses.error:
            pass


def wait_key(stdscr: "curses._CursesWindow") -> int:
    stdscr.refresh()
    return stdscr.getch()


def language_screen(stdscr: "curses._CursesWindow") -> str:
    focus = 0
    languages = (("es", "Español"), ("en", "English"))
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        box_w = min(70, max(40, w - 4))
        x = max(1, (w - box_w) // 2)
        add_box(stdscr, 3, x, 12, box_w, "LEONES RC4")
        put(stdscr, 5, x + 4, "SELECT LANGUAGE / SELECCIONA IDIOMA", box_w - 8)
        for i, (_, label) in enumerate(languages):
            put(stdscr, 8 + i, x + 8, f"{'>' if i == focus else ' '} [{i + 1}] {label}", box_w - 16)
        put(stdscr, 12, x + 4, "UP/DOWN · ENTER", box_w - 8)
        key = wait_key(stdscr)
        if key in (curses.KEY_UP, ord("k")):
            focus = (focus - 1) % len(languages)
        elif key in (curses.KEY_DOWN, ord("j")):
            focus = (focus + 1) % len(languages)
        elif key in (10, 13, ord("1"), ord("2")):
            if key in (ord("1"), ord("2")):
                focus = int(chr(key)) - 1
            return languages[focus][0]


def machine_state_screen(stdscr: "curses._CursesWindow", language: str) -> None:
    inv = load_inventory()
    used, total, mem_pct = memory_stats()
    disk_used, disk_total, disk_pct = disk_stats()
    agents = agent_names()
    components = inv.get("components", [])
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 25 or w < 92:
            put(stdscr, 1, 2, "LEONES RC4 -- terminal demasiado pequena (min 92x25)", w - 4)
            put(stdscr, 3, 2, "Redimensiona la ventana. Q: salir", w - 4)
            if wait_key(stdscr) in (ord("q"), ord("Q")):
                raise SystemExit(0)
            continue
        put(stdscr, 0, max(2, (w - 34) // 2), "LEONES // MACHINE STATE", 34)
        add_box(stdscr, 1, 1, h - 4, w - 2, "ESTADO DE LA MÁQUINA")
        x = 4
        put(stdscr, 3, x, "HARDWARE", w - 8)
        for i, line in enumerate(machine_hardware()):
            put(stdscr, 4 + i, x, line, w - 8)
        put(stdscr, 7, x, "RECURSOS EN USO", w - 8)
        put(stdscr, 8, x, f"RAM     {human_bytes(used)} / {human_bytes(total)}   [{mem_pct:>3}%]", w - 8)
        put(stdscr, 9, x, f"CPU     {cpu_percent():>3}%", w - 8)
        put(stdscr, 10, x, f"DISCO   {human_bytes(disk_used)} / {human_bytes(disk_total)}   [{disk_pct:>3}%]", w - 8)
        put(stdscr, 12, x, "SOFTWARE IA INSTALADO", w - 8)
        row = 13
        for c in components:
            if not c.get("installed"):
                continue
            detail = ""
            if c.get("models"):
                detail = " :: " + ", ".join(c["models"])
            put(stdscr, row, x, f"● {c['display_name']}{detail}", w - 8)
            row += 1
        agent_detail = ", ".join(agents) if agents else "ninguno detectado"
        put(stdscr, row, x, f"● Agentes ({len(agents)}) :: {agent_detail}", w - 8)
        row += 2
        put(stdscr, row, x, "[ENTER] continuar   [M] mantenimiento   [Q] salir", w - 8)
        key = wait_key(stdscr)
        if key in (ord("q"), ord("Q")):
            raise SystemExit(0)
        if key in (10, 13):
            return
        if key in (ord("m"), ord("M")):
            maintenance_screen(stdscr, inv, language)


def maintenance_screen(stdscr: "curses._CursesWindow", inv: dict, language: str) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    add_box(stdscr, 2, 2, min(h - 5, 30), w - 4, "MANTENIMIENTO")
    x = 5
    row = 4
    put(stdscr, row, x, "ACTUALIZAR / DESINSTALAR", w - 10)
    row += 2
    for c in inv.get("components", []):
        if c.get("installed"):
            suffix = " [desinstalable]" if c.get("uninstallable") else " [runtime/protegido]"
            put(stdscr, row, x, f"{c['display_name']}{suffix}", w - 10)
            row += 1
    row += 1
    put(stdscr, row, x, "LEONES calcula el inventario antes de cualquier cambio.", w - 10)
    put(stdscr, row + 1, x, "La acción destructiva sigue siendo opt-in y requiere confirmación.", w - 10)
    put(stdscr, row + 3, x, "[ENTER] volver", w - 10)
    wait_key(stdscr)


def run_recommendation(purposes: list[str]) -> tuple[str, dict | None]:
    command = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes:
        command.extend(["--purpose", purpose])
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        data = json.loads(completed.stdout)
        return data.get("status", "error"), data
    except (OSError, json.JSONDecodeError) as exc:
        return "error", {"message": str(exc)}


def draw(stdscr, selected: set[str], status: str, result: dict | None, focus: int) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    if height < 25 or width < 92:
        put(stdscr, 1, 2, "LEONES RC4 TUI -- terminal demasiado pequena (min 92x25)", width - 4)
        put(stdscr, 3, 2, "Redimensiona la ventana.  Q: salir", width - 4)
        stdscr.refresh()
        return
    put(stdscr, 0, max(2, (width - 46) // 2), "LEONES // AI OPERATING SYSTEM v4", 46)
    left_w = 27
    right_x = left_w + 3
    right_w = width - right_x - 2
    top_h = 7
    bottom_y = top_h + 2
    main_h = height - bottom_y - 2
    add_box(stdscr, 1, 1, height - 3, left_w, "NAVIGATION")
    put(stdscr, 3, 4, "[X] LEONES RC4", left_w - 6)
    put(stdscr, 4, 6, "-> Dashboard", left_w - 8)
    put(stdscr, 5, 6, "-> Machine State", left_w - 8)
    put(stdscr, 6, 6, "-> Intent", left_w - 8)
    put(stdscr, 7, 6, "-> Recommender", left_w - 8)
    put(stdscr, 8, 6, "-> Evidence", left_w - 8)
    put(stdscr, 10, 4, "[ ] RC2 legacy", left_w - 6)
    put(stdscr, 12, 4, "[ ] Settings", left_w - 6)
    put(stdscr, 14, 4, "[ ] Exit", left_w - 6)
    add_box(stdscr, 1, right_x, top_h, right_w, "SYSTEM STATUS")
    put(stdscr, 3, right_x + 3, f"CPU: {cpu_percent():>3}%   MEM: {memory_percent():>3}%   NETWORK: UP", right_w - 6)
    put(stdscr, 4, right_x + 3, "RUNTIME: llama.cpp / local measurement boundary", right_w - 6)
    put(stdscr, 5, right_x + 3, "EVIDENCE: HF + Artificial Analysis / ESTIMATED", right_w - 6)
    add_box(stdscr, bottom_y, right_x, main_h, right_w, "RC4 WORKSPACE")
    inner_x = right_x + 3
    content_w = right_w - 6
    put(stdscr, bottom_y + 2, inner_x, "USER INTENT[]  --  MULTI SELECT  --  REQUIRED", content_w)
    put(stdscr, bottom_y + 3, inner_x, "Select purposes, then press ENTER to recommend.", content_w)
    for idx, (key, label) in enumerate(PURPOSES):
        mark = "X" if key in selected else " "
        prefix = ">" if idx == focus else " "
        put(stdscr, bottom_y + 5 + idx, inner_x, f"{prefix} [{mark}] {idx + 1}. {label}", content_w)
    status_y = bottom_y + 5 + len(PURPOSES) + 1
    if status == "running":
        put(stdscr, status_y, inner_x, "JOB: #RC4 -- querying evidence + LLMFit ...", content_w)
    elif result:
        put(stdscr, status_y, inner_x, f"JOB: #RC4 -- {status.upper()}", content_w)
        rows = result.get("recommendations") or []
        for n, row in enumerate(rows[:3], 1):
            put(stdscr, status_y + n, inner_x, f"[{n}] {row.get('model_id', '?')}  ::  ESTIMATED", content_w)
        if not rows:
            put(stdscr, status_y + 1, inner_x, result.get("message", "No candidates"), content_w)
    footer = "SPACE select  UP/DOWN move  ENTER recommend  R rerun  Q quit"
    put(stdscr, height - 1, 2, footer, width - 4)
    stdscr.refresh()


def main() -> int:
    selected: set[str] = set()
    focus = 0
    status = "ready"
    result: dict | None = None

    def app(stdscr: "curses._CursesWindow") -> None:
        nonlocal focus, status, result
        curses.curs_set(0)
        stdscr.keypad(True)
        language = language_screen(stdscr)
        machine_state_screen(stdscr, language)
        while True:
            draw(stdscr, selected, status, result, focus)
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                return
            if key in (curses.KEY_UP, ord("k")):
                focus = (focus - 1) % len(PURPOSES)
            elif key in (curses.KEY_DOWN, ord("j")):
                focus = (focus + 1) % len(PURPOSES)
            elif key in (ord(" "),):
                key_name = PURPOSES[focus][0]
                if key_name in selected:
                    selected.remove(key_name)
                else:
                    selected.add(key_name)
            elif key in (ord("r"), ord("R"), 10, 13):
                if not selected:
                    status = "insufficient"
                    result = {"message": "Selecciona al menos un proposito antes de recomendar."}
                    continue
                status = "running"
                draw(stdscr, selected, status, None, focus)
                status, result = run_recommendation([p for p, _ in PURPOSES if p in selected])

    curses.wrapper(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
