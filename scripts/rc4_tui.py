#!/usr/bin/env python3
"""LEONES RC4 persistent control-center TUI.

Long operations run in the background.  Software installation supports
multi-selection and there is a separate multi-selection uninstall screen.
The recommender remains ESTIMATED and never authorizes execution.
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
            ("magnitude", "Magnitude"), ("hermes", "Hermes"),
            ("omh", "OMH"))


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
            p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                                "--format=csv,noheader"], capture_output=True,
                               text=True, timeout=5, check=False)
            if p.returncode == 0 and p.stdout.strip():
                gpu = p.stdout.strip().replace("\n", "; ")
        except (OSError, subprocess.TimeoutExpired):
            pass
    return cpu, os.cpu_count() or 1, gpu


def inventory():
    try:
        p = subprocess.run([sys.executable, str(INVENTORY), "--json"], cwd=ROOT,
                           capture_output=True, text=True, timeout=20, check=False)
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
    return sorted(p.name for p in MODELS_DIR.iterdir()
                  if p.is_dir() and not p.name.startswith(".")
                  and (p / ".leones-installed.json").is_file())


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
    """One background worker; the curses main loop remains responsive."""
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
            return {"active": self.active, "kind": self.kind, "label": self.label,
                    "model_index": self.model_index, "model_total": self.model_total,
                    "model": self.model, "percent": self.percent,
                    "downloaded": self.downloaded, "total": self.total,
                    "rate": self.rate, "phase": self.phase,
                    "lines": list(self.lines), "results": list(self.results),
                    "finished_at": self.finished_at}

    def _reset(self, kind, label):
        with self.lock:
            self.active = True; self.kind = kind; self.label = label
            self.model_index = 0; self.model_total = 0; self.model = ""
            self.percent = None; self.downloaded = 0; self.total = 0; self.rate = 0.0
            self.phase = "preparing"; self.lines = []; self.results = []; self.finished_at = None

    def _line(self, line):
        line = line.strip()
        if not line:
            return
        with self.lock:
            self.lines = (self.lines + [line])[-5:]
            if line.startswith("PROGRESS="):
                fields = dict(part.split("=", 1) for part in line.split() if "=" in part)
                try: self.percent = float(fields.get("PROGRESS", "").rstrip("%"))
                except ValueError: self.percent = None
                try: self.downloaded = int(fields.get("DOWNLOADED", self.downloaded))
                except ValueError: pass
                try: self.total = int(fields.get("TOTAL", self.total))
                except ValueError: pass
                try: self.rate = float(fields.get("RATE", self.rate))
                except ValueError: pass
            elif line.startswith("PHASE="):
                self.phase = line.split("=", 1)[1]
            elif line.startswith("STATUS="):
                self.phase = line.split("=", 1)[1]

    def _run_process(self, command, model_index=0, model_total=0, model=""):
        with self.lock:
            self.model_index = model_index; self.model_total = model_total
            self.model = model; self.phase = "running"
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError as exc:
            self._line(f"ERROR={exc}"); return False
        if process.stdout is not None:
            for line in process.stdout:
                self._line(line)
        rc = process.wait()
        self._line(f"RETURN_CODE={rc}")
        return rc == 0

    def _finish(self, phase, results):
        with self.lock:
            self.phase = phase; self.active = False; self.finished_at = time.monotonic()
            self.results = list(results)

    def start_models(self, rows):
        if self.is_active() or not rows: return False
        rows = list(rows); self._reset("models", f"Instalación de {len(rows)} modelo(s)")
        self.thread = threading.Thread(target=self._models_worker, args=(rows,), daemon=True)
        self.thread.start(); return True

    def _models_worker(self, rows):
        MODELS_DIR.mkdir(parents=True, exist_ok=True); results = []
        for index, row in enumerate(rows, 1):
            model_id = row.get("model_id", "?")
            with self.lock:
                self.model_index = index; self.model_total = len(rows); self.model = model_id
                self.phase = "downloading"; self.percent = None; self.downloaded = 0
                self.total = 0; self.rate = 0.0; self.lines = []
            ok = self._run_process([sys.executable, str(INSTALLER), "--model-id", model_id,
                                    "--output-dir", str(MODELS_DIR)], index, len(rows), model_id)
            results.append((model_id, ok, " | ".join(self.snapshot()["lines"][-2:])))
            with self.lock: self.results = list(results)
        self._finish("completed" if all(x[1] for x in results) else "completed_with_errors", results)

    def start_software(self, components):
        if self.is_active() or not components: return False
        components = list(components)
        labels = [name for key, name in SOFTWARE if key in components]
        self._reset("software", f"Instalación de {', '.join(labels)}")
        self.thread = threading.Thread(target=self._software_worker, args=(components,), daemon=True)
        self.thread.start(); return True

    def _software_worker(self, components):
        results = []
        for index, component in enumerate(components, 1):
            label = next((n for k, n in SOFTWARE if k == component), component)
            with self.lock:
                self.model_index = index; self.model_total = len(components); self.model = label
                self.phase = "installing"; self.percent = None; self.downloaded = 0
                self.total = 0; self.rate = 0.0; self.lines = []
            ok = self._run_process(["bash", str(INSTALL_SH), f"--{component}"], index, len(components), label)
            results.append((component, ok, " | ".join(self.snapshot()["lines"][-3:])))
            with self.lock: self.results = list(results)
        self._finish("completed" if all(x[1] for x in results) else "completed_with_errors", results)

    def start_uninstall(self, components):
        if self.is_active() or not components: return False
        components = list(dict.fromkeys(components))
        labels = [name for key, name in SOFTWARE if key in components]
        self._reset("uninstall", f"Desinstalación de {', '.join(labels)}")
        self.thread = threading.Thread(target=self._uninstall_worker, args=(components,), daemon=True)
        self.thread.start(); return True

    def _uninstall_worker(self, components):
        command = ["bash", str(UNINSTALL_SH), "--yes"]
        command += [f"--{component}" for component in components]
        ok = self._run_process(command)
        self._finish("completed" if ok else "failed",
                     [(", ".join(components), ok, " | ".join(self.snapshot()["lines"][-3:]))])

    def is_active(self):
        with self.lock: return self.active


NAV = (("home", "INICIO"), ("state", "ESTADO"), ("recommend", "RECOMENDADOR"),
       ("models", "LLMs / INSTALACIÓN"), ("software", "SOFTWARE IA"))


def draw_shell(stdscr, active_key, task):
    stdscr.erase(); h, w = stdscr.getmaxyx()
    if h < 25 or w < 96:
        put(stdscr, 1, 2, "LEONES RC4 — terminal demasiado pequeña (mín. 96x25)", w - 4)
        stdscr.refresh(); return False
    title = "LEONES // CENTRO DE CONTROL RC4"
    put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title))
    box(stdscr, 1, 1, h - 3, w - 2, "LEONES RC4")
    nav_w = 25; box(stdscr, 3, 3, h - 7, nav_w, "NAVEGACIÓN")
    for i, (key, label) in enumerate(NAV):
        put(stdscr, 5 + i * 2, 6, f"{'>' if key == active_key else ' '} [{i+1}] {label}", nav_w - 6)
    put(stdscr, h - 5, 6, "↑/↓ mover", nav_w - 6); put(stdscr, h - 4, 6, "ENTER abrir", nav_w - 6)
    put(stdscr, h - 3, 6, "Q salir", nav_w - 6)
    op_x = 30; op_w = w - op_x - 4
    box(stdscr, 3, op_x, 7, op_w, "OPERACIÓN EN SEGUNDO PLANO")
    snap = task.snapshot()
    if snap["active"]:
        label = snap["label"]
        if snap["model_total"]: label = f"{snap['kind'].upper()} {snap['model_index']}/{snap['model_total']}: {snap['model']}"
        put(stdscr, 5, op_x + 3, f"● ACTIVA  {label}", op_w - 6)
        put(stdscr, 6, op_x + 3, f"{progress_bar(snap['percent'])} {snap['percent']:5.1f}%" if snap['percent'] is not None else progress_bar(None), op_w - 6)
        put(stdscr, 7, op_x + 3, f"FASE: {snap['phase']}   DATOS: {human_bytes(snap['downloaded'])}   VELOCIDAD: {human_bytes(snap['rate'])}/s", op_w - 6)
        put(stdscr, 8, op_x + 3, "La navegación permanece disponible mientras la operación continúa.", op_w - 6)
    else:
        put(stdscr, 5, op_x + 3, f"○ {(snap['phase'] if snap['phase'] != 'idle' else 'sin operaciones').upper()}", op_w - 6)
        if snap["results"]: put(stdscr, 6, op_x + 3, f"Último resultado: {sum(1 for x in snap['results'] if x[1])}/{len(snap['results'])} correctas", op_w - 6)
        put(stdscr, 7, op_x + 3, "El centro de control sigue disponible.", op_w - 6)
    return True


def language_screen(stdscr):
    focus = 0
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx(); bw = min(64, max(40, w - 4)); x = max(1, (w-bw)//2)
        box(stdscr, 3, x, 11, bw, "LEONES RC4"); put(stdscr, 5, x+4, "SELECCIONA IDIOMA", bw-8)
        for i, label in enumerate(("Español", "English")): put(stdscr, 8+i, x+8, f"{'>' if i==focus else ' '} [{i+1}] {label}", bw-16)
        put(stdscr, 12, x+4, "↑/↓ · ENTER", bw-8); stdscr.refresh(); key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')): focus = (focus-1)%2
        elif key in (curses.KEY_DOWN, ord('j')): focus = (focus+1)%2
        elif key in (10,13,ord('1'),ord('2')): return 'es' if (key==ord('1') or (key not in (ord('2'),) and focus==0)) else 'en'
        elif key in (27,ord('q'),ord('Q')): raise SystemExit(0)


def state_panel(stdscr):
    h,w=stdscr.getmaxyx(); x=30; width=w-x-4; used,total,mp=memory_stats(); du,dt,dp=disk_stats(); cpu,cores,gpu=hardware(); inv=inventory(); names=agents(); models=local_models()
    box(stdscr,12,x,h-14,width,"ESTADO DE LA MÁQUINA"); put(stdscr,14,x+3,"HARDWARE",width-6); put(stdscr,15,x+3,f"CPU  {cpu} ({cores} logical CPUs)",width-6); put(stdscr,16,x+3,f"GPU  {gpu}",width-6)
    put(stdscr,18,x+3,"RECURSOS EN USO",width-6); put(stdscr,19,x+3,f"RAM  {human_bytes(used)} / {human_bytes(total)} [{mp}%]",width-6); put(stdscr,20,x+3,f"CPU  {cpu_percent()}%",width-6); put(stdscr,21,x+3,f"DISCO {human_bytes(du)} / {human_bytes(dt)} [{dp}%]",width-6)
    put(stdscr,23,x+3,"SOFTWARE IA INSTALADO",width-6); row=24
    for c in inv.get('components',[]):
        if c.get('installed') and row<h-4: put(stdscr,row,x+3,f"● {c.get('display_name',c.get('component_id','?'))}",width-6); row+=1
    if row<h-4: put(stdscr,row,x+3,f"● Agentes ({len(names)}) :: {', '.join(names) if names else 'ninguno'}",width-6); row+=1
    if row<h-4: put(stdscr,row,x+3,f"● LLMs locales ({len(models)}) :: {', '.join(models) if models else 'ninguno instalado'}",width-6)


def home_panel(stdscr):
    h,w=stdscr.getmaxyx(); x=30; width=w-x-4; box(stdscr,12,x,h-14,width,"PANEL PRINCIPAL")
    put(stdscr,15,x+3,"LEONES coordina selección, instalación y estado sin bloquear la interfaz.",width-6)
    put(stdscr,17,x+3,"1  Estado de la máquina",width-6); put(stdscr,18,x+3,"2  Recomendador RC4 (intención múltiple)",width-6)
    put(stdscr,19,x+3,"3  LLMs / instalación",width-6); put(stdscr,20,x+3,"4  Software IA",width-6)
    put(stdscr,22,x+3,"Mientras una operación está activa, la navegación sigue disponible.",width-6)


def recommend(purposes):
    command=[sys.executable,str(RECOMMENDER),'--json']
    for purpose in purposes: command += ['--purpose',purpose]
    try:
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120,check=False); data=json.loads(p.stdout)
        return data.get('status','error'),data
    except Exception as exc: return 'error',{'message':str(exc)}


def intent_screen(stdscr):
    selected=set(); focus=0
    while True:
        stdscr.erase(); h,w=stdscr.getmaxyx(); title="LEONES // INTENCIÓN DE USO"; put(stdscr,0,max(2,(w-len(title))//2),title,len(title)); box(stdscr,1,1,h-4,w-2,"USER INTENT[] — MULTI SELECT — REQUIRED")
        put(stdscr,3,4,"Selecciona uno o varios propósitos. ENTER recomienda.",w-8)
        for i,(key,label) in enumerate(PURPOSES): put(stdscr,5+i,6,f"{'>' if i==focus else ' '} [{'X' if key in selected else ' '}] {i+1}. {label}",w-12)
        put(stdscr,h-2,2,"ESPACIO seleccionar   ENTER recomendar   Q salir",w-4); stdscr.refresh(); key=stdscr.getch()
        if key in (curses.KEY_UP,ord('k')): focus=(focus-1)%len(PURPOSES)
        elif key in (curses.KEY_DOWN,ord('j')): focus=(focus+1)%len(PURPOSES)
        elif key==ord(' '):
            name=PURPOSES[focus][0]; selected.symmetric_difference_update({name})
        elif key in (10,13) and selected: return [p for p,_ in PURPOSES if p in selected]
        elif key in (27,ord('q'),ord('Q')): raise SystemExit(0)


def confirm_screen(stdscr,title,rows,verb):
    while True:
        stdscr.erase(); h,w=stdscr.getmaxyx(); put(stdscr,0,max(2,(w-len(title))//2),title,len(title)); box(stdscr,2,1,h-6,w-2,"CONSENTIMIENTO EXPLÍCITO")
        put(stdscr,4,5,f"ELEMENTOS SELECCIONADOS: {len(rows)}",w-10)
        for i,row in enumerate(rows[:8]): put(stdscr,6+i,5,f"[{i+1}] {row}",w-10)
        put(stdscr,h-4,5,f"¿Confirmar {verb} de TODOS? [Y] sí  [N/ESC] cancelar",w-10); stdscr.refresh(); key=stdscr.getch()
        if key in (ord('y'),ord('Y')): return True
        if key in (ord('n'),ord('N'),27): return False


def recommendation_panel(stdscr,recommendation):
    h,w=stdscr.getmaxyx(); x=30; width=w-x-4; box(stdscr,12,x,h-14,width,"FITLLM / LLMFIT + EVIDENCE")
    if recommendation.get('result') is None: put(stdscr,15,x+3,"No hay recomendación cargada. ENTER para iniciar.",width-6); return
    result=recommendation['result']; rows=result.get('recommendations') or []; put(stdscr,14,x+3,f"STATUS: {recommendation.get('status','error').upper()}",width-6); put(stdscr,15,x+3,f"INTENT: {', '.join(recommendation.get('purposes',[]))}",width-6); put(stdscr,16,x+3,f"CANDIDATES: {result.get('candidate_count',0)}/3",width-6); put(stdscr,17,x+3,"KIND: ESTIMATED   EXECUTION_AUTHORIZED: False",width-6); put(stdscr,18,x+3,"MEASUREMENT_AUTHORIZED: False   MEASURED: False",width-6)
    for i,row in enumerate(rows[:3]): put(stdscr,20+i,x+3,f"{'>' if i==recommendation.get('focus',0) else ' '} [{'X' if i in recommendation.get('selected',set()) else ' '}] [{i+1}] {row.get('model_id','?')} :: ESTIMATED",width-6)
    put(stdscr,h-5,x+3,"↑/↓ mover  SPACE marcar  1-3 marcar  ENTER instalar  R repetir",width-6)


def model_panel(stdscr,recommendation):
    h,w=stdscr.getmaxyx(); x=30; width=w-x-4; box(stdscr,12,x,h-14,width,"LLMs / INSTALACIÓN"); models=local_models(); rows=recommendation.get('result',{}).get('recommendations') or []
    put(stdscr,14,x+3,"MODELOS LOCALES",width-6)
    if models:
        for i,m in enumerate(models[:max(1,h-20)]): put(stdscr,16+i,x+3,f"● {m}",width-6)
    else: put(stdscr,16,x+3,"ningún modelo instalado",width-6)
    if rows: put(stdscr,19,x+3,"ÚLTIMA RECOMENDACIÓN",width-6); [put(stdscr,20+i,x+3,f"[{i+1}] {r.get('model_id','?')}",width-6) for i,r in enumerate(rows[:3])]
    put(stdscr,h-5,x+3,"R volver a recomendar   Q salir",width-6)


def software_select_screen(stdscr, installed_only=False):
    """Multi-select screen for install or uninstall; numbers also toggle."""
    selected=set(); focus=0
    while True:
        stdscr.erase(); h,w=stdscr.getmaxyx(); title="LEONES // DESINSTALACIÓN" if installed_only else "LEONES // SOFTWARE IA"
        put(stdscr,0,max(2,(w-len(title))//2),title,len(title)); box(stdscr,1,1,h-4,w-2,"MULTI SELECT")
        if installed_only:
            inv=inventory(); installed={c.get('component_id') for c in inv.get('components',[]) if c.get('installed')}
            items=[x for x in SOFTWARE if x[0] in installed]
            if not items:
                put(stdscr,5,5,"No hay componentes de Software IA instalados detectados.",w-10); put(stdscr,h-2,2,"ESC volver",w-4); stdscr.refresh(); key=stdscr.getch()
                if key in (27,ord('q'),ord('Q')): return []
                continue
        else: items=list(SOFTWARE)
        put(stdscr,3,4,"Selecciona uno o varios componentes:",w-8)
        for i,(_,label) in enumerate(items): put(stdscr,5+i,6,f"{'>' if i==focus else ' '} [{'X' if i in selected else ' '}] [{i+1}] {label}",w-12)
        put(stdscr,h-3,2,"ESPACIO/1-5 seleccionar   ENTER continuar   ESC volver",w-4); stdscr.refresh(); key=stdscr.getch()
        if key in (curses.KEY_UP,ord('k')): focus=(focus-1)%len(items)
        elif key in (curses.KEY_DOWN,ord('j')): focus=(focus+1)%len(items)
        elif key==ord(' '): selected.symmetric_difference_update({focus})
        elif ord('1')<=key<=ord('5'):
            i=int(chr(key))-1
            if i<len(items): focus=i; selected.symmetric_difference_update({i})
        elif key in (10,13) and selected: return [items[i][0] for i in sorted(selected)]
        elif key in (27,ord('q'),ord('Q')): return []


def software_panel(stdscr,software_state):
    h,w=stdscr.getmaxyx(); x=30; width=w-x-4; box(stdscr,12,x,h-14,width,"SOFTWARE IA")
    put(stdscr,14,x+3,"INSTALACIÓN",width-6); put(stdscr,15,x+3,"Selecciona uno o varios componentes para instalar en segundo plano:",width-6)
    selected=software_state.get('selected',set()); focus=software_state.get('focus',0)
    for i,(_,label) in enumerate(SOFTWARE): put(stdscr,17+i,x+6,f"{'>' if i==focus else ' '} [{'X' if i in selected else ' '}] [{i+1}] {label}",width-12)
    put(stdscr,24,x+3,"ENTER instalar seleccionados   D desinstalar   SPACE marcar   ↑/↓ mover",width-6)
    put(stdscr,h-5,x+3,"R reiniciar selección   Q salir",width-6)


def operation_panel(stdscr,task):
    snap=task.snapshot(); h,w=stdscr.getmaxyx(); x=30; width=w-x-4; box(stdscr,12,x,h-14,width,"DETALLE DE OPERACIÓN")
    put(stdscr,15,x+3,f"{snap['kind'].upper()} :: {snap['label']}",width-6)
    if snap['model_total']:
        put(stdscr,17,x+3,f"ELEMENTO {snap['model_index']}/{snap['model_total']}: {snap['model']}",width-6)
        if snap['percent'] is not None: put(stdscr,18,x+3,f"{progress_bar(snap['percent'],40)} {snap['percent']:5.1f}%",width-6)
        put(stdscr,19,x+3,f"DATOS: {human_bytes(snap['downloaded'])} / {human_bytes(snap['total'])}   VELOCIDAD: {human_bytes(snap['rate'])}/s",width-6)
    put(stdscr,21,x+3,f"FASE: {snap['phase']}",width-6)
    for i,line in enumerate(snap['lines'][-5:]): put(stdscr,23+i,x+3,line,width-6)
    put(stdscr,h-5,x+3,"B volver al panel anterior",width-6)


def run_app(stdscr):
    curses.curs_set(0); stdscr.keypad(True); stdscr.timeout(200); language=language_screen(stdscr); task=TaskManager(); nav_index=0; panel='home'
    recommendation={'result':None,'status':'','purposes':[],'selected':set(),'focus':0}
    software_state={'selected':set(),'focus':0}
    while True:
        active_key=panel if panel in {k for k,_ in NAV} else 'home'
        if not draw_shell(stdscr,active_key,task):
            if stdscr.getch() in (27,ord('q'),ord('Q')): return
            continue
        if panel=='home': home_panel(stdscr)
        elif panel=='state': state_panel(stdscr)
        elif panel=='recommend': recommendation_panel(stdscr,recommendation)
        elif panel=='models': model_panel(stdscr,recommendation)
        elif panel=='software': software_panel(stdscr,software_state)
        elif panel=='operation': operation_panel(stdscr,task)
        stdscr.refresh(); key=stdscr.getch()
        if key==-1: continue
        if key in (ord('q'),ord('Q'),27): return

        if panel=='recommend':
            rows=(recommendation.get('result') or {}).get('recommendations') or []
            if key in (curses.KEY_UP,ord('k')) and rows: recommendation['focus']=(recommendation['focus']-1)%min(3,len(rows))
            elif key in (curses.KEY_DOWN,ord('j')) and rows: recommendation['focus']=(recommendation['focus']+1)%min(3,len(rows))
            elif key==ord(' ') and rows: recommendation['selected'].symmetric_difference_update({recommendation['focus']})
            elif ord('1')<=key<=ord('3') and rows:
                i=int(chr(key))-1
                if i<len(rows): recommendation['focus']=i; recommendation['selected'].symmetric_difference_update({i})
            elif key in (ord('r'),ord('R')) and recommendation['purposes']:
                status,result=recommend(recommendation['purposes']); recommendation.update(status=status,result=result,selected=set(),focus=0)
            elif key in (10,13):
                if recommendation.get('result') is None:
                    purposes=intent_screen(stdscr); status,result=recommend(purposes); recommendation.update(status=status,result=result,purposes=purposes,selected=set(),focus=0)
                elif rows and recommendation['selected'] and not task.is_active():
                    chosen=[rows[i] for i in sorted(recommendation['selected'])]
                    if confirm_screen(stdscr,"LEONES // CONFIRMAR INSTALACIÓN",[r.get('model_id','?') for r in chosen],"instalación"): task.start_models(chosen); panel='operation'
            elif key in (curses.KEY_LEFT,ord('h'),curses.KEY_RIGHT,ord('l')): panel='home'
        elif panel=='software':
            items=list(SOFTWARE)
            if key in (curses.KEY_UP,ord('k')): software_state['focus']=(software_state['focus']-1)%len(items)
            elif key in (curses.KEY_DOWN,ord('j')): software_state['focus']=(software_state['focus']+1)%len(items)
            elif key==ord(' '): software_state['selected'].symmetric_difference_update({software_state['focus']})
            elif ord('1')<=key<=ord('5'):
                i=int(chr(key))-1
                if i<len(items): software_state['focus']=i; software_state['selected'].symmetric_difference_update({i})
            elif key in (ord('d'),ord('D')) and not task.is_active():
                components=software_select_screen(stdscr,True)
                if components and confirm_screen(stdscr,"LEONES // CONFIRMAR DESINSTALACIÓN",[dict(SOFTWARE)[c] for c in components],"desinstalación"): task.start_uninstall(components); panel='operation'
            elif key in (10,13) and software_state['selected'] and not task.is_active():
                components=[items[i][0] for i in sorted(software_state['selected'])]
                if confirm_screen(stdscr,"LEONES // CONFIRMAR INSTALACIÓN",[dict(SOFTWARE)[c] for c in components],"instalación"): task.start_software(components); software_state['selected']=set(); panel='operation'
            elif key in (ord('r'),ord('R')): software_state['selected']=set(); software_state['focus']=0
        elif panel=='models':
            if key in (ord('r'),ord('R')):
                purposes=intent_screen(stdscr); status,result=recommend(purposes); recommendation.update(status=status,result=result,purposes=purposes,selected=set(),focus=0); panel='recommend'
        elif panel=='operation':
            if key in (ord('b'),ord('B')): panel='home'

        if key in (ord('1'),ord('2'),ord('3'),ord('4'),ord('5')) and panel not in {'recommend','software'}:
            idx=int(chr(key))-1
            if idx<len(NAV): panel=NAV[idx][0]; nav_index=idx
        elif key in (curses.KEY_UP,ord('k')) and panel not in {'recommend','software'}:
            nav_index=(nav_index-1)%len(NAV); panel=NAV[nav_index][0]
        elif key in (curses.KEY_DOWN,ord('j')) and panel not in {'recommend','software'}:
            nav_index=(nav_index+1)%len(NAV); panel=NAV[nav_index][0]
        elif key in (10,13) and panel=='home': panel=NAV[nav_index][0]


def main():
    curses.wrapper(run_app); return 0


if __name__=='__main__': raise SystemExit(main())
