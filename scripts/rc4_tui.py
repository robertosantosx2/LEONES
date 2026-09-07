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
        return min(100, round(os.getloadavg()[0] * 100 / (os.cpu_count() or 1)))
    except Exception:
        return 0


def pctdisk() -> int:
    try:
        disk = shutil.disk_usage(ROOT)
        return round(disk.used * 100 / disk.total)
    except Exception:
        return 0


def put(screen, y: int, x: int, text: str, width: int) -> None:
    if width > 0:
        try:
            screen.addstr(y, x, text[:width])
        except curses.error:
            pass


def box(screen, y: int, x: int, height: int, width: int, title: str) -> None:
    if height < 3 or width < 4:
        return
    try:
        screen.addstr(y, x, "+" + "-" * (width - 2) + "+")
        for row in range(y + 1, y + height - 1):
            screen.addstr(row, x, "|")
            screen.addstr(row, x + width - 1, "|")
        screen.addstr(y + height - 1, x, "+" + "-" * (width - 2) + "+")
        screen.addstr(y, x + 2, "[ " + title + " ]")
    except curses.error:
        pass


def pause(screen, message: str) -> None:
    height, width = screen.getmaxyx()
    put(screen, height - 2, 2, message, width - 4)
    screen.refresh()
    screen.getch()


def ask(screen, prompt: str) -> str:
    height, width = screen.getmaxyx()
    curses.echo(); curses.curs_set(1)
    put(screen, height - 2, 2, prompt, width - 4); screen.refresh()
    try:
        value = screen.getstr(height - 1, 2, max(1, width - 5)).decode("utf8", "replace").strip()
    finally:
        curses.noecho(); curses.curs_set(0)
    return value


def run_recommendation(purposes: list[str]) -> tuple[str, dict]:
    try:
        command = [sys.executable, str(REC), "--json"]
        for purpose in purposes:
            command += ["--purpose", purpose]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        data = json.loads(result.stdout)
        return data.get("status", "error"), data
    except Exception as exc:
        return "error", {"message": str(exc)}


# Backward-compatible name used by older TUI tests/callers.
recommend = run_recommendation


def run_operation(screen, command: list[str], *, operation: str, phase: OperationPhase) -> tuple[int, str]:
    """Run a real installer/uninstaller without making the TUI appear frozen."""
    try:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except OSError as exc:
        return 127, terminal_progress(operation, False, str(exc)).render()

    lines: list[str] = []
    spinner = ("|", "/", "-", "\\")
    tick = 0
    screen.timeout(100)
    started = time.monotonic()
    while process.poll() is None:
        if process.stdout is not None:
            line = process.stdout.readline()
            if line:
                lines.append(line.rstrip())
        elapsed = int(time.monotonic() - started)
        render_operation(screen, OperationProgress(operation, phase, detail=f"{spinner[tick % len(spinner)]} actividad {elapsed}s"))
        tick += 1
    if process.stdout is not None:
        lines.extend(x.rstrip() for x in process.stdout.readlines())
    rc = process.returncode
    terminal = terminal_progress(operation, rc == 0, "completado" if rc == 0 else f"código {rc}")
    render_operation(screen, terminal)
    screen.timeout(-1)
    return rc, "\n".join(lines[-12:] + [terminal.render()])


def render_operation(screen, progress: OperationProgress) -> None:
    height, width = screen.getmaxyx()
    box(screen, max(1, height // 2 - 4), 5, 8, max(20, width - 10), "ACTIVIDAD RC4")
    put(screen, height // 2, 8, progress.render(), width - 16)
    put(screen, height // 2 + 2, 8, "La TUI permanece activa durante la operación.", width - 16)
    screen.refresh()


def draw(screen, inventory: dict, selected: set[str], focus: int, phase: str, status: str = "", result: dict | None = None) -> None:
    screen.erase(); height, width = screen.getmaxyx()
    if height < 25 or width < 92:
        put(screen, 1, 2, "LEONES RC4 TUI -- terminal demasiado pequena (min 92x25)", width - 4); screen.refresh(); return
    put(screen, 0, max(2, (width - 46) // 2), "LEONES // AI OPERATING SYSTEM v4", 46)
    left_width, right_x = 27, 30; right_width = width - right_x - 2
    box(screen, 1, 1, height - 3, left_width, "NAVIGATION")
    navigation = ["Idioma", "Estado de la máquina", "Propósito(s)", "Evidencia", "Recomendación", "Selección", "Stack", "Runtime / Benchmark"]
    for index, item in enumerate(navigation): put(screen, 3 + index, 4, (">" if item == phase else " ") + " " + item, left_width - 6)
    box(screen, 1, right_x, 8, right_width, "ESTADO DE LA MÁQUINA")
    put(screen, 3, right_x + 3, f"CPU {pctcpu():3}%   RAM {pctmem():3}%   DISCO {pctdisk():3}%", right_width - 6)
    names = (("fitllm", "FitLLM"), ("ods", "ODS"), ("magnitude", "Magnitude"), ("llms", "LLMs"), ("hermes", "Hermes"), ("omh", "OMH"))
    put(screen, 5, right_x + 3, "IA: " + " ".join(f'{label}={"OK" if comp(inventory, key).get("installed") else "--"}' for key, label in names[:3]), right_width - 6)
    put(screen, 6, right_x + 3, "    " + " ".join(f'{label}={"OK" if comp(inventory, key).get("installed") else "--"}' for key, label in names[3:]), right_width - 6)
    workspace_y = 11; box(screen, workspace_y, right_x, height - workspace_y - 3, right_width, "RC4 WORKSPACE")
    x, content_width = right_x + 3, right_width - 6
    put(screen, workspace_y + 2, x, "FASE: " + phase.upper(), content_width)
    if phase == "Idioma":
        put(screen, workspace_y + 4, x, "> Español", content_width); put(screen, workspace_y + 5, x, "  English", content_width)
    elif phase == "Estado de la máquina":
        put(screen, workspace_y + 4, x, "Hardware + recursos + software IA", content_width)
        put(screen, workspace_y + 6, x, "ENTER para continuar; instalaciones muestran actividad/progreso", content_width)
    elif phase == "Propósito(s)":
        put(screen, workspace_y + 4, x, "USER INTENT[] · selección múltiple", content_width)
        for index, (_, label) in enumerate(PURPOSES): put(screen, workspace_y + 6 + index, x, f'{">" if index == focus else " "} [{"X" if PURPOSES[index][0] in selected else " "}] {index + 1}. {label}', content_width)
    elif phase == "Evidencia":
        put(screen, workspace_y + 4, x, "Hugging Face + Artificial Analysis", content_width); put(screen, workspace_y + 5, x, "Feed <=100 -> intersección -> LLMFit", content_width); put(screen, workspace_y + 7, x, "ENTER para ejecutar recomendación", content_width)
    elif phase == "Recomendación":
        put(screen, workspace_y + 4, x, "STATUS: " + (status or "READY").upper(), content_width)
        rows = (result or {}).get("recommendations") or []
        for index, row in enumerate(rows[:3], 1): put(screen, workspace_y + 6 + index, x, f'[{index}] {row.get("model_id", "?")} :: ESTIMATED', content_width)
        if not rows and result: put(screen, workspace_y + 6, x, result.get("message", "Sin candidatos"), content_width)
    elif phase == "Selección": put(screen, workspace_y + 4, x, "El usuario elige el modelo. ESTIMATED no autoriza ejecución.", content_width)
    elif phase == "Stack":
        put(screen, workspace_y + 4, x, "> Magnitude", content_width); put(screen, workspace_y + 5, x, "  ODS", content_width); put(screen, workspace_y + 6, x, "  ninguno", content_width); put(screen, workspace_y + 8, x, "G = gestionar/instalar   D = desinstalar   ENTER = continuar", content_width)
    else:
        put(screen, workspace_y + 4, x, "Runtime -> A01 -> MEASURED", content_width); put(screen, workspace_y + 5, x, "Doble autorización: ejecución + medición", content_width)
    put(screen, height - 1, 2, "TAB/ARROWS mover  SPACE select  ENTER aceptar  B volver  Q salir", width - 4); screen.refresh()


def manage(screen, inventory: dict) -> None:
    options = [("LLMs seleccionados", None), ("Instalar LLM concreto (ruta completa)", None), ("ODS", "--ods"), ("Magnitude", "--magnitude")]; focus = 0
    while True:
        draw(screen, inventory, set(), focus, "Stack"); height, width = screen.getmaxyx(); box(screen, 14, 34, 10, width - 36, "GESTIONAR / INSTALAR")
        for index, (label, _) in enumerate(options): put(screen, 16 + index, 37, ("> " if index == focus else "  ") + label, width - 40)
        key = screen.getch()
        if key in (ord("b"), ord("B"), 27): return
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(options)
        elif key in (10, 13):
            flag = options[focus][1]
            if flag:
                _, output = run_operation(screen, [str(INS), flag], operation="install", phase=OperationPhase.INSTALLING); pause(screen, output + "\nENTER")
            elif focus == 1:
                path = ask(screen, "Ruta completa del fichero LLM: "); pause(screen, "Ruta recibida: " + path + " | validación antes de instalar. ENTER") if path else None
            else: pause(screen, "Selección de LLM conservada. ENTER")
            return


def unmanage(screen, inventory: dict) -> None:
    offers = [x for x in inventory.get("uninstall_offers", []) if x.get("component_id") != "leones"]
    options = [(x["display_name"], x["uninstall_flag"]) for x in offers] + [("Cancelar", None)]; focus = 0
    while True:
        draw(screen, inventory, set(), focus, "Stack"); height, width = screen.getmaxyx(); box(screen, 14, 34, min(13, 5 + len(options)), width - 36, "DESINSTALAR")
        for index, (label, _) in enumerate(options): put(screen, 16 + index, 37, ("> " if index == focus else "  ") + label, width - 40)
        key = screen.getch()
        if key in (ord("b"), ord("B"), 27): return
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(options)
        elif key in (10, 13):
            _, flag = options[focus]
            if not flag: return
            if flag == "--llms":
                models = comp(inventory, "llms").get("models", []); name = ask(screen, "Modelo a desinstalar (nombre exacto): ")
                if name in models: _, output = run_operation(screen, ["ollama", "rm", name], operation="uninstall", phase=OperationPhase.REMOVING); pause(screen, output + "\nENTER")
            else:
                _, output = run_operation(screen, ["bash", str(UN), flag, "--yes"], operation="uninstall", phase=OperationPhase.REMOVING); pause(screen, output + "\nENTER")
            return


def main() -> int:
    selected: set[str] = set(); focus = 0; phase = "Idioma"; status = "ready"; result: dict | None = None; inventory = inv()
    def app(screen) -> None:
        nonlocal focus, phase, status, result, inventory
        curses.curs_set(0); screen.keypad(True)
        while True:
            draw(screen, inventory, selected, focus, phase, status, result); key = screen.getch()
            if key in (ord("q"), ord("Q")): return
            if key in (ord("b"), ord("B")):
                phase = {"Propósito(s)": "Estado de la máquina", "Evidencia": "Propósito(s)", "Recomendación": "Propósito(s)", "Selección": "Recomendación", "Stack": "Selección", "Runtime / Benchmark": "Stack"}.get(phase, phase); continue
            if phase == "Idioma" and key in (10, 13): phase = "Estado de la máquina"
            elif phase == "Estado de la máquina" and key in (10, 13): phase = "Propósito(s)"
            elif phase == "Propósito(s)":
                if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(PURPOSES)
                elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(PURPOSES)
                elif key == ord(" "):
                    purpose = PURPOSES[focus][0]; selected.remove(purpose) if purpose in selected else selected.add(purpose)
                elif key in (10, 13):
                    if not selected: pause(screen, "Debes seleccionar al menos un propósito. ENTER")
                    else: phase = "Evidencia"
            elif phase == "Evidencia" and key in (10, 13):
                status, result = run_recommendation([purpose for purpose, _ in PURPOSES if purpose in selected]); phase = "Recomendación"
            elif phase == "Recomendación" and key in (10, 13): phase = "Selección"
            elif phase == "Selección" and key in (10, 13): phase = "Stack"
            elif phase == "Stack":
                if key in (ord("g"), ord("G"), ord("s"), ord("S")): manage(screen, inventory); inventory = inv()
                elif key in (ord("d"), ord("D")): unmanage(screen, inventory); inventory = inv()
                elif key in (10, 13): phase = "Runtime / Benchmark"
            elif phase == "Runtime / Benchmark" and key in (ord("r"), ord("R")): phase = "Stack"
    curses.wrapper(app); return 0


if __name__ == "__main__": raise SystemExit(main())
