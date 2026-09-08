#!/usr/bin/env python3
"""LEONES RC4 default runner (also wired from ./leones).

The normal terminal path opens the dependency-free retro ASCII TUI. Privileged
software installation/uninstallation is authorized from inside the TUI so
sudo never steals the curses terminal for an external password prompt.
"""
from __future__ import annotations

import argparse
import curses
import inspect
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


def _sudo_available() -> bool:
    import shutil
    return shutil.which("sudo") is not None


def _sudo_cached() -> bool:
    if os.geteuid() == 0:
        return True
    if not _sudo_available():
        return False
    return subprocess.run(
        ["sudo", "-n", "-v"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _privilege_box(scr, lang: str, operation: str) -> bool:
    """Authorize sudo without allowing a sudo prompt to escape the TUI."""
    if os.geteuid() == 0 or _sudo_cached():
        return True
    if not _sudo_available():
        return True

    h, w = scr.getmaxyx()
    bw = min(96, max(60, w - 6))
    bh = 9
    x = max(2, (w - bw) // 2)
    y = max(4, h // 2 - bh // 2)
    title = "AUTORIZACIÓN DEL SISTEMA" if lang == "es" else "SYSTEM AUTHORIZATION"
    action = "instalación" if operation == "install" else "desinstalación"

    _box(scr, y, x, bh, bw, title)
    _put(scr, y + 2, x + 3,
         f"La {action} requiere privilegios de administrador." if lang == "es"
         else f"{action.capitalize()} requires administrator privileges.", bw - 6)
    _put(scr, y + 4, x + 3,
         "[Y] Autorizar    [N/ESC] Cancelar" if lang == "es"
         else "[Y] Authorize    [N/ESC] Cancel", bw - 6)
    scr.refresh()

    while True:
        key = scr.getch()
        if key in (ord("n"), ord("N"), 27):
            return False
        if key in (ord("y"), ord("Y")):
            break

    _box(scr, y, x, bh, bw, title)
    _put(scr, y + 2, x + 3,
         "Contraseña de sudo:" if lang == "es" else "sudo password:", bw - 6)
    _put(scr, y + 4, x + 3,
         "Entrada oculta · ENTER confirma" if lang == "es"
         else "Hidden input · ENTER confirms", bw - 6)
    scr.refresh()

    password = ""
    try:
        curses.echo(False)
        while True:
            key = scr.getch()
            if key in (10, 13):
                break
            if key == 27:
                return False
            if key in (curses.KEY_BACKSPACE, 127, 8):
                password = password[:-1]
            elif 32 <= key <= 126:
                password += chr(key)
            _put(scr, y + 5, x + 3, "*" * len(password), bw - 6)
            scr.refresh()
    finally:
        curses.echo(True)

    try:
        proc = subprocess.run(
            ["sudo", "-S", "-v"],
            input=password + "\n",
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    finally:
        password = ""

    _box(scr, y, x, bh, bw, title)
    if proc.returncode == 0:
        _put(scr, y + 2, x + 3,
             "Privilegios autorizados. Se ejecutará en segundo plano." if lang == "es"
             else "Privileges authorized. It will run in background.", bw - 6)
        _put(scr, y + 4, x + 3, "ENTER continuar" if lang == "es" else "ENTER continue", bw - 6)
        scr.refresh()
        while scr.getch() not in (10, 13):
            pass
        return True

    _put(scr, y + 2, x + 3,
         "No se pudo autorizar sudo. Operación cancelada." if lang == "es"
         else "sudo authorization failed. Operation cancelled.", bw - 6)
    _put(scr, y + 4, x + 3, "ENTER volver" if lang == "es" else "ENTER back", bw - 6)
    scr.refresh()
    while scr.getch() not in (10, 13, 27):
        pass
    return False


def run_tui() -> int:
    """Run the TUI with privilege authorization kept inside its confirmation box."""
    from scripts import rc4_tui as tui

    original_confirm = tui.confirm

    def confirm_bridge(scr, lang, title, question):
        approved = original_confirm(scr, lang, title, question)
        if not approved:
            return False

        # Inspect the TUI caller only to distinguish software install/uninstall
        # from model installation. The existing confirmation box remains the
        # effective user-action boundary for every operation.
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        panel = caller.f_locals.get("panel") if caller is not None else None
        if panel == "software":
            return _privilege_box(scr, lang, "install")
        if panel == "uninstall":
            return _privilege_box(scr, lang, "uninstall")
        return True

    tui.confirm = confirm_bridge
    try:
        return tui.main()
    finally:
        tui.confirm = original_confirm


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
