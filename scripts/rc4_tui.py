#!/usr/bin/env python3
"""LEONES RC4 persistent control-center TUI.

NORMATIVE CONTRACT: docs/TUI_RULES_RC4.md
The language screen is the only screen without the persistent navigation frame.
After language selection, TAB switches focus between navigation and content;
the menu, key hints, visible cursor and background-operation indicator remain
present for the whole session.
"""
from __future__ import annotations

import curses
import json
import os
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
UNINSTALL_SH = ROOT / "scripts" / "uninstall.sh"
MODELS_DIR = ROOT / "models"

PURPOSES = (("programming", "PROGRAMMING"), ("reasoning", "REASONING"),
            ("research", "RESEARCH"), ("chat", "CHAT"),
            ("multimodal", "MULTIMODAL"), ("embedding", "EMBEDDING"),
            ("general", "GENERAL"))
SOFTWARE = (("fitllm", "FitLLM"), ("ods", "ODS"),
            ("magnitude", "Magnitude"), ("hermes", "Hermes"), ("omh", "OMH"))
NAV = (("home", "INICIO"), ("state", "ESTADO"), ("recommend", "RECOMENDADOR"),
       ("models", "LLMs / INSTALACIÓN"), ("software", "SOFTWARE IA"),
       ("uninstall", "DESINSTALACIÓN"))

TEXT = {
    "es": {
        "nav": "NAVEGACIÓN", "content": "CONTENIDO", "ops": "OPERACIÓN EN SEGUNDO PLANO",
        "active": "ACTIVA", "idle": "SIN OPERACIONES", "completed": "COMPLETADA",
        "activity": "ACTIVIDAD", "phase": "FASE", "data": "DATOS", "rate": "VELOCIDAD",
        "focus_nav": "FOCO: NAVEGACIÓN", "focus_content": "FOCO: CONTENIDO",
        "tab": "TAB cambiar foco", "move": "↑/↓ mover", "open": "ENTER abrir",
        "back": "ESC volver", "quit": "Q salir", "select": "SPACE seleccionar",
        "keys": "TECLAS", "cursor": "CURSOR", "background": "en segundo plano",
        "install": "INSTALAR", "uninstall": "DESINSTALAR", "confirm": "CONFIRMAR",
        "none": "ninguno", "installed": "instalado", "selected": "seleccionado",
        "machine": "ESTADO DE LA MÁQUINA", "hardware": "HARDWARE", "resources": "RECURSOS EN USO",
        "software_installed": "SOFTWARE IA INSTALADO", "models_local": "LLMs LOCALES",
        "agents": "AGENTES", "recommendation": "RECOMENDACIÓN RC4", "intent": "INTENCIÓN",
        "recommend_now": "ENTER iniciar recomendación", "multiple": "MULTI SELECCIÓN",
        "model_select": "Selecciona uno o varios modelos recomendados", "software_select": "Selecciona uno o varios componentes para instalar en segundo plano",
        "uninstall_select": "Selecciona uno o varios componentes instalados para desinstalar",
        "no_installed": "No hay componentes instalados que ofrecer para desinstalación.",
        "confirm_install": "¿Confirmar instalación de todos los seleccionados? Y sí / N no",
        "confirm_uninstall": "¿Confirmar DESINSTALACIÓN de todos los seleccionados? Y sí / N no",
        "language": "SELECCIONA IDIOMA", "home": "Centro de control: puedes navegar mientras una operación continúa.",
        "estimated": "ESTIMATED · ejecución no autorizada · medición no autorizada",
        "finished": "Último resultado", "error": "La operación ha terminado con errores.",
        "ok": "La operación ha terminado correctamente.", "no_selection": "No hay elementos seleccionados.",
        "installing": "instalando", "downloading": "descargando", "preparing": "preparando",
        "running": "ejecutando", "unknown": "estado no disponible", "details": "DETALLE DE OPERACIÓN",
    },
    "en": {
        "nav": "NAVIGATION", "content": "CONTENT", "ops": "BACKGROUND OPERATION",
        "active": "ACTIVE", "idle": "NO OPERATIONS", "completed": "COMPLETED",
        "activity": "ACTIVITY", "phase": "PHASE", "data": "DATA", "rate": "SPEED",
        "focus_nav": "FOCUS: NAVIGATION", "focus_content": "FOCUS: CONTENT",
        "tab": "TAB switch focus", "move": "↑/↓ move", "open": "ENTER open",
        "back": "ESC back", "quit": "Q quit", "select": "SPACE select",
        "keys": "KEYS", "cursor": "CURSOR", "background": "in background",
        "install": "INSTALL", "uninstall": "UNINSTALL", "confirm": "CONFIRM",
        "none": "none", "installed": "installed", "selected": "selected",
        "machine": "MACHINE STATE", "hardware": "HARDWARE", "resources": "RESOURCES IN USE",
        "software_installed": "INSTALLED AI SOFTWARE", "models_local": "LOCAL LLMs",
        "agents": "AGENTS", "recommendation": "RC4 RECOMMENDATION", "intent": "INTENT",
        "recommend_now": "ENTER start recommendation", "multiple": "MULTI SELECT",
        "model_select": "Select one or more recommended models", "software_select": "Select one or more components to install in background",
        "uninstall_select": "Select one or more installed components to uninstall",
        "no_installed": "No installed components available for uninstall.",
        "confirm_install": "Confirm installation of all selected? Y yes / N no",
        "confirm_uninstall": "Confirm UNINSTALL of all selected? Y yes / N no",
        "language": "SELECT LANGUAGE", "home": "Control center: you can navigate while an operation continues.",
        "estimated": "ESTIMATED · execution not authorized · measurement not authorized",
        "finished": "Last result", "error": "The operation finished with errors.",
        "ok": "The operation finished successfully.", "no_selection": "No items selected.",
        "installing": "installing", "downloading": "downloading", "preparing": "preparing",
        "running": "running", "unknown": "status unavailable", "details": "OPERATION DETAIL",
    },
}


def t(lang, key):
    return TEXT.get(lang, TEXT["es"]).get(key, key)


def put(scr, y, x, text, width):
    if width <= 0 or y < 0 or y >= scr.getmaxyx()[0]: return
    try: scr.addnstr(y, max(0, x), str(text), width)
    except curses.error: pass


def box(scr, y, x, h, w, title=""):
    if h < 3 or w < 4: return
    try:
        scr.addstr(y, x, "+" + "-" * (w - 2) + "+")
        for r in range(y + 1, y + h - 1):
            scr.addstr(r, x, "|"); scr.addstr(r, x + w - 1, "|")
        scr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
        if title: scr.addstr(y, x + 2, f"[ {title} ]")
    except curses.error: pass


def human_bytes(value):
    size = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB": return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def progress_bar(percent, width=30):
    if percent is None: return "[" + "." * width + "]"
    n = max(0, min(width, round(width * percent / 100)))
    return "[" + "#" * n + "." * (width - n) + "]"


def memory_stats():
    try:
        vals = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1); vals[k] = int(v.split()[0]) * 1024
        total, avail = vals["MemTotal"], vals["MemAvailable"]
        used = total - avail; return used, total, round(100 * used / total)
    except Exception: return 0, 0, 0


def cpu_percent():
    try: return min(100, round(os.getloadavg()[0] * 100 / (os.cpu_count() or 1)))
    except OSError: return 0


def disk_stats():
    try:
        u = shutil.disk_usage(ROOT); return u.used, u.total, round(100 * u.used / u.total)
    except OSError: return 0, 0, 0


def hardware():
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip(); break
    except OSError: pass
    gpu = "not detected"
    if shutil.which("nvidia-smi"):
        try:
            p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=5, check=False)
            if p.returncode == 0 and p.stdout.strip(): gpu = p.stdout.strip().replace("\n", "; ")
        except (OSError, subprocess.TimeoutExpired): pass
    return cpu, os.cpu_count() or 1, gpu


def inventory():
    try:
        p = subprocess.run([sys.executable, str(INVENTORY), "--json"], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
        return json.loads(p.stdout)
    except Exception: return {"components": []}


def local_models():
    if not MODELS_DIR.is_dir(): return []
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".") and (p / ".leones-installed.json").is_file())


def agents():
    names = []
    for directory in (ROOT / "agents", ROOT / ".leones" / "agents"):
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if not child.name.startswith(".") and (child.is_dir() or child.suffix in {".py", ".sh", ".json", ".yaml", ".yml"}):
                    names.append(child.stem if child.is_file() else child.name)
    return list(dict.fromkeys(names))


class TaskManager:
    def __init__(self, lang="es"):
        self.lang = lang; self.lock = threading.Lock(); self.active = False
        self.kind = ""; self.label = ""; self.index = 0; self.total_items = 0; self.item = ""
        self.percent = None; self.downloaded = 0; self.total_bytes = 0; self.rate = 0.0
        self.phase = "idle"; self.results = []; self.started = None; self.finished = None

    def snapshot(self):
        with self.lock:
            return dict(active=self.active, kind=self.kind, label=self.label, index=self.index,
                        total_items=self.total_items, item=self.item, percent=self.percent,
                        downloaded=self.downloaded, total_bytes=self.total_bytes, rate=self.rate,
                        phase=self.phase, results=list(self.results), started=self.started, finished=self.finished)

    def _reset(self, kind, label, n):
        with self.lock:
            self.active = True; self.kind = kind; self.label = label; self.index = 0; self.total_items = n
            self.item = ""; self.percent = None; self.downloaded = 0; self.total_bytes = 0; self.rate = 0.0
            self.phase = "preparing"; self.results = []; self.started = time.monotonic(); self.finished = None

    def _line(self, line):
        line = line.strip()
        if not line: return
        with self.lock:
            if line.startswith("PROGRESS="):
                fields = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in line.split() if "=" in p}
                try: self.percent = float(fields.get("PROGRESS", "").rstrip("%"))
                except ValueError: pass
                try: self.downloaded = int(fields.get("DOWNLOADED", self.downloaded))
                except ValueError: pass
                try: self.total_bytes = int(fields.get("TOTAL", self.total_bytes))
                except ValueError: pass
                try: self.rate = float(fields.get("RATE", self.rate))
                except ValueError: pass
            elif line.startswith("PHASE=") or line.startswith("STATUS="):
                self.phase = line.split("=", 1)[1].strip().lower()

    def _run(self, command):
        try:
            p = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError:
            return False
        if p.stdout:
            for line in p.stdout: self._line(line)
        return p.wait() == 0

    def start_models(self, rows):
        if self.active or not rows: return False
        rows = list(rows); self._reset("models", "", len(rows))
        threading.Thread(target=self._models, args=(rows,), daemon=True).start(); return True

    def _models(self, rows):
        MODELS_DIR.mkdir(parents=True, exist_ok=True); results = []
        for i, row in enumerate(rows, 1):
            model = row.get("model_id", "?")
            with self.lock: self.index = i; self.item = model; self.label = model; self.phase = "downloading"; self.percent = None; self.downloaded = 0; self.total_bytes = 0; self.rate = 0.0
            ok = self._run([sys.executable, str(INSTALLER), "--model-id", model, "--output-dir", str(MODELS_DIR)])
            results.append((model, ok))
            with self.lock: self.results = list(results)
        self._finish(results)

    def start_software(self, components):
        if self.active or not components: return False
        components = list(components); self._reset("software", "", len(components))
        threading.Thread(target=self._software, args=(components,), daemon=True).start(); return True

    def _software(self, components):
        results = []
        for i, component in enumerate(components, 1):
            label = next((n for k, n in SOFTWARE if k == component), component)
            with self.lock: self.index = i; self.item = label; self.label = label; self.phase = "installing"; self.percent = None; self.downloaded = 0; self.total_bytes = 0; self.rate = 0.0
            ok = self._run(["bash", str(INSTALL_SH), f"--{component}"])
            results.append((label, ok))
            with self.lock: self.results = list(results)
        self._finish(results)

    def start_uninstall(self, components):
        if self.active or not components: return False
        components = list(components); self._reset("uninstall", "", len(components))
        threading.Thread(target=self._uninstall, args=(components,), daemon=True).start(); return True

    def _uninstall(self, components):
        results = []
        for i, component in enumerate(components, 1):
            label = next((n for k, n in SOFTWARE if k == component), component)
            with self.lock: self.index = i; self.item = label; self.label = label; self.phase = "uninstalling"; self.percent = None; self.downloaded = 0; self.total_bytes = 0; self.rate = 0.0
            ok = self._run(["bash", str(UNINSTALL_SH), "--yes", f"--{component}"])
            results.append((label, ok))
            with self.lock: self.results = list(results)
        self._finish(results)

    def _finish(self, results):
        with self.lock:
            self.active = False; self.phase = "completed" if all(x[1] for x in results) else "completed_with_errors"; self.finished = time.monotonic(); self.results = list(results)


def language_screen(scr):
    choices = (("es", "Español"), ("en", "English")); focus = 0
    while True:
        scr.erase(); h, w = scr.getmaxyx(); bw = min(64, max(42, w - 4)); x = max(1, (w - bw) // 2)
        box(scr, 3, x, 12, bw, "LEONES RC4")
        put(scr, 5, x + 4, "SELECCIONA IDIOMA / SELECT LANGUAGE", bw - 8)
        for i, (_, label) in enumerate(choices): put(scr, 8 + i, x + 8, f"{'>' if i == focus else ' '} [{i+1}] {label}", bw - 16)
        put(scr, 12, x + 4, "↑/↓ · ENTER · Q", bw - 8); scr.refresh(); key = scr.getch()
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % 2
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % 2
        elif key in (10, 13, ord("1"), ord("2")):
            if key in (ord("1"), ord("2")): focus = int(chr(key)) - 1
            return choices[focus][0]
        elif key in (ord("q"), ord("Q"), 27): raise SystemExit(0)


def confirm(scr, lang, title, question):
    h, w = scr.getmaxyx(); bw = min(90, w - 6); x = max(2, (w - bw) // 2); y = max(4, h // 2 - 3)
    box(scr, y, x, 7, bw, title); put(scr, y + 2, x + 3, question, bw - 6); put(scr, y + 4, x + 3, "[Y] sí    [N/ESC] no" if lang == "es" else "[Y] yes    [N/ESC] no", bw - 6); scr.refresh()
    while True:
        k = scr.getch()
        if k in (ord("y"), ord("Y")): return True
        if k in (ord("n"), ord("N"), 27): return False


def draw_frame(scr, lang, panel, focus_zone, task, nav_index):
    scr.erase(); h, w = scr.getmaxyx();
    if h < 25 or w < 96:
        put(scr, 1, 2, "LEONES RC4 — terminal demasiado pequeña (mín. 96x25)", w - 4); scr.refresh(); return False
    title = "LEONES // CENTRO DE CONTROL RC4"
    put(scr, 0, max(2, (w - len(title)) // 2), title, len(title))
    box(scr, 1, 1, h - 3, w - 2, "LEONES RC4")
    nav_w = 25; box(scr, 3, 3, h - 7, nav_w, t(lang, "nav"))
    for i, (key, label) in enumerate(NAV):
        marker = ">" if i == nav_index else " "
        put(scr, 5 + i * 2, 6, f"{marker} [{i+1}] {label}", nav_w - 6)
    op_x = 30; op_w = w - op_x - 4; box(scr, 3, op_x, 7, op_w, t(lang, "ops"))
    snap = task.snapshot(); blink = int(time.monotonic() * 2) % 2 == 0
    if snap["active"]:
        activity = "●" if blink else "○"
        label = f"{snap['kind'].upper()} {snap['index']}/{snap['total_items']}: {snap['item']}"
        put(scr, 5, op_x + 3, f"{activity} {t(lang,'active')}  {label}", op_w - 6)
        put(scr, 6, op_x + 3, f"{progress_bar(snap['percent'])} {snap['percent']:5.1f}%" if snap["percent"] is not None else f"{progress_bar(None)}   -- %", op_w - 6)
        put(scr, 7, op_x + 3, f"{t(lang,'phase').upper()}: {snap['phase']}   {t(lang,'data').upper()}: {human_bytes(snap['downloaded'])}   {t(lang,'rate').upper()}: {human_bytes(snap['rate'])}/s", op_w - 6)
        put(scr, 8, op_x + 3, f"{t(lang,'activity')}: {t(lang,'background')}", op_w - 6)
    else:
        status = snap["phase"] if snap["phase"] != "idle" else t(lang, "idle")
        put(scr, 5, op_x + 3, f"○ {status.upper()}", op_w - 6)
        if snap["results"]:
            ok = sum(1 for x in snap["results"] if x[1]); put(scr, 6, op_x + 3, f"{t(lang,'finished')}: {ok}/{len(snap['results'])}", op_w - 6)
        put(scr, 7, op_x + 3, t(lang, "home"), op_w - 6)
    # Key hints are deliberately duplicated top/bottom so they are always visible.
    hint = f"TAB={t(lang,'tab')} | {t(lang,'move')} | ENTER={t(lang,'open')} | {t(lang,'back')} | {t(lang,'quit')}"
    put(scr, 2, 32, hint, op_w - 4)
    put(scr, h - 2, 4, f"{t(lang,'focus_nav') if focus_zone == 'nav' else t(lang,'focus_content')} | {hint}", w - 8)
    return True


def home_panel(scr, lang, task):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, "INICIO")
    put(scr, 15, x + 3, t(lang, "home"), width - 6)
    put(scr, 17, x + 3, "1 Estado   2 Recomendador   3 LLMs   4 Software IA   5 Desinstalación", width - 6)
    put(scr, 19, x + 3, "TAB cambia el foco entre navegación y contenido.", width - 6)


def state_panel(scr, lang):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, t(lang, "machine"))
    used, total, mp = memory_stats(); du, dt, dp = disk_stats(); cpu, cores, gpu = hardware(); inv = inventory(); mods = local_models(); ag = agents()
    put(scr, 14, x + 3, t(lang, "hardware"), width - 6); put(scr, 15, x + 3, f"CPU  {cpu} ({cores})", width - 6); put(scr, 16, x + 3, f"GPU  {gpu}", width - 6)
    put(scr, 18, x + 3, t(lang, "resources"), width - 6); put(scr, 19, x + 3, f"RAM  {human_bytes(used)} / {human_bytes(total)} [{mp}%]", width - 6); put(scr, 20, x + 3, f"CPU  {cpu_percent()}%", width - 6); put(scr, 21, x + 3, f"DISCO {human_bytes(du)} / {human_bytes(dt)} [{dp}%]", width - 6)
    put(scr, 23, x + 3, f"{t(lang,'software_installed')}: ", width - 6); row = 24
    for c in inv.get("components", []):
        if c.get("installed") and row < h - 5: put(scr, row, x + 3, f"● {c.get('display_name', c.get('component_id','?'))}", width - 6); row += 1
    if row < h - 5: put(scr, row, x + 3, f"● {t(lang,'models_local')}: {len(mods)} :: {', '.join(mods) if mods else t(lang,'none')}", width - 6); row += 1
    if row < h - 5: put(scr, row, x + 3, f"● {t(lang,'agents')}: {len(ag)} :: {', '.join(ag) if ag else t(lang,'none')}", width - 6)


def intent_screen(scr, lang):
    selected = set(); focus = 0
    while True:
        scr.erase(); h, w = scr.getmaxyx(); box(scr, 2, 2, h - 4, w - 4, t(lang, "intent")); put(scr, 4, 6, "Selecciona uno o varios propósitos / Select one or more purposes", w - 12)
        for i, (key, label) in enumerate(PURPOSES): put(scr, 6 + i, 8, f"{'>' if i == focus else ' '} [{'X' if key in selected else ' '}] [{i+1}] {label}", w - 16)
        put(scr, h - 3, 4, f"{t(lang,'select')} | ↑/↓ | ENTER", w - 8); scr.refresh(); k = scr.getch()
        if k in (curses.KEY_UP, ord('k')): focus = (focus - 1) % len(PURPOSES)
        elif k in (curses.KEY_DOWN, ord('j')): focus = (focus + 1) % len(PURPOSES)
        elif k == ord(' '): selected.symmetric_difference_update({PURPOSES[focus][0]})
        elif k in (10, 13) and selected: return [p for p, _ in PURPOSES if p in selected]
        elif k in (27, ord('q'), ord('Q')): return []


def recommend(purposes):
    cmd = [sys.executable, str(RECOMMENDER), "--json"]
    for p in purposes: cmd += ["--purpose", p]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120, check=False); data = json.loads(r.stdout); return data.get("status", "error"), data
    except Exception as exc: return "error", {"message": str(exc)}


def recommendation_panel(scr, lang, task, state, focus_zone):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, t(lang, "recommendation"))
    result = state.get("result")
    if result is None: put(scr, 15, x + 3, t(lang, "recommend_now"), width - 6); return
    rows = result.get("recommendations") or []; put(scr, 14, x + 3, f"STATUS: {state.get('status','').upper()}   INTENT: {', '.join(state.get('purposes', []))}", width - 6); put(scr, 15, x + 3, t(lang, "estimated"), width - 6)
    for i, row in enumerate(rows[:3]): put(scr, 17 + i, x + 3, f"{'>' if i == state.get('focus',0) else ' '} [{'X' if i in state.get('selected',set()) else ' '}] [{i+1}] {row.get('model_id','?')}", width - 6)
    put(scr, h - 5, x + 3, f"{t(lang,'select')} | 1-3 alternar | ENTER {t(lang,'install').lower()} | R repetir", width - 6)


def model_panel(scr, lang, state):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, "LLMs / INSTALACIÓN")
    mods = local_models(); put(scr, 14, x + 3, f"{t(lang,'models_local')}: {len(mods)}", width - 6); row = 16
    for m in mods[:max(1, h - 21)]: put(scr, row, x + 3, f"● {m}", width - 6); row += 1
    put(scr, h - 5, x + 3, "R repetir recomendación", width - 6)


def software_panel(scr, lang, state):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, "SOFTWARE IA")
    selected = state.setdefault("selected", set()); focus = state.get("focus", 0)
    put(scr, 14, x + 3, t(lang, "software_select"), width - 6)
    for i, (key, label) in enumerate(SOFTWARE): put(scr, 17 + i, x + 6, f"{'>' if i == focus else ' '} [{'X' if i in selected else ' '}] [{i+1}] {label}", width - 12)
    put(scr, h - 5, x + 3, f"{t(lang,'select')} | 1-5 alternar | ENTER {t(lang,'install').lower()} | D {t(lang,'uninstall').lower()}", width - 6)


def uninstall_panel(scr, lang, state):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, "DESINSTALACIÓN")
    inv = inventory(); comps = [c for c in inv.get("components", []) if c.get("installed") and c.get("uninstallable") and not c.get("offer_last")]
    selected = state.setdefault("selected", set()); focus = state.get("focus", 0)
    if not comps: put(scr, 15, x + 3, t(lang, "no_installed"), width - 6)
    else:
        put(scr, 14, x + 3, t(lang, "uninstall_select"), width - 6)
        for i, c in enumerate(comps[:8]): put(scr, 17 + i, x + 6, f"{'>' if i == focus else ' '} [{'X' if i in selected else ' '}] [{i+1}] {c.get('display_name', c.get('component_id','?'))}", width - 12)
    put(scr, h - 5, x + 3, f"{t(lang,'select')} | 1-n alternar | ENTER {t(lang,'uninstall').lower()}", width - 6)
    return comps


def operation_panel(scr, lang, task):
    h, w = scr.getmaxyx(); x = 30; width = w - x - 4; box(scr, 12, x, h - 14, width, t(lang, "details")); s = task.snapshot()
    put(scr, 15, x + 3, f"{s['kind'].upper()} :: {s['label']}", width - 6); put(scr, 17, x + 3, f"ELEMENTO {s['index']}/{s['total_items']}: {s['item']}", width - 6)
    put(scr, 19, x + 3, f"{progress_bar(s['percent'],40)} {s['percent']:5.1f}%" if s['percent'] is not None else f"{progress_bar(None,40)}   -- %", width - 6)
    put(scr, 20, x + 3, f"{t(lang,'data').upper()}: {human_bytes(s['downloaded'])} / {human_bytes(s['total_bytes'])}   {t(lang,'rate').upper()}: {human_bytes(s['rate'])}/s", width - 6)
    put(scr, 22, x + 3, f"{t(lang,'phase').upper()}: {s['phase']}", width - 6); put(scr, 24, x + 3, t(lang,'ok') if s['results'] and all(x[1] for x in s['results']) else (t(lang,'error') if s['results'] else t(lang,'background')), width - 6)


def run_app(scr):
    scr.keypad(True); scr.timeout(200); lang = language_screen(scr)
    # Visible terminal cursor is part of the permanent TUI contract.
    try: curses.curs_set(1)
    except curses.error: pass
    task = TaskManager(lang); panel = "home"; nav_index = 0; focus_zone = "nav"; content_focus = 0
    rec = {"result": None, "status": "", "purposes": [], "selected": set(), "focus": 0}
    software = {"selected": set(), "focus": 0}; uninstall = {"selected": set(), "focus": 0}
    while True:
        active_key = panel if panel in {k for k, _ in NAV} else NAV[nav_index][0]
        if not draw_frame(scr, lang, active_key, focus_zone, task, nav_index):
            scr.getch(); continue
        if panel == "home": home_panel(scr, lang, task)
        elif panel == "state": state_panel(scr, lang)
        elif panel == "recommend": recommendation_panel(scr, lang, task, rec, focus_zone)
        elif panel == "models": model_panel(scr, lang, rec)
        elif panel == "software": software_panel(scr, lang, software)
        elif panel == "uninstall": uninstall_panel(scr, lang, uninstall)
        elif panel == "operation": operation_panel(scr, lang, task)
        # Always put the real terminal cursor on the active control; terminal decides blink rate.
        cursor_y = 5 + nav_index * 2 if focus_zone == "nav" else max(13, 15 + content_focus)
        cursor_x = 6 if focus_zone == "nav" else 33
        try: scr.move(min(scr.getmaxyx()[0] - 2, cursor_y), min(scr.getmaxyx()[1] - 2, cursor_x))
        except curses.error: pass
        scr.refresh(); key = scr.getch()
        if key == -1: continue
        if key in (ord('q'), ord('Q')): return
        if key == 9:
            focus_zone = "content" if focus_zone == "nav" else "nav"; continue
        if key in (27,) and panel != "home": panel = "home"; focus_zone = "nav"; continue

        if focus_zone == "nav":
            if key in (curses.KEY_UP, ord('k')): nav_index = (nav_index - 1) % len(NAV); panel = NAV[nav_index][0]
            elif key in (curses.KEY_DOWN, ord('j')): nav_index = (nav_index + 1) % len(NAV); panel = NAV[nav_index][0]
            elif ord('1') <= key <= ord('6'):
                nav_index = int(chr(key)) - 1; panel = NAV[nav_index][0]
            elif key in (10, 13): panel = NAV[nav_index][0]; focus_zone = "content"
            continue

        # Content focus/actions.
        if panel == "home":
            if key in (curses.KEY_UP, ord('k')): nav_index = (nav_index - 1) % len(NAV); panel = NAV[nav_index][0]
            elif key in (curses.KEY_DOWN, ord('j')): nav_index = (nav_index + 1) % len(NAV); panel = NAV[nav_index][0]
            elif key in (10, 13): focus_zone = "nav"
        elif panel == "recommend":
            rows = (rec.get("result") or {}).get("recommendations") or []; n = min(3, len(rows))
            if key in (curses.KEY_UP, ord('k')) and n: rec['focus'] = (rec['focus'] - 1) % n; content_focus = rec['focus']
            elif key in (curses.KEY_DOWN, ord('j')) and n: rec['focus'] = (rec['focus'] + 1) % n; content_focus = rec['focus']
            elif key == ord(' ') and n: rec['selected'].symmetric_difference_update({rec['focus']})
            elif ord('1') <= key <= ord('3') and n:
                i = int(chr(key)) - 1
                if i < n: rec['selected'].symmetric_difference_update({i}); rec['focus'] = i
            elif key in (ord('r'), ord('R')) and rec['purposes']:
                rec['status'], rec['result'] = recommend(rec['purposes']); rec['selected'] = set(); rec['focus'] = 0
            elif key in (10, 13):
                if rec['result'] is None:
                    purposes = intent_screen(scr, lang)
                    if purposes: rec['purposes'] = purposes; rec['status'], rec['result'] = recommend(purposes)
                elif rec['selected'] and not task.active:
                    chosen = [rows[i] for i in sorted(rec['selected'])]
                    if confirm(scr, lang, t(lang,'confirm'), t(lang,'confirm_install')): task.start_models(chosen); panel = 'operation'
        elif panel == "models":
            if key in (ord('r'), ord('R')):
                purposes = intent_screen(scr, lang)
                if purposes: rec['purposes'] = purposes; rec['status'], rec['result'] = recommend(purposes); rec['selected'] = set(); panel = 'recommend'
        elif panel == "software":
            if key in (curses.KEY_UP, ord('k')): software['focus'] = (software['focus'] - 1) % len(SOFTWARE); content_focus = software['focus']
            elif key in (curses.KEY_DOWN, ord('j')): software['focus'] = (software['focus'] + 1) % len(SOFTWARE); content_focus = software['focus']
            elif key == ord(' '): software['selected'].symmetric_difference_update({software['focus']})
            elif ord('1') <= key <= ord('5'):
                i = int(chr(key)) - 1; software['selected'].symmetric_difference_update({i}); software['focus'] = i; content_focus = i
            elif key in (10, 13) and software['selected'] and not task.active:
                components = [SOFTWARE[i][0] for i in sorted(software['selected'])]
                if confirm(scr, lang, t(lang,'confirm'), t(lang,'confirm_install')): task.start_software(components); software['selected'] = set(); panel = 'operation'
            elif key in (ord('d'), ord('D')): panel = 'uninstall'; focus_zone = 'content'; uninstall['selected'] = set(); uninstall['focus'] = 0
        elif panel == "uninstall":
            comps = [c for c in inventory().get('components', []) if c.get('installed') and c.get('uninstallable') and not c.get('offer_last')]
            if comps:
                n = min(8, len(comps))
                if key in (curses.KEY_UP, ord('k')): uninstall['focus'] = (uninstall['focus'] - 1) % n; content_focus = uninstall['focus']
                elif key in (curses.KEY_DOWN, ord('j')): uninstall['focus'] = (uninstall['focus'] + 1) % n; content_focus = uninstall['focus']
                elif key == ord(' '): uninstall['selected'].symmetric_difference_update({uninstall['focus']})
                elif ord('1') <= key <= ord('8'):
                    i = int(chr(key)) - 1
                    if i < n: uninstall['selected'].symmetric_difference_update({i}); uninstall['focus'] = i
                elif key in (10, 13) and uninstall['selected'] and not task.active:
                    components = [comps[i]['component_id'] for i in sorted(uninstall['selected'])]
                    if confirm(scr, lang, t(lang,'confirm'), t(lang,'confirm_uninstall')): task.start_uninstall(components); uninstall['selected'] = set(); panel = 'operation'
        elif panel == "operation":
            if key in (ord('b'), ord('B'), 27): panel = 'home'; focus_zone = 'nav'


def main():
    return curses.wrapper(run_app) or 0


if __name__ == "__main__":
    raise SystemExit(main())
