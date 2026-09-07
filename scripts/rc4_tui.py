#!/usr/bin/env python3
"""LEONES RC4 interactive TUI.

Flow: language -> machine state -> mandatory multi-select intent ->
recommendations -> explicit model selection/consent -> installation progress
-> refreshed machine state.

The recommender envelope remains ESTIMATED and never authorizes execution.
Installation authorization exists only at the explicit user-consent boundary
inside this TUI.
"""
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
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
INSTALLER = ROOT / "scripts" / "rc4_model_install.py"
INVENTORY = ROOT / "scripts" / "rc4_component_inventory.py"
MODELS_DIR = ROOT / "models"
PURPOSES = (("programming", "PROGRAMMING"), ("reasoning", "REASONING"), ("research", "RESEARCH"), ("chat", "CHAT"), ("multimodal", "MULTIMODAL"), ("embedding", "EMBEDDING"), ("general", "GENERAL"))


def memory_stats():
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0]) * 1024
        total, available = values["MemTotal"], values["MemAvailable"]
        used = total - available
        return used, total, round(used * 100 / total)
    except Exception:
        return 0, 0, 0


def cpu_percent():
    try:
        return min(100, round(os.getloadavg()[0] * 100 / (os.cpu_count() or 1)))
    except OSError:
        return 0


def disk_stats():
    try:
        u = shutil.disk_usage(ROOT)
        return u.used, u.total, round(u.used * 100 / u.total)
    except OSError:
        return 0, 0, 0


def human_bytes(value):
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def directory_bytes(path):
    total = 0
    if not path.exists():
        return 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def hardware():
    cpu = "desconocido"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    gpu = "no detectada"
    if shutil.which("nvidia-smi"):
        try:
            p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=5, check=False)
            if p.returncode == 0 and p.stdout.strip():
                gpu = p.stdout.strip().replace("\n", "; ")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return cpu, os.cpu_count() or 1, gpu


def inventory():
    try:
        p = subprocess.run([sys.executable, str(INVENTORY), "--json"], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
        return json.loads(p.stdout)
    except Exception:
        return {"components": []}


def agents():
    names = []
    for directory in (ROOT / "agents", ROOT / ".leones" / "agents"):
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if not child.name.startswith(".") and (child.is_dir() or child.suffix in {".py", ".sh", ".json", ".yaml", ".yml"}):
                    names.append(child.stem if child.is_file() else child.name)
    return list(dict.fromkeys(names))


def local_models():
    if not MODELS_DIR.is_dir():
        return []
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def box(stdscr, y, x, h, w, title):
    if h < 3 or w < 4:
        return
    stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
    for row in range(y + 1, y + h - 1):
        stdscr.addstr(row, x, "|")
        stdscr.addstr(row, x + w - 1, "|")
    stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
    label = f"[ {title} ]"
    if len(label) < w - 4:
        stdscr.addstr(y, x + 2, label)


def put(stdscr, y, x, text, width):
    if width <= 0 or y < 0 or y >= stdscr.getmaxyx()[0]:
        return
    try:
        stdscr.addnstr(y, x, str(text), width)
    except curses.error:
        pass


def language_screen(stdscr):
    languages = (("es", "Español"), ("en", "English"))
    focus = 0
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        bw = min(64, max(40, w - 4)); x = max(1, (w - bw) // 2)
        box(stdscr, 3, x, 11, bw, "LEONES RC4")
        put(stdscr, 5, x + 4, "SELECCIONA IDIOMA" if focus == 0 else "SELECT LANGUAGE", bw - 8)
        for i, (_, label) in enumerate(languages):
            put(stdscr, 8 + i, x + 8, f"{'>' if i == focus else ' '} [{i + 1}] {label}", bw - 16)
        put(stdscr, 12, x + 4, "↑/↓ · ENTER", bw - 8)
        stdscr.refresh(); key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(languages)
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(languages)
        elif key in (10, 13, ord("1"), ord("2")):
            if key in (ord("1"), ord("2")): focus = int(chr(key)) - 1
            return languages[focus][0]
        elif key in (27, ord("q"), ord("Q")): raise SystemExit(0)


def machine_state(stdscr, language):
    while True:
        inv = inventory(); used, total, mp = memory_stats(); du, dt, dp = disk_stats(); cpu, cores, gpu = hardware(); names = agents(); models = local_models()
        stdscr.erase(); h, w = stdscr.getmaxyx()
        if h < 25 or w < 92:
            put(stdscr, 1, 2, "LEONES RC4 — terminal demasiado pequeña (mín. 92x25)", w - 4); put(stdscr, 3, 2, "Redimensiona la ventana. Q: salir", w - 4); stdscr.refresh()
            if stdscr.getch() in (ord("q"), ord("Q"), 27): raise SystemExit(0)
            continue
        title = "LEONES // ESTADO DE LA MÁQUINA" if language == "es" else "LEONES // MACHINE STATE"
        box_title = "ESTADO DE LA MÁQUINA" if language == "es" else "MACHINE STATE"
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); box(stdscr, 1, 1, h - 4, w - 2, box_title)
        x = 4
        put(stdscr, 3, x, "HARDWARE", w - 8)
        put(stdscr, 4, x, f"CPU     {cpu} ({cores} logical CPUs)", w - 8)
        put(stdscr, 5, x, f"GPU     {gpu}", w - 8)
        put(stdscr, 7, x, "RECURSOS EN USO", w - 8)
        put(stdscr, 8, x, f"RAM     {human_bytes(used)} / {human_bytes(total)}   [{mp:>3}%]", w - 8)
        put(stdscr, 9, x, f"CPU     {cpu_percent():>3}%", w - 8)
        put(stdscr, 10, x, f"DISCO   {human_bytes(du)} / {human_bytes(dt)}   [{dp:>3}%]", w - 8)
        put(stdscr, 12, x, "SOFTWARE IA INSTALADO", w - 8)
        row = 13
        for c in inv.get("components", []):
            if c.get("installed"):
                detail = " :: " + ", ".join(c.get("models", [])) if c.get("models") else ""
                put(stdscr, row, x, f"● {c.get('display_name', c.get('component_id', '?'))}{detail}", w - 8); row += 1
        put(stdscr, row, x, f"● Agentes ({len(names)}) :: {', '.join(names) if names else 'ninguno detectado'}", w - 8); row += 1
        put(stdscr, row, x, f"● LLMs locales ({len(models)}) :: {', '.join(models) if models else 'ninguno instalado'}", w - 8); row += 2
        put(stdscr, row, x, "[ENTER] continuar   [Q] salir", w - 8)
        stdscr.refresh(); key = stdscr.getch()
        if key in (10, 13): return
        if key in (27, ord("q"), ord("Q")): raise SystemExit(0)


def recommend(purposes):
    command = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes: command += ["--purpose", purpose]
    try:
        p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
        data = json.loads(p.stdout)
        return data.get("status", "error"), data
    except Exception as exc:
        return "error", {"message": str(exc)}


def intent_screen(stdscr, language):
    selected = set(); focus = 0
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        if h < 25 or w < 92:
            put(stdscr, 1, 2, "LEONES RC4 — terminal demasiado pequeña (mín. 92x25)", w - 4); stdscr.refresh()
            if stdscr.getch() in (ord("q"), ord("Q"), 27): raise SystemExit(0)
            continue
        title = "LEONES // INTENCIÓN DE USO" if language == "es" else "LEONES // USER INTENT"
        help_text = "Selecciona uno o varios propósitos. ENTER recomienda." if language == "es" else "Select one or more purposes. ENTER recommends."
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); box(stdscr, 1, 1, h - 4, w - 2, "USER INTENT[] — MULTI SELECT — REQUIRED")
        put(stdscr, 3, 4, help_text, w - 8)
        for i, (key, label) in enumerate(PURPOSES):
            put(stdscr, 5 + i, 6, f"{'>' if i == focus else ' '} [{'X' if key in selected else ' '}] {i + 1}. {label}", w - 12)
        footer = "ESPACIO seleccionar   ENTER recomendar   Q salir" if language == "es" else "SPACE select   ENTER recommend   Q quit"
        put(stdscr, h - 2, 2, footer, w - 4); stdscr.refresh(); key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(PURPOSES)
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(PURPOSES)
        elif key == ord(" "):
            name = PURPOSES[focus][0]
            if name in selected: selected.remove(name)
            else: selected.add(name)
        elif key in (10, 13):
            if selected: return [p for p, _ in PURPOSES if p in selected]
        elif key in (27, ord("q"), ord("Q")): raise SystemExit(0)


def confirm_screen(stdscr, language, row):
    model_id = row.get("model_id", "?")
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        title = "LEONES // CONFIRMAR INSTALACIÓN" if language == "es" else "LEONES // CONFIRM INSTALLATION"
        box_title = "CONSENTIMIENTO EXPLÍCITO" if language == "es" else "EXPLICIT CONSENT"
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); box(stdscr, 2, 1, h - 6, w - 2, box_title)
        x = 5
        put(stdscr, 5, x, "MODELO SELECCIONADO", w - 10)
        put(stdscr, 7, x, model_id, w - 10)
        put(stdscr, 10, x, "La instalación descargará este modelo desde Hugging Face", w - 10)
        put(stdscr, 11, x, "y lo guardará en ./models/. Esta acción no mide ni ejecuta el modelo.", w - 10)
        put(stdscr, 14, x, "¿Confirmar instalación?  [Y] sí   [N/ESC] cancelar", w - 10)
        stdscr.refresh(); key = stdscr.getch()
        if key in (ord("y"), ord("Y")): return True
        if key in (ord("n"), ord("N"), 27): return False


def install_progress(stdscr, language, row):
    model_id = row.get("model_id", "?")
    target = MODELS_DIR / model_id.replace("/", "--")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    before = directory_bytes(target)
    command = [sys.executable, str(INSTALLER), "--model-id", model_id, "--output-dir", str(MODELS_DIR)]
    try:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except OSError as exc:
        return False, str(exc)

    lines = []
    started = time.monotonic()
    last_size = before
    spinner = ("|", "/", "-", "\\")
    while process.poll() is None:
        current = directory_bytes(target)
        elapsed = max(time.monotonic() - started, 0.001)
        rate = max(0, (current - before) / elapsed)
        if process.stdout is not None:
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    lines.append(line.strip())
                    lines = lines[-4:]
            except OSError:
                pass
        stdscr.erase(); h, w = stdscr.getmaxyx()
        title = "LEONES // INSTALACIÓN" if language == "es" else "LEONES // INSTALLATION"
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); box(stdscr, 2, 1, h - 6, w - 2, "OPERACIÓN RC4")
        x = 5
        put(stdscr, 5, x, f"MODELO: {model_id}", w - 10)
        put(stdscr, 7, x, f"ESTADO: descargando {spinner[int(elapsed * 4) % 4]}", w - 10)
        put(stdscr, 8, x, f"DATOS LOCALES: {human_bytes(current)}   VELOCIDAD: {human_bytes(rate)}/s", w - 10)
        put(stdscr, 10, x, "ACTIVIDAD", w - 10)
        for i, line in enumerate(lines): put(stdscr, 11 + i, x, line, w - 10)
        put(stdscr, h - 3, x, "La operación está activa; no cierres LEONES.", w - 10)
        stdscr.refresh(); time.sleep(0.25)

    output, _ = process.communicate(timeout=5)
    if output:
        lines.extend(line.strip() for line in output.splitlines())
        lines = lines[-4:]
    success = process.returncode == 0
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        title = "LEONES // INSTALACIÓN" if language == "es" else "LEONES // INSTALLATION"
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); box(stdscr, 2, 1, h - 6, w - 2, "OPERACIÓN RC4")
        x = 5
        put(stdscr, 5, x, f"MODELO: {model_id}", w - 10)
        put(stdscr, 7, x, "ESTADO: ✓ completada" if success else "ESTADO: ✗ fallida", w - 10)
        put(stdscr, 8, x, f"TAMAÑO LOCAL: {human_bytes(directory_bytes(target))}", w - 10)
        for i, line in enumerate(lines): put(stdscr, 10 + i, x, line, w - 10)
        put(stdscr, h - 3, x, "ENTER volver al estado de la máquina   Q salir", w - 10)
        stdscr.refresh(); key = stdscr.getch()
        if key in (10, 13): return success, "Instalación completada" if success else "La instalación falló"
        if key in (ord("q"), ord("Q"), 27): raise SystemExit(0)


def result_screen(stdscr, language, purposes):
    status, result = recommend(purposes)
    focus = 0
    while True:
        rows = result.get("recommendations") or []
        if rows:
            focus = max(0, min(focus, len(rows) - 1))
        stdscr.erase(); h, w = stdscr.getmaxyx(); title = "LEONES // RECOMENDADOR RC4" if language == "es" else "LEONES // RC4 RECOMMENDER"
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); box(stdscr, 1, 1, h - 4, w - 2, "FITLLM / LLMFIT + EVIDENCE")
        x = 4; put(stdscr, 3, x, f"STATUS: {status.upper()}", w - 8); put(stdscr, 4, x, f"INTENT: {', '.join(purposes)}", w - 8)
        put(stdscr, 5, x, f"CANDIDATES: {result.get('candidate_count', 0)}/3", w - 8)
        put(stdscr, 6, x, "KIND: ESTIMATED   EXECUTION_AUTHORIZED: False", w - 8)
        put(stdscr, 7, x, "MEASUREMENT_AUTHORIZED: False   MEASURED: False", w - 8)
        put(stdscr, 8, x, "BOUNDARY: evidence_backed_intersection", w - 8)
        put(stdscr, 10, x, "PROPUESTAS — selecciona un modelo para instalar" if language == "es" else "PROPOSALS — select a model to install", w - 8)
        for i, row in enumerate(rows[:3]):
            marker = ">" if i == focus else " "
            put(stdscr, 12 + i, x, f"{marker} [{i + 1}] {row.get('model_id', '?')} :: ESTIMATED", w - 8)
        if not rows: put(stdscr, 12, x, result.get("message", "Sin candidatos"), w - 8)
        footer = "↑/↓ o 1-3 seleccionar   ENTER instalar   R repetir   Q salir" if language == "es" else "↑/↓ or 1-3 select   ENTER install   R repeat   Q quit"
        put(stdscr, h - 2, 2, footer, w - 4); stdscr.refresh(); key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27): raise SystemExit(0)
        if key in (curses.KEY_UP, ord("k")) and rows: focus = (focus - 1) % len(rows)
        elif key in (curses.KEY_DOWN, ord("j")) and rows: focus = (focus + 1) % len(rows)
        elif key in (ord("1"), ord("2"), ord("3")) and rows:
            selected = int(chr(key)) - 1
            if selected < len(rows): focus = selected
        elif key in (10, 13) and rows:
            row = rows[focus]
            if confirm_screen(stdscr, language, row):
                success, _ = install_progress(stdscr, language, row)
                if success:
                    machine_state(stdscr, language)
                else:
                    return
        elif key in (ord("r"), ord("R")):
            status, result = recommend(purposes); focus = 0
        elif key in (ord("b"), ord("B")): return


def main():
    def app(stdscr):
        curses.curs_set(0); stdscr.keypad(True)
        language = language_screen(stdscr)
        machine_state(stdscr, language)
        while True:
            purposes = intent_screen(stdscr, language)
            result_screen(stdscr, language, purposes)
    curses.wrapper(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
