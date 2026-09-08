#!/usr/bin/env python3
"""LEONES RC4 default runner (also wired from ./leones).

The normal terminal path opens the dependency-free retro ASCII TUI. Privileged
software installation/uninstallation is authorized from inside the TUI so
sudo never steals the curses terminal for an external password prompt.
"""
from __future__ import annotations

import argparse
import curses
import os
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


def _put(scr, y: int, x: int, text: str, width: int) -> None:
    try:
        if width > 0 and 0 <= y < scr.getmaxyx()[0]:
            scr.addnstr(y, max(0, x), str(text), width)
    except curses.error:
        pass


def _box(scr, y: int, x: int, h: int, w: int, title: str = "") -> None:
    try:
        scr.addstr(y, x, "+" + "-" * (w - 2) + "+")
        for row in range(y + 1, y + h - 1):
            scr.addstr(row, x, "|")
            scr.addstr(row, x + w - 1, "|")
        scr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
        if title:
            scr.addstr(y, x + 2, f"[ {title} ]")
    except curses.error:
        pass


def _sudo_cached() -> bool:
    if os.geteuid() == 0:
        return True
    if not shutil_which("sudo"):
        return False
    return subprocess.run(["sudo", "-n", "-v"], stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          check=False).returncode == 0


def shutil_which(command: str) -> str | None:
    import shutil
    return shutil.which(command)


def _privilege_box(scr, lang: str, operation: str) -> bool:
    """Authorize sudo without allowing a sudo prompt to escape the TUI."""
    if _sudo_cached():
        return True
    if not shutil_which("sudo"):
        return True

    h, w = scr.getmaxyx()
    bw = min(96, max(60, w - 6))
    bh = 9
    x = max(2, (w - bw) // 2)
    y = max(4, h // 2 - bh // 2)
    title = "AUTORIZACIÓN DEL SISTEMA" if lang == "es" else "SYSTEM AUTHORIZATION"
    action = "instalación" if operation == "install" else "desinstalación"
    question = (
        f"{action.capitalize()} requiere privilegios de administrador."
        if lang == "es" else
        f"{operation.capitalize()} requires administrator privileges."
    )
    _box(scr, y, x, bh, bw, title)
    _put(scr, y + 2, x + 3, question, bw - 6)
    _put(scr, y + 4, x + 3, "[Y] Autorizar    [N/ESC] Cancelar" if lang == "es"
         else "[Y] Authorize    [N/ESC] Cancel", bw - 6)
    scr.refresh()
    while True:
        key = scr.getch()
        if key in (ord("n"), ord("N"), 27):
            return False
        if key not in (ord("y"), ord("Y")):
            continue
        break

    # The password prompt is rendered by the TUI, never by sudo itself.
    _box(scr, y, x, bh, bw, title)
    _put(scr, y + 2, x + 3,
         "Contraseña de sudo:" if lang == "es" else "sudo password:", bw - 6)
    _put(scr, y + 4, x + 3,
         "(entrada oculta; ENTER confirma)" if lang == "es"
         else "(hidden input; ENTER confirms)", bw - 6)
    try:
        curses.echo(False)
        curses.curs_set(1)
        password = ""
        while True:
            key = scr.getch()
            if key in (10, 13):
                break
            if key in (27,):
                curses.echo(True)
                return False
            if key in (curses.KEY_BACKSPACE, 127, 8):
                password = password[:-1]
            elif 32 <= key <= 126:
                password += chr(key)
            _put(scr, y + 5, x + 3, "*" * len(password), bw - 6)
            scr.refresh()
    finally:
        curses.echo(True)

    proc = subprocess.run(
        ["sudo", "-S", "-v"],
        input=password + "\n",
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    password = ""
    _box(scr, y, x, bh, bw, title)
    if proc.returncode == 0:
        _put(scr, y + 2, x + 3,
             "Privilegios autorizados. La operación continúa en segundo plano."
             if lang == "es" else
             "Privileges authorized. The operation continues in background.", bw - 6)
        _put(scr, y + 4, x + 3, "ENTER continuar", bw - 6)
        scr.refresh()
        while scr.getch() not in (10, 13):
            pass
        return True
    _put(scr, y + 2, x + 3,
         "No se pudo autorizar sudo. Operación cancelada." if lang == "es"
         else "sudo authorization failed. Operation cancelled.", bw - 6)
    _put(scr, y + 4, x + 3, "ENTER volver", bw - 6)
    scr.refresh()
    while scr.getch() not in (10, 13, 27):
        pass
    return False


def run_tui() -> int:
    """Run the TUI and bridge privileged actions into its confirmation UI."""
    from scripts import rc4_tui as tui

    # The TUI's existing Y/N confirmation remains the first authorization gate.
    # After it succeeds, these wrappers perform the system-privilege handshake
    # before the background task is launched, while the curses screen is active.
    original_start_software = tui.TaskManager.start_software
    original_start_uninstall = tui.TaskManager.start_uninstall
    screen_ref = {"scr": None, "lang": "es"}

    original_confirm = tui.confirm

    def confirm_bridge(scr, lang, title, question):
        screen_ref["scr"] = scr
        screen_ref["lang"] = lang
        return original_confirm(scr, lang, title, question)

    def start_software_bridge(self, components):
        scr = screen_ref.get("scr")
        lang = screen_ref.get("lang", "es")
        if scr is not None and not _privilege_box(scr, lang, "install"):
            return False
        return original_start_software(self, components)

    def start_uninstall_bridge(self, components):
        scr = screen_ref.get("scr")
        lang = screen_ref.get("lang", "es")
        if scr is not None and not _privilege_box(scr, lang, "uninstall"):
            return False
        return original_start_uninstall(self, components)

    tui.confirm = confirm_bridge
    tui.TaskManager.start_software = start_software_bridge
    tui.TaskManager.start_uninstall = start_uninstall_bridge
    try:
        return tui.main()
    finally:
        tui.confirm = original_confirm
        tui.TaskManager.start_software = original_start_software
        tui.TaskManager.start_uninstall = original_start_uninstall


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEONES RC4 default runner")
    parser.add_argument("--rc2", action="store_true", help="run the historical RC2 wizard")
    parser.add_argument("--json", action="store_true", help="emit recommender JSON")
    parser.add_argument("--inventory", action="store_true", help="show component inventory and uninstall offers, then exit")
    parser.add_argument("--purpose", action="append", dest="purposes", help="non-interactive purpose; repeatable")
    args = parser.parse_args(argv)

    if args.inventory:
        inv = ROOT / "scripts" / "rc4_component_inventory.py"
        return subprocess.run([sys.executable, str(inv)], cwd=ROOT, check=False).returncode

    if args.rc2:
        return subprocess.run([sys.executable, str(RC2_WIZARD)], cwd=ROOT, check=False).returncode

    if args.purposes is None and not args.json and sys.stdin.isatty() and sys.stdout.isatty():
        return run_tui()

    purposes = list(dict.fromkeys(args.purposes or choose_purposes()))
    command = [sys.executable, str(RECOMMENDER)]
    for purpose in purposes:
        command.extend(["--purpose", purpose])
    if args.json:
        command.append("--json")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
