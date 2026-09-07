#!/usr/bin/env python3
"""LEONES RC4 interactive TUI.

The TUI is deliberately non-blocking while installations run.  A persistent
navigation frame stays available so the user can inspect the machine,
re-run recommendations, review installed models, or start another software
operation while a background task downloads/installs models.

The recommender envelope remains ESTIMATED and never authorizes execution.
Installation authorization exists only at the explicit user-consent boundary.
"""
from __future__ import annotations

import curses
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
INSTALLER = ROOT / "scripts" / "rc4_model_install.py"
INVENTORY = ROOT / "scripts" / "rc4_component_inventory.py"
INSTALL_SH = ROOT / "install.sh"
MODELS_DIR = ROOT / "models"
PURPOSES = (
    ("programming", "PROGRAMMING"),
    ("reasoning", "REASONING"),
    ("research", "RESEARCH"),
    ("chat", "CHAT"),
    ("multimodal", "MULTIMODAL"),
    ("embedding", "EMBEDDING"),
    ("general", "GENERAL"),
)
SOFTWARE = (
    ("fitllm", "FitLLM"),
    ("ods", "ODS"),
    ("magnitude", "Magnitude"),
    ("hermes", "Hermes"),
    ("omh", "OMH"),
)


# ---------------------------------------------------------------------------
# Machine / inventory helpers


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
            p = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if p.returncode == 0 and p.stdout.strip():
                gpu = p.stdout.strip().replace("\n", "; ")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return cpu, os.cpu_count() or 1, gpu


def inventory():
    try:
        p = subprocess.run(
            [sys.executable, str(INVENTORY), "--json"],
            cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
        )
        return json.loads(p.stdout)
    except Exception:
        return {"components": []}


def agents():
    names = []
    for directory in (ROOT / "agents", ROOT / ".leones" / "agents"):
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if not child.name.startswith(".") and (
                    child.is_dir() or child.suffix in {".py", ".sh", ".json", ".yaml", ".yml"}
                ):
                    names.append(child.stem if child.is_file() else child.name)
    return list(dict.fromkeys(names))


def local_models():
    if not MODELS_DIR.is_dir():
        return []
    result = []
    for p in sorted(MODELS_DIR.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        # A model is considered installed only after the installer writes its
        # completion marker.  This prevents partial/legacy directories being
        # reported as usable LLMs.
        if (p / ".leones-installed.json").is_file():
            result.append(p.name)
    return result


# ---------------------------------------------------------------------------
# Drawing primitives / persistent frame


def put(stdscr, y, x, text, width):
    if width <= 0 or y < 0 or y >= stdscr.getmaxyx()[0]:
        return
    try:
        stdscr.addnstr(y, max(0, x), str(text), width)
    except curses.error:
        pass


def box(stdscr, y, x, h, w, title=""):
    if h < 3 or w < 4:
        return
    try:
        stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
        for row in range(y + 1, y + h - 1):
            stdscr.addstr(row, x, "|")
            stdscr.addstr(row, x + w - 1, "|")
        stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
        if title:
            label = f"[ {title} ]"
            if len(label) < w - 4:
                stdscr.addstr(y, x + 2, label)
    except curses.error:
        pass


def progress_bar(percent, width=28):
    if percent is None:
        return "[" + "." * width + "]"
    filled = max(0, min(width, round(width * percent / 100)))
    return "[" + "#" * filled + "." * (width - filled) + "]"


class TaskManager:
    """Small background process manager owned by the TUI main thread."""

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.active = False
        self.kind = ""
        self.label = ""
        self.model_index = 0
        self.model_total = 0
        self.model = ""
        self.percent = None
        self.downloaded = 0
        self.total = 0
        self.rate = 0.0
        self.phase = "idle"
        self.lines = []
        self.results = []
        self.finished_at = None

    def snapshot(self):
        with self.lock:
            return {
                "active": self.active, "kind": self.kind, "label": self.label,
                "model_index": self.model_index, "model_total": self.model_total,
                "model": self.model, "percent": self.percent,
                "downloaded": self.downloaded, "total": self.total,
                "rate": self.rate, "phase": self.phase,
                "lines": list(self.lines), "results": list(self.results),
                "finished_at": self.finished_at,
            }

    def _reset(self, kind, label):
        with self.lock:
            self.active = True
            self.kind = kind
            self.label = label
            self.model_index = 0
            self.model_total = 0
            self.model = ""
            self.percent = None
            self.downloaded = 0
            self.total = 0
            self.rate = 0.0
            self.phase = "preparing"
            self.lines = []
            self.results = []
            self.finished_at = None

    def _line(self, line):
        line = line.strip()
        if not line:
            return
        with self.lock:
            self.lines.append(line)
            self.lines = self.lines[-4:]
            if line.startswith("PROGRESS="):
                fields = dict(
                    part.split("=", 1) for part in line.split() if "=" in part
                )
                raw = fields.get("PROGRESS", "")
                try:
                    self.percent = float(raw.rstrip("%"))
                except ValueError:
                    self.percent = None
                try:
                    self.downloaded = int(fields.get("DOWNLOADED", self.downloaded))
                    self.total = int(fields.get("TOTAL", self.total))
                    self.rate = float(fields.get("RATE", self.rate))
                except ValueError:
                    pass
            elif line.startswith("PHASE="):
                self.phase = line.split("=", 1)[1]
            elif line.startswith("STATUS="):
                self.phase = line.split("=", 1)[1]

    def _run_process(self, command, label, model_index=0, model_total=0, model=""):
        with self.lock:
            self.model_index = model_index
            self.model_total = model_total
            self.model = model
            self.phase = "running"
        try:
            process = subprocess.Popen(
                command, cwd=ROOT, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
        except OSError as exc:
            self._line(f"ERROR={exc}")
            return False
        if process.stdout is not None:
            for line in process.stdout:
                self._line(line)
        returncode = process.wait()
        self._line(f"RETURN_CODE={returncode}")
        return returncode == 0

    def start_models(self, rows):
        if self.is_active():
            return False
        rows = list(rows)
        self._reset("models", f"Instalación de {len(rows)} modelo(s)")
        self.thread = threading.Thread(target=self._models_worker, args=(rows,), daemon=True)
        self.thread.start()
        return True

    def _models_worker(self, rows):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        results = []
        for index, row in enumerate(rows, 1):
            model_id = row.get("model_id", "?")
            target = MODELS_DIR / model_id.replace("/", "--")
            with self.lock:
                self.model_index = index
                self.model_total = len(rows)
                self.model = model_id
                self.phase = "downloading"
                self.percent = None
                self.downloaded = 0
                self.total = 0
                self.rate = 0.0
                self.lines = []
            command = [
                sys.executable, str(INSTALLER),
                "--model-id", model_id,
                "--output-dir", str(MODELS_DIR),
            ]
            ok = self._run_process(command, model_id, index, len(rows), model_id)
            detail = " | ".join(self.snapshot()["lines"][-2:])
            results.append((model_id, ok, detail))
            with self.lock:
                self.results = list(results)
        with self.lock:
            self.phase = "completed" if all(item[1] for item in results) else "completed_with_errors"
            self.active = False
            self.finished_at = time.monotonic()
            self.results = list(results)

    def start_software(self, component):
        if self.is_active():
            return False
        label = next((name for key, name in SOFTWARE if key == component), component)
        self._reset("software", f"Instalación de {label}")
        self.thread = threading.Thread(target=self._software_worker, args=(component,), daemon=True)
        self.thread.start()
        return True

    def _software_worker(self, component):
        command = ["bash", str(INSTALL_SH), f"--{component}"]
        ok = self._run_process(command, component)
        with self.lock:
            self.phase = "completed" if ok else "failed"
            self.active = False
            self.finished_at = time.monotonic()
            self.results = [(component, ok, " | ".join(self.lines[-3:]))]

    def is_active(self):
        with self.lock:
            return self.active


# ---------------------------------------------------------------------------
# Screens

NAV = (
    ("home", "INICIO"),
    ("state", "ESTADO"),
    ("recommend", "RECOMENDADOR"),
    ("models", "LLMs / INSTALACIÓN"),
    ("software", "SOFTWARE IA"),
)


def draw_shell(stdscr, language, active_key, task, title):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    if h < 25 or w < 96:
        put(stdscr, 1, 2, "LEONES RC4 — terminal demasiado pequeña (mín. 96x25)", w - 4)
        put(stdscr, 3, 2, "Redimensiona la ventana. Q: salir", w - 4)
        stdscr.refresh()
        return False
    put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title))
    box(stdscr, 1, 1, h - 3, w - 2, "LEONES RC4")
    nav_w = 25
    box(stdscr, 3, 3, h - 7, nav_w, "NAVEGACIÓN")
    for i, (key, label) in enumerate(NAV):
        marker = ">" if key == active_key else " "
        put(stdscr, 5 + i * 2, 6, f"{marker} [{i + 1}] {label}", nav_w - 6)
    put(stdscr, h - 5, 6, "↑/↓ mover", nav_w - 6)
    put(stdscr, h - 4, 6, "ENTER abrir", nav_w - 6)
    put(stdscr, h - 3, 6, "Q salir", nav_w - 6)

    op_x = 30
    op_w = w - op_x - 4
    box(stdscr, 3, op_x, 7, op_w, "OPERACIÓN EN SEGUNDO PLANO")
    snap = task.snapshot()
    if snap["active"]:
        label = snap["label"]
        if snap["model_total"]:
            label = f"MODELO {snap['model_index']}/{snap['model_total']}: {snap['model']}"
        put(stdscr, 5, op_x + 3, f"● ACTIVA  {label}", op_w - 6)
        if snap["percent"] is not None:
            put(stdscr, 6, op_x + 3, f"{progress_bar(snap['percent'])} {snap['percent']:5.1f}%", op_w - 6)
        else:
            put(stdscr, 6, op_x + 3, progress_bar(None), op_w - 6)
        put(stdscr, 7, op_x + 3, f"FASE: {snap['phase']}   DATOS: {human_bytes(snap['downloaded'])}   VELOCIDAD: {human_bytes(snap['rate'])}/s", op_w - 6)
        put(stdscr, 8, op_x + 3, "ENTER en el panel de operación para ver detalle", op_w - 6)
    else:
        phase = snap["phase"] if snap["phase"] != "idle" else "sin operaciones"
        put(stdscr, 5, op_x + 3, f"○ {phase.upper()}", op_w - 6)
        if snap["results"]:
            ok = sum(1 for _, success, _ in snap["results"] if success)
            put(stdscr, 6, op_x + 3, f"Último resultado: {ok}/{len(snap['results'])} operaciones correctas", op_w - 6)
        put(stdscr, 7, op_x + 3, "El TUI sigue disponible mientras no haya una operación activa", op_w - 6)
    return True


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


def state_panel(stdscr, language, task):
    h, w = stdscr.getmaxyx(); op_x = 30; content_y = 12
    inv = inventory(); used, total, mp = memory_stats(); du, dt, dp = disk_stats()
    cpu, cores, gpu = hardware(); names = agents(); models = local_models()
    box(stdscr, content_y, op_x, h - content_y - 2, w - op_x - 4, "ESTADO DE LA MÁQUINA")
    x = op_x + 3; width = w - op_x - 7
    put(stdscr, content_y + 2, x, "HARDWARE", width)
    put(stdscr, content_y + 3, x, f"CPU     {cpu} ({cores} logical CPUs)", width)
    put(stdscr, content_y + 4, x, f"GPU     {gpu}", width)
    put(stdscr, content_y + 6, x, "RECURSOS EN USO", width)
    put(stdscr, content_y + 7, x, f"RAM     {human_bytes(used)} / {human_bytes(total)}   [{mp:>3}%]", width)
    put(stdscr, content_y + 8, x, f"CPU     {cpu_percent():>3}%", width)
    put(stdscr, content_y + 9, x, f"DISCO   {human_bytes(du)} / {human_bytes(dt)}   [{dp:>3}%]", width)
    put(stdscr, content_y + 11, x, "SOFTWARE IA INSTALADO", width)
    row = content_y + 12
    for c in inv.get("components", []):
        if c.get("installed") and row < h - 4:
            detail = " :: " + ", ".join(c.get("models", [])) if c.get("models") else ""
            put(stdscr, row, x, f"● {c.get('display_name', c.get('component_id', '?'))}{detail}", width); row += 1
    if row < h - 4:
        put(stdscr, row, x, f"● Agentes ({len(names)}) :: {', '.join(names) if names else 'ninguno detectado'}", width); row += 1
    if row < h - 4:
        put(stdscr, row, x, f"● LLMs locales ({len(models)}) :: {', '.join(models) if models else 'ninguno instalado'}", width)


def home_panel(stdscr, language, task):
    h, w = stdscr.getmaxyx(); x = 30; width = w - x - 4
    box(stdscr, 12, x, h - 14, width, "PANEL PRINCIPAL")
    put(stdscr, 15, x + 3, "LEONES coordina selección, instalación y estado sin bloquear la interfaz.", width - 6)
    put(stdscr, 17, x + 3, "1  Estado de la máquina", width - 6)
    put(stdscr, 18, x + 3, "2  Recomendador RC4 (intención múltiple)", width - 6)
    put(stdscr, 19, x + 3, "3  LLMs / instalación", width - 6)
    put(stdscr, 20, x + 3, "4  Software IA", width - 6)
    put(stdscr, 22, x + 3, "Mientras una operación está activa, esta navegación sigue disponible.", width - 6)


def recommend(purposes):
    command = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes:
        command += ["--purpose", purpose]
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
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title))
        box(stdscr, 1, 1, h - 4, w - 2, "USER INTENT[] — MULTI SELECT — REQUIRED")
        put(stdscr, 3, 4, "Selecciona uno o varios propósitos. ENTER recomienda.", w - 8)
        for i, (key, label) in enumerate(PURPOSES):
            put(stdscr, 5 + i, 6, f"{'>' if i == focus else ' '} [{'X' if key in selected else ' '}] {i + 1}. {label}", w - 12)
        put(stdscr, h - 2, 2, "ESPACIO seleccionar   ENTER recomendar   Q salir", w - 4)
        stdscr.refresh(); key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(PURPOSES)
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(PURPOSES)
        elif key == ord(" "):
            name = PURPOSES[focus][0]
            if name in selected: selected.remove(name)
            else: selected.add(name)
        elif key in (10, 13):
            if selected: return [p for p, _ in PURPOSES if p in selected]
        elif key in (27, ord("q"), ord("Q")): raise SystemExit(0)


def confirm_models_screen(stdscr, language, rows):
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        title = "LEONES // CONFIRMAR INSTALACIÓN"
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title))
        box(stdscr, 2, 1, h - 6, w - 2, "CONSENTIMIENTO EXPLÍCITO")
        x = 5
        put(stdscr, 4, x, f"MODELOS SELECCIONADOS: {len(rows)}", w - 10)
        for i, row in enumerate(rows[:8]):
            put(stdscr, 6 + i, x, f"[{i + 1}] {row.get('model_id', '?')}", w - 10)
        put(stdscr, min(h - 5, 16), x, "Se descargarán desde Hugging Face y se guardarán en ./models/.", w - 10)
        put(stdscr, min(h - 4, 17), x, "La instalación no ejecuta ni mide los modelos.", w - 10)
        put(stdscr, h - 3, x, "¿Confirmar TODAS?  [Y] sí   [N/ESC] cancelar", w - 10)
        stdscr.refresh(); key = stdscr.getch()
        if key in (ord("y"), ord("Y")): return True
        if key in (ord("n"), ord("N"), 27): return False


def recommendation_panel(stdscr, language, task, state):
    # state is a small mutable holder owned by the UI thread.
    h, w = stdscr.getmaxyx(); x = 30; width = w - x - 4
    box(stdscr, 12, x, h - 14, width, "FITLLM / LLMFIT + EVIDENCE")
    if state.get("result") is None:
        put(stdscr, 15, x + 3, "No hay recomendación cargada.", width - 6)
        put(stdscr, 17, x + 3, "ENTER para iniciar la recomendación.", width - 6)
        return
    status = state.get("status", "error"); result = state["result"]; purposes = state.get("purposes", [])
    put(stdscr, 14, x + 3, f"STATUS: {status.upper()}", width - 6)
    put(stdscr, 15, x + 3, f"INTENT: {', '.join(purposes)}", width - 6)
    put(stdscr, 16, x + 3, f"CANDIDATES: {result.get('candidate_count', 0)}/3", width - 6)
    put(stdscr, 17, x + 3, "KIND: ESTIMATED   EXECUTION_AUTHORIZED: False", width - 6)
    put(stdscr, 18, x + 3, "MEASUREMENT_AUTHORIZED: False   MEASURED: False", width - 6)
    put(stdscr, 19, x + 3, "PROPUESTAS — SPACE marca uno o varios", width - 6)
    rows = result.get("recommendations") or []
    for i, row in enumerate(rows[:3]):
        selected = "X" if i in state.setdefault("selected", set()) else " "
        marker = ">" if i == state.get("focus", 0) else " "
        put(stdscr, 21 + i, x + 3, f"{marker} [{selected}] [{i + 1}] {row.get('model_id', '?')} :: ESTIMATED", width - 6)
    put(stdscr, h - 5, x + 3, "↑/↓ mover  SPACE marcar  1-3 marcar  ENTER instalar  R repetir", width - 6)


def model_panel(stdscr, language, task, state):
    h, w = stdscr.getmaxyx(); x = 30; width = w - x - 4
    box(stdscr, 12, x, h - 14, width, "LLMs / INSTALACIÓN")
    rows = state.get("rows") or []
    put(stdscr, 14, x + 3, "MODELOS LOCALES", width - 6)
    models = local_models()
    if models:
        for i, model in enumerate(models[:max(1, h - 20)]):
            put(stdscr, 16 + i, x + 3, f"● {model}", width - 6)
    else:
        put(stdscr, 16, x + 3, "ningún modelo instalado", width - 6)
    if rows:
        put(stdscr, 19, x + 3, "ÚLTIMA RECOMENDACIÓN", width - 6)
        for i, row in enumerate(rows[:3]):
            put(stdscr, 20 + i, x + 3, f"[{i + 1}] {row.get('model_id', '?')}", width - 6)
    put(stdscr, h - 5, x + 3, "R volver a recomendar   Q salir", width - 6)


def software_panel(stdscr, language, task, state):
    h, w = stdscr.getmaxyx(); x = 30; width = w - x - 4
    box(stdscr, 12, x, h - 14, width, "SOFTWARE IA")
    put(stdscr, 15, x + 3, "Selecciona un componente para instalar en segundo plano:", width - 6)
    for i, (_, label) in enumerate(SOFTWARE):
        put(stdscr, 17 + i, x + 6, f"{'>' if i == state.get('focus', 0) else ' '} [{i + 1}] {label}", width - 12)
    put(stdscr, h - 5, x + 3, "↑/↓ mover   ENTER instalar   Q salir", width - 6)


def operation_panel(stdscr, task):
    snap = task.snapshot(); h, w = stdscr.getmaxyx(); x = 30; width = w - x - 4
    box(stdscr, 12, x, h - 14, width, "DETALLE DE OPERACIÓN")
    put(stdscr, 15, x + 3, f"{snap['kind'].upper()} :: {snap['label']}", width - 6)
    if snap["model_total"]:
        put(stdscr, 17, x + 3, f"MODELO {snap['model_index']}/{snap['model_total']}: {snap['model']}", width - 6)
        if snap["percent"] is not None:
            put(stdscr, 18, x + 3, f"{progress_bar(snap['percent'], 40)} {snap['percent']:5.1f}%", width - 6)
        put(stdscr, 19, x + 3, f"DATOS: {human_bytes(snap['downloaded'])} / {human_bytes(snap['total'])}   VELOCIDAD: {human_bytes(snap['rate'])}/s", width - 6)
    put(stdscr, 21, x + 3, f"FASE: {snap['phase']}", width - 6)
    for i, line in enumerate(snap["lines"][-5:]):
        put(stdscr, 23 + i, x + 3, line, width - 6)
    put(stdscr, h - 5, x + 3, "B volver al panel anterior", width - 6)


def run_app(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(200)
    language = language_screen(stdscr)
    task = TaskManager()
    nav_index = 0
    panel = "home"
    recommendation = {"result": None, "status": "", "purposes": [], "selected": set(), "focus": 0}
    software_focus = 0
    last_results_seen = None

    # Initial machine state is displayed, but it no longer blocks the TUI.
    while True:
        active_key = panel if panel in {key for key, _ in NAV} else "home"
        title = "LEONES // CENTRO DE CONTROL RC4"
        if not draw_shell(stdscr, language, active_key, task, title):
            key = stdscr.getch()
            if key in (ord("q"), ord("Q"), 27):
                return
            continue

        if panel == "home":
            home_panel(stdscr, language, task)
        elif panel == "state":
            state_panel(stdscr, language, task)
        elif panel == "recommend":
            recommendation_panel(stdscr, language, task, recommendation)
        elif panel == "models":
            model_panel(stdscr, language, task, recommendation)
        elif panel == "software":
            recommendation["focus"] = software_focus
            software_panel(stdscr, language, task, recommendation)
        elif panel == "operation":
            operation_panel(stdscr, task)

        # A completed task remains visible until the user navigates away.  No
        # modal "installation finished" screen steals control from the user.
        snap = task.snapshot()
        if snap["results"] != last_results_seen:
            last_results_seen = list(snap["results"])

        stdscr.refresh()
        key = stdscr.getch()
        if key == -1:
            continue
        if key in (ord("q"), ord("Q"), 27):
            if task.is_active():
                # Do not kill a background installation just because the user
                # is leaving the TUI; the daemon thread keeps its process alive.
                return
            return

        if panel == "recommend":
            rows = recommendation.get("result", {}).get("recommendations") if recommendation.get("result") else []
            rows = rows or []
            if key in (curses.KEY_UP, ord("k")) and rows:
                recommendation["focus"] = (recommendation.get("focus", 0) - 1) % min(3, len(rows))
            elif key in (curses.KEY_DOWN, ord("j")) and rows:
                recommendation["focus"] = (recommendation.get("focus", 0) + 1) % min(3, len(rows))
            elif key == ord(" ") and rows:
                i = recommendation.get("focus", 0)
                if i in recommendation["selected"]: recommendation["selected"].remove(i)
                else: recommendation["selected"].add(i)
            elif key in (ord("1"), ord("2"), ord("3")) and rows:
                i = int(chr(key)) - 1
                if i < len(rows):
                    if i in recommendation["selected"]: recommendation["selected"].remove(i)
                    else: recommendation["selected"].add(i)
                    recommendation["focus"] = i
            elif key in (ord("r"), ord("R")):
                purposes = recommendation.get("purposes") or []
                if purposes:
                    status, result = recommend(purposes)
                    recommendation.update(status=status, result=result, selected=set(), focus=0)
            elif key in (10, 13):
                if not recommendation.get("result"):
                    purposes = intent_screen(stdscr, language)
                    status, result = recommend(purposes)
                    recommendation.update(status=status, result=result, purposes=purposes, selected=set(), focus=0)
                elif rows and recommendation["selected"] and not task.is_active():
                    chosen = [rows[i] for i in sorted(recommendation["selected"])]
                    if confirm_models_screen(stdscr, language, chosen):
                        task.start_models(chosen)
                        panel = "operation"
            elif key in (curses.KEY_LEFT, ord("h"), curses.KEY_RIGHT, ord("l")):
                panel = "home"
        elif panel == "software":
            if key in (curses.KEY_UP, ord("k")): software_focus = (software_focus - 1) % len(SOFTWARE)
            elif key in (curses.KEY_DOWN, ord("j")): software_focus = (software_focus + 1) % len(SOFTWARE)
            elif key in (10, 13) and not task.is_active():
                component = SOFTWARE[software_focus][0]
                task.start_software(component)
                panel = "operation"
        elif panel == "models":
            if key in (ord("r"), ord("R")):
                purposes = intent_screen(stdscr, language)
                status, result = recommend(purposes)
                recommendation.update(status=status, result=result, purposes=purposes, selected=set(), focus=0)
                panel = "recommend"
        elif panel == "operation":
            if key in (ord("b"), ord("B")):
                panel = "home"
        # Persistent navigation: numbers always work, and arrows cycle panels.
        if key in (ord("1"), ord("2"), ord("3"), ord("4"), ord("5")) and panel != "recommend" and panel != "software":
            idx = int(chr(key)) - 1
            if idx < len(NAV): panel = NAV[idx][0]
        elif key in (curses.KEY_UP, ord("k")) and panel not in {"recommend", "software"}:
            nav_index = (nav_index - 1) % len(NAV); panel = NAV[nav_index][0]
        elif key in (curses.KEY_DOWN, ord("j")) and panel not in {"recommend", "software"}:
            nav_index = (nav_index + 1) % len(NAV); panel = NAV[nav_index][0]
        elif key in (10, 13) and panel == "home":
            panel = NAV[nav_index][0]


def main():
    curses.wrapper(run_app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
