#!/usr/bin/env python3
"""LEONES RC4 retro TUI.

A dependency-free curses interface inspired by classic ASCII operating
consoles. The TUI is presentation only: recommendation remains delegated to
the canonical RC4 recommender and its ESTIMATED/MEASURED boundary.
"""
from __future__ import annotations

import curses
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"

PURPOSES = (
    ("programming", "PROGRAMMING"),
    ("reasoning", "REASONING"),
    ("research", "RESEARCH"),
    ("chat", "CHAT"),
    ("multimodal", "MULTIMODAL"),
    ("embedding", "EMBEDDING"),
    ("general", "GENERAL"),
)


def memory_percent() -> int:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0])
        total = values["MemTotal"]
        available = values["MemAvailable"]
        return round((total - available) * 100 / total)
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return 0


def cpu_percent() -> int:
    try:
        load = os.getloadavg()[0]
        cpus = os.cpu_count() or 1
        return min(100, round(load * 100 / cpus))
    except OSError:
        return 0


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
    if width <= 0:
        return
    stdscr.addstr(y, x, text[:width])


def run_recommendation(purposes: list[str]) -> tuple[str, dict | None]:
    command = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes:
        command.extend(["--purpose", purpose])
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False
        )
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
    put(stdscr, 5, 6, "-> Intent", left_w - 8)
    put(stdscr, 6, 6, "-> Recommender", left_w - 8)
    put(stdscr, 7, 6, "-> Evidence", left_w - 8)
    put(stdscr, 9, 4, "[ ] RC2 legacy", left_w - 6)
    put(stdscr, 11, 4, "[ ] Settings", left_w - 6)
    put(stdscr, 13, 4, "[ ] Exit", left_w - 6)

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
