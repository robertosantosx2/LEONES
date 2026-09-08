#!/usr/bin/env python3
"""LEONES RC4 persistent TUI.

RC4 TUI usage model is deliberately explicit:
- the logical cursor is always visible on the focused item;
- SPACE changes selection, ENTER crosses the execution boundary;
- installed components are marked with a white bullet (•);
- privileged work is authorized inside curses before execution;
- long-running work is asynchronous and is only marked complete after exit.
"""
from __future__ import annotations

import curses
import getpass
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts/rc4_fitllm_recommend.py"
INSTALLER = ROOT / "scripts/rc4_model_install.py"
INSTALL_SH = ROOT / "install.sh"
UNINSTALL_SH = ROOT / "scripts/uninstall.sh"
MODELS_DIR = ROOT / "models"
PURPOSES = ("programming", "reasoning", "research", "chat", "multimodal", "embedding", "general")
SOFTWARE = ("fitllm", "ods", "magnitude", "hermes", "omh")
NAV_KEYS = ("home", "state", "intent", "recommend", "models", "software", "uninstall")
NAV = {
    "es": ("INICIO", "ESTADO", "INTENCIÓN", "RECOMENDADOR", "LLMs / INSTALACIÓN", "INST IA LOCAL", "DESINSTALACIÓN"),
    "en": ("HOME", "STATE", "INTENT", "RECOMMENDER", "LLMs / INSTALLATION", "LOCAL AI INST", "UNINSTALL"),
    "zh": ("首页", "状态", "意图", "推荐器", "LLM / 安装", "本地 AI", "卸载"),
}
PURPOSES_LABEL = {
    "es": {"programming":"Programación", "reasoning":"Razonamiento", "research":"Investigación", "chat":"Chat", "multimodal":"Multimodal", "embedding":"Embeddings", "general":"General"},
    "en": {"programming":"Programming", "reasoning":"Reasoning", "research":"Research", "chat":"Chat", "multimodal":"Multimodal", "embedding":"Embeddings", "general":"General"},
    "zh": {"programming":"编程", "reasoning":"推理", "research":"研究", "chat":"聊天", "multimodal":"多模态", "embedding":"嵌入", "general":"通用"},
}
SOFTWARE_LABEL = {"fitllm":"FitLLM", "ods":"ODS", "magnitude":"Magnitude", "hermes":"Hermes", "omh":"OMH"}
TEXT = {
    "es": {"nav":"NAVEGACIÓN", "activity":"ACTIVIDAD RC4 / OPERACIÓN / PROGRESO", "selection":"SELECCIÓN / INFORMACIÓN PRINCIPAL", "action":"ACCIÓN / ESCALADO / PRIVILEGIOS", "active":"ACTIVA", "idle":"SIN OPERACIONES", "phase":"FASE", "data":"DATOS", "rate":"VELOCIDAD", "tab":"TAB cambiar foco", "move":"↑/↓ mover", "enter":"ENTER ejecutar", "space":"SPACE seleccionar", "back":"ESC volver", "quit":"Q salir", "intent":"INTENCIÓN DE USO", "help":"Selecciona uno o varios propósitos", "details":"CARACTERÍSTICAS DE LA SELECCIÓN", "accept":"ACEPTACIÓN", "first":"Selecciona al menos un elemento con SPACE.", "confirm":"¿Confirmar ejecución? [Y] sí / [N] no", "authorize":"AUTORIZACIÓN DEL SISTEMA — sudo", "password":"Contraseña sudo: ", "auth_failed":"Autorización del sistema fallida. No se inicia la operación.", "recommend":"RECOMENDACIÓN RC4", "estimated":"ESTIMATED · ejecución no autorizada · medición no autorizada", "running":"Ejecutando recomendador RC4…", "done":"Operación finalizada", "failed":"Operación fallida", "machine":"ESTADO DE LA MÁQUINA", "cpu":"CPU", "logical":"CPU lógicas", "gpu":"GPU", "ram":"RAM ocupada/total", "disk":"DISCO ocupado/total", "llms":"LLMs locales", "none":"ninguno", "installed":"INSTALADO", "not_installed":"NO INSTALADO", "confirm_uninstall":"¿Confirmar DESINSTALACIÓN? [Y] sí / [N] no", "nothing_installed":"No hay componentes instalados para desinstalar."},
    "en": {"nav":"NAVIGATION", "activity":"RC4 ACTIVITY / OPERATION / PROGRESS", "selection":"SELECTION / MAIN INFORMATION", "action":"ACTION / ESCALATION / PRIVILEGES", "active":"ACTIVE", "idle":"NO OPERATIONS", "phase":"PHASE", "data":"DATA", "rate":"SPEED", "tab":"TAB switch focus", "move":"↑/↓ move", "enter":"ENTER execute", "space":"SPACE select", "back":"ESC back", "quit":"Q quit", "intent":"USE INTENT", "help":"Select one or more purposes", "details":"SELECTION CHARACTERISTICS", "accept":"ACCEPTANCE", "first":"Select at least one item with SPACE.", "confirm":"Confirm execution? [Y] yes / [N] no", "authorize":"SYSTEM AUTHORIZATION — sudo", "password":"sudo password: ", "auth_failed":"System authorization failed. Operation not started.", "recommend":"RC4 RECOMMENDATION", "estimated":"ESTIMATED · execution not authorized · measurement not authorized", "running":"Running RC4 recommender…", "done":"Operation finished", "failed":"Operation failed", "machine":"MACHINE STATE", "cpu":"CPU", "logical":"Logical CPUs", "gpu":"GPU", "ram":"RAM used/total", "disk":"DISK used/total", "llms":"Local LLMs", "none":"none", "installed":"INSTALLED", "not_installed":"NOT INSTALLED", "confirm_uninstall":"Confirm UNINSTALL? [Y] yes / [N] no", "nothing_installed":"No installed components available to uninstall."},
    "zh": {"nav":"导航", "activity":"RC4 活动 / 操作 / 进度", "selection":"选择 / 主要信息", "action":"操作 / 权限 / 授权", "active":"运行中", "idle":"无操作", "phase":"阶段", "data":"数据", "rate":"速度", "tab":"TAB 切换焦点", "move":"↑/↓ 移动", "enter":"ENTER 执行", "space":"SPACE 选择", "back":"ESC 返回", "quit":"Q 退出", "intent":"使用意图", "help":"选择一个或多个用途", "details":"选择特征", "accept":"确认", "first":"请使用 SPACE 选择至少一个项目。", "confirm":"确认执行？[Y] 是 / [N] 否", "authorize":"系统授权 — sudo", "password":"sudo 密码：", "auth_failed":"系统授权失败。未启动操作。", "recommend":"RC4 推荐", "estimated":"ESTIMATED · 未授权执行 · 未授权测量", "running":"正在运行 RC4 推荐器…", "done":"操作已完成", "failed":"操作失败", "machine":"机器状态", "cpu":"CPU", "logical":"逻辑 CPU", "gpu":"GPU", "ram":"RAM 已用/总量", "disk":"磁盘 已用/总量", "llms":"本地 LLM", "none":"无", "installed":"已安装", "not_installed":"未安装", "confirm_uninstall":"确认卸载？[Y] 是 / [N] 否", "nothing_installed":"没有可卸载的已安装组件。"},
}


def tr(lang, key):
    return TEXT[lang].get(key, key)


def human(value):
    n = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024


def bar(percent, width=34):
    if percent is None:
        return "[" + "." * width + "]"
    n = max(0, min(width, round(width * float(percent) / 100)))
    return "[" + "#" * n + "." * (width - n) + "]"


def put(s, y, x, text, width):
    if y < 0 or y >= s.getmaxyx()[0] or width <= 0:
        return
    try:
        s.addnstr(y, max(0, x), str(text), width)
    except curses.error:
        pass


def box(s, y, x, h, w, title=""):
    if h < 3 or w < 4:
        return
    try:
        s.addstr(y, x, "+" + "-" * (w - 2) + "+")
        for r in range(y + 1, y + h - 1):
            s.addstr(r, x, "|")
            s.addstr(r, x + w - 1, "|")
        s.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
        if title:
            s.addstr(y, x + 2, f"[ {title} ]")
    except curses.error:
        pass


def local_models():
    if not MODELS_DIR.is_dir():
        return []
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and (p / ".leones-installed.json").is_file())


def recommendation_models(state):
    data = state.get("recommendation", {})
    return [x.get("model_id", x.get("model", "?")) for x in data.get("recommendations", [])[:3]]


def software_installed():
    """Mirror install.sh detection as closely as possible without mutating state."""
    installed = set()
    if shutil.which("llmfit"):
        installed.add("fitllm")
    if shutil.which("ods"):
        installed.add("ods")
    if shutil.which("magnitude"):
        installed.add("magnitude")
    if shutil.which("hermes") or (Path.home() / ".hermes").is_dir():
        installed.add("hermes")
    if shutil.which("omh") or (Path.home() / ".omh").is_dir():
        installed.add("omh")
    return installed


def installed_uninstall_components():
    """Only expose components for which local state/commands prove installation."""
    return [item for item in SOFTWARE if item in software_installed()]


def machine_state():
    cpu = "unavailable"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    gpu = "unavailable"
    if shutil.which("nvidia-smi"):
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                gpu = r.stdout.strip().replace("\n", "; ")
        except Exception:
            pass
    try:
        mem = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            mem[k] = int(v.split()[0]) * 1024
        ram = f"{human(mem['MemTotal'] - mem['MemAvailable'])} / {human(mem['MemTotal'])}"
    except Exception:
        ram = "unavailable"
    d = shutil.disk_usage(ROOT)
    return cpu, os.cpu_count() or 1, gpu, ram, f"{human(d.used)} / {human(d.total)}"


@dataclass
class OperationProgress:
    """TUI-visible operation state; terminal_progress remains the output bridge contract."""
    operation: str = ""
    phase: str = "idle"
    percent: float | None = None
    detail: str = ""

    @property
    def active(self):
        return self.phase not in {"idle", "completed", "failed"}

    def render(self):
        pct = "—" if self.percent is None else f"{self.percent:.1f}%"
        return f"{self.operation} | {self.phase} | {pct} | {self.detail}".strip()


def terminal_progress(operation, success, detail=None):
    """Compatibility bridge for operation-progress terminal reporting."""
    status = "completed" if success else "failed"
    return OperationProgress(operation, status, 100.0 if success else None, detail or "").render()


@dataclass
class TaskManager:
    lock: threading.Lock = field(default_factory=threading.Lock)
    active: bool = False
    kind: str = ""
    item: str = ""
    index: int = 0
    total: int = 0
    percent: float | None = None
    downloaded: int = 0
    total_bytes: int = 0
    rate: float = 0.0
    phase: str = "idle"
    message: str = ""
    results: list = field(default_factory=list)
    progress: OperationProgress = field(default_factory=OperationProgress)

    def snapshot(self):
        with self.lock:
            data = dict(self.__dict__)
            data["progress"] = self.progress.render()
            return data

    def start(self, kind, total):
        with self.lock:
            self.active = True
            self.kind = kind
            self.index = 0
            self.total = total
            self.item = ""
            self.percent = 0.0
            self.downloaded = 0
            self.total_bytes = 0
            self.rate = 0.0
            self.phase = "preparing"
            self.message = ""
            self.results = []
            self.progress = OperationProgress(kind, "preparing", 0.0, "")

    def parse(self, line):
        with self.lock:
            fields = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in line.split() if "=" in p}
            for key, attr, caster in (("PROGRESS", "percent", float), ("DOWNLOADED", "downloaded", int), ("TOTAL", "total_bytes", int), ("RATE", "rate", float)):
                if key in fields:
                    try:
                        setattr(self, attr, caster(fields[key].rstrip("%")))
                    except ValueError:
                        pass
            if line.startswith("PHASE=") or line.startswith("STATUS="):
                self.phase = line.split("=", 1)[1].strip().lower()
            elif line:
                self.message = line[-180:]
            self.progress = OperationProgress(self.item or self.kind, self.phase, self.percent, self.message)

    def run_cmd(self, command):
        try:
            p = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError as exc:
            with self.lock:
                self.message = str(exc)
            return False
        if p.stdout is not None:
            for line in p.stdout:
                self.parse(line.strip())
        return p.wait() == 0

    def finish(self, results):
        ok = all(success for _, success in results)
        with self.lock:
            self.results = results
            self.active = False
            self.phase = "completed" if ok else "failed"
            self.percent = 100.0 if ok else self.percent
            self.message = terminal_progress(self.item or self.kind, ok)
            self.progress = OperationProgress(self.item or self.kind, self.phase, self.percent, self.message)

    def launch(self, kind, items):
        items = list(items)
        if self.active or not items:
            return False
        self.start(kind, len(items))
        threading.Thread(target=self._worker, args=(kind, items), daemon=True).start()
        return True

    def _worker(self, kind, items):
        results = []
        for i, item in enumerate(items, 1):
            with self.lock:
                self.index = i
                self.item = item
                self.percent = 0.0
                self.phase = "downloading" if kind == "models" else ("removing" if kind == "uninstall" else "installing")
                self.message = ""
                self.progress = OperationProgress(item, self.phase, 0.0, "")
            if kind == "models":
                cmd = [sys.executable, str(INSTALLER), "--model-id", item, "--output-dir", str(MODELS_DIR)]
            elif kind == "software":
                cmd = ["bash", str(INSTALL_SH), f"--{item}"]
            else:
                cmd = ["bash", str(UNINSTALL_SH), "--yes", f"--{item}"]
            results.append((item, self.run_cmd(cmd)))
        self.finish(results)


def run_operation(task, kind, items):
    """Real-operation gateway used by ENTER; never reports success before exit."""
    return task.launch(kind, items)


def run_recommendation(task, purposes, state):
    task.start("recommender", 1)
    with task.lock:
        task.index = 1
        task.item = ", ".join(purposes)
        task.phase = "running"
        task.message = "RC4 recommender"
        task.progress = OperationProgress(task.item, "running", None, "RC4 recommender")

    def worker():
        cmd = [sys.executable, str(RECOMMENDER), "--json"]
        for purpose in purposes:
            cmd += ["--purpose", purpose]
        try:
            p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            output = []
            if p.stdout is not None:
                for line in p.stdout:
                    line = line.rstrip()
                    output.append(line)
                    with task.lock:
                        task.message = line[-180:]
                        task.percent = 10.0
                        task.progress = OperationProgress(task.item, "running", None, task.message)
            rc = p.wait()
            raw = "\n".join(output)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"status": "error", "message": raw[-500:]}
            with task.lock:
                state["recommendation"] = data
                task.results = [(data.get("status", "error"), rc == 0)]
                task.percent = 100.0 if rc == 0 else task.percent
                task.phase = "completed" if rc == 0 else "failed"
                task.message = terminal_progress("RC4 recommender", rc == 0, data.get("status", "error"))
                task.progress = OperationProgress("RC4 recommender", task.phase, task.percent, task.message)
                task.active = False
        except Exception as exc:
            with task.lock:
                task.results = [("error", False)]
                task.phase = "failed"
                task.message = str(exc)
                task.progress = OperationProgress("RC4 recommender", "failed", task.percent, task.message)
                task.active = False

    threading.Thread(target=worker, daemon=True).start()
    return True


def enter_key(key):
    return key in (10, 13, getattr(curses, "KEY_ENTER", 343))


def language_screen(s):
    focus = 0
    langs = ("es", "en", "zh")
    names = ("Español", "English", "中文")
    while True:
        s.erase()
        h, w = s.getmaxyx()
        bw = min(64, max(44, w - 4))
        x = max(1, (w - bw) // 2)
        box(s, 3, x, 14, bw, "LEONES RC4")
        put(s, 5, x + 4, "SELECCIONA IDIOMA / SELECT LANGUAGE / 选择语言", bw - 8)
        for i, name in enumerate(names):
            put(s, 8 + i, x + 8, f"{'▶' if i == focus else ' '} [{i + 1}] {name}", bw - 16)
        put(s, 13, x + 4, "↑/↓ · ENTER · Q", bw - 8)
        s.refresh()
        k = s.getch()
        if k in (curses.KEY_UP, ord("k")):
            focus = (focus - 1) % 3
        elif k in (curses.KEY_DOWN, ord("j")):
            focus = (focus + 1) % 3
        elif enter_key(k):
            return langs[focus]
        elif k in (ord("1"), ord("2"), ord("3")):
            return langs[int(chr(k)) - 1]
        elif k in (ord("q"), ord("Q"), 27):
            raise SystemExit


def content_items(nav, state):
    if nav == 2:
        return list(PURPOSES)
    if nav in (3, 4):
        return recommendation_models(state)
    if nav == 5:
        return list(SOFTWARE)
    if nav == 6:
        return installed_uninstall_components()
    return []


def selectable_mark(selected, item):
    return "[X]" if item in selected else "[ ]"


def ask_confirm(s, lang, uninstall=False):
    h, w = s.getmaxyx()
    title = tr(lang, "accept")
    message = tr(lang, "confirm_uninstall" if uninstall else "confirm")
    y = max(2, h - 7)
    box(s, y, 34, 5, max(42, w - 38), title)
    put(s, y + 2, 37, message, max(36, w - 44))
    s.refresh()
    while True:
        k = s.getch()
        if k in (ord("y"), ord("Y")):
            return True
        if k in (ord("n"), ord("N"), 27):
            return False


def requires_sudo(kind, item):
    if not shutil.which("sudo"):
        return False
    if kind == "software" and item in {"magnitude", "ods"}:
        return True
    if kind == "uninstall" and item in {"magnitude", "ods"}:
        return True
    return False


def authorize_system(s, lang):
    """Keep sudo authorization inside curses; never leak a normal sudo prompt."""
    h, w = s.getmaxyx()
    y = max(2, h - 7)
    box(s, y, 28, 5, max(48, w - 32), tr(lang, "authorize"))
    put(s, y + 2, 31, tr(lang, "password"), max(40, w - 38))
    s.refresh()
    try:
        curses.echo(False)
        s.move(y + 2, min(w - 2, 31 + len(tr(lang, "password"))))
        password = s.getstr().decode("utf-8", "replace")
    finally:
        curses.echo(True)
    if not password:
        return False
    try:
        p = subprocess.run(["sudo", "-S", "-p", "", "-v"], input=password + "\n", text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        return p.returncode == 0
    except Exception:
        return False
    finally:
        password = ""


def render(s, lang, nav, focus, index, state, task):
    s.erase()
    h, w = s.getmaxyx()
    if h < 30 or w < 100:
        put(s, 1, 2, "LEONES RC4 — minimum 100x30", w - 4)
        s.refresh()
        return
    box(s, 1, 1, h - 3, w - 2, "LEONES RC4")
    nw = 27
    box(s, 3, 3, h - 7, nw, tr(lang, "nav"))
    for i, label in enumerate(NAV[lang]):
        put(s, 5 + i * 2, 6, f"{'▶' if focus == 0 and i == nav else ' '} [{i + 1}] {label}", nw - 6)
    x = 32
    rw = w - x - 4
    mid_y = 13
    mid_h = max(10, h - 25)
    bot_y = mid_y + mid_h + 1
    bot_h = h - bot_y - 4
    box(s, 3, x, 9, rw, tr(lang, "activity"))
    box(s, mid_y, x, mid_h, rw, tr(lang, "selection"))
    box(s, bot_y, x, bot_h, rw, tr(lang, "action"))

    q = task.snapshot()
    put(s, 5, x + 2, f"● {tr(lang, 'active') if q['active'] else tr(lang, 'idle')}   {q['kind']} {q['index']}/{q['total']}", rw - 4)
    put(s, 6, x + 2, q["item"], rw - 4)
    put(s, 7, x + 2, f"{tr(lang, 'phase')}: {q['phase']}   {q['percent'] if q['percent'] is not None else '—'}%", rw - 4)
    put(s, 8, x + 2, bar(q["percent"]), rw - 4)
    put(s, 9, x + 2, f"{tr(lang, 'data')}: {human(q['downloaded'])}/{human(q['total_bytes'])}   {tr(lang, 'rate')}: {human(q['rate'])}/s", rw - 4)

    items = content_items(nav, state)
    if nav == 0:
        put(s, mid_y + 3, x + 2, tr(lang, "machine"), rw - 4)
    elif nav == 1:
        cpu, cores, gpu, ram, disk = machine_state()
        put(s, mid_y + 2, x + 2, tr(lang, "machine"), rw - 4)
        put(s, mid_y + 4, x + 3, f"{tr(lang, 'cpu')}: {cpu}", rw - 7)
        put(s, mid_y + 5, x + 3, f"{tr(lang, 'logical')}: {cores}", rw - 7)
        put(s, mid_y + 6, x + 3, f"{tr(lang, 'gpu')}: {gpu}", rw - 7)
        put(s, mid_y + 7, x + 3, f"{tr(lang, 'ram')}: {ram}", rw - 7)
        put(s, mid_y + 8, x + 3, f"{tr(lang, 'disk')}: {disk}", rw - 7)
        models = local_models()
        sw = software_installed()
        put(s, mid_y + 10, x + 3, f"{tr(lang, 'llms')}: {len(models)}", rw - 7)
        put(s, mid_y + 11, x + 3, ", ".join(models) if models else tr(lang, "none"), rw - 7)
        put(s, mid_y + 13, x + 3, "IA local: " + ", ".join(f"• {SOFTWARE_LABEL[k]}" for k in SOFTWARE if k in sw) if sw else "IA local: " + tr(lang, "none"), rw - 7)
    elif nav == 2:
        put(s, mid_y + 2, x + 2, tr(lang, "intent"), rw - 4)
        put(s, mid_y + 3, x + 2, tr(lang, "help"), rw - 4)
        for r, item in enumerate(items):
            mark = selectable_mark(state["purposes"], item)
            prefix = "▶" if focus == 1 and r == index else " "
            put(s, mid_y + 5 + r, x + 4, f"{prefix} {mark} {PURPOSES_LABEL[lang][item]}", rw - 8)
    elif nav == 3:
        put(s, mid_y + 2, x + 2, tr(lang, "recommend"), rw - 4)
        put(s, mid_y + 3, x + 2, tr(lang, "estimated"), rw - 4)
        if q["active"] and q["kind"] == "recommender":
            put(s, mid_y + 5, x + 4, tr(lang, "running"), rw - 8)
        for r, item in enumerate(items):
            prefix = "▶" if focus == 1 and r == index else " "
            put(s, mid_y + 6 + r, x + 4, f"{prefix} [{r + 1}] {item}", rw - 8)
    elif nav == 4:
        for r, item in enumerate(items):
            mark = selectable_mark(state["selected_models"], item)
            installed = "• " if item in local_models() else "  "
            prefix = "▶" if focus == 1 and r == index else " "
            put(s, mid_y + 4 + r, x + 4, f"{prefix} {mark} {installed}{item}", rw - 8)
    elif nav == 5:
        installed = software_installed()
        for r, item in enumerate(items):
            mark = selectable_mark(state["selected_software"], item)
            status = "•" if item in installed else " "
            prefix = "▶" if focus == 1 and r == index else " "
            put(s, mid_y + 4 + r, x + 4, f"{prefix} {mark} {status} {SOFTWARE_LABEL[item]}", rw - 8)
    else:
        chosen = state["selected_uninstall"]
        for r, item in enumerate(items):
            mark = selectable_mark(chosen, item)
            prefix = "▶" if focus == 1 and r == index else " "
            put(s, mid_y + 4 + r, x + 4, f"{prefix} {mark} • {SOFTWARE_LABEL[item]}", rw - 8)
        if not items:
            put(s, mid_y + 4, x + 4, tr(lang, "nothing_installed"), rw - 8)

    detail = items[index] if items and index < len(items) else ""
    put(s, bot_y + 2, x + 2, tr(lang, "details"), rw - 4)
    put(s, bot_y + 4, x + 4, detail, rw - 8)
    if q["message"]:
        put(s, bot_y + 5, x + 4, q["message"], rw - 8)
    put(s, h - 2, 4, f"{tr(lang,'tab')} · {tr(lang,'move')} · {tr(lang,'enter')} · {tr(lang,'space')} · {tr(lang,'back')} · {tr(lang,'quit')}", w - 8)

    try:
        if focus == 0:
            cy, cx = 5 + nav * 2, 6
        elif items and index < len(items):
            cy = (mid_y + 5 + index) if nav == 2 else (mid_y + 6 + index if nav == 3 else mid_y + 4 + index)
            cx = x + 4
        else:
            cy, cx = bot_y + 4, x + 4
        s.move(min(h - 2, cy), min(w - 2, cx))
    except curses.error:
        pass
    s.refresh()


def app(s):
    curses.curs_set(1)
    s.keypad(True)
    s.timeout(120)
    lang = language_screen(s)
    nav = 0
    # After language selection the persistent TUI always lands on [1] INICIO.
    # Focus is deliberately on the left navigation so the visible cursor is there.
    focus = 0
    index = 0
    state = {"purposes": set(), "selected_models": set(), "selected_software": set(), "selected_uninstall": set(), "recommendation": {}}
    task = TaskManager()
    while True:
        items = content_items(nav, state)
        if items:
            index %= len(items)
        else:
            index = 0
        render(s, lang, nav, focus, index, state, task)
        key = s.getch()
        if key == -1:
            continue
        if key in (ord("q"), ord("Q")):
            return
        if key == 9:
            focus = 0 if focus else 1
            continue
        if key == 27:
            focus = 0
            continue
        if focus == 0:
            if key in (curses.KEY_UP, ord("k")):
                nav = (nav - 1) % len(NAV_KEYS)
                index = 0
            elif key in (curses.KEY_DOWN, ord("j")):
                nav = (nav + 1) % len(NAV_KEYS)
                index = 0
            elif key in (ord("1"), ord("2"), ord("3"), ord("4"), ord("5"), ord("6"), ord("7")):
                nav = int(chr(key)) - 1
                index = 0
            continue
        if key in (curses.KEY_UP, ord("k")) and items:
            index = (index - 1) % len(items)
        elif key in (curses.KEY_DOWN, ord("j")) and items:
            index = (index + 1) % len(items)
        elif key == ord(" ") and items:
            selected = None
            if nav == 2:
                selected = state["purposes"]
            elif nav == 4:
                selected = state["selected_models"]
            elif nav == 5:
                selected = state["selected_software"]
            elif nav == 6:
                selected = state["selected_uninstall"]
            if selected is not None:
                if items[index] in selected:
                    selected.remove(items[index])
                else:
                    selected.add(items[index])
        elif enter_key(key):
            if nav == 2:
                selected = list(state["purposes"])
                # USER INTENT[] is mandatory. SPACE select is the multi-select boundary.
                if not selected:
                    put(s, s.getmaxyx()[0] - 5, 36, tr(lang, "first"), s.getmaxyx()[1] - 40)
                    s.refresh()
                    time.sleep(0.8)
                    continue
                if not task.active:
                    run_recommendation(task, selected, state)
                    nav = 3
                    index = 0
            elif nav == 4 and state["selected_models"] and not task.active:
                if ask_confirm(s, lang):
                    if all(not requires_sudo("models", item) for item in state["selected_models"]):
                        run_operation(task, "models", state["selected_models"])
            elif nav == 5 and state["selected_software"] and not task.active:
                if ask_confirm(s, lang):
                    authorized = True
                    for item in state["selected_software"]:
                        if requires_sudo("software", item):
                            authorized = authorize_system(s, lang)
                            if not authorized:
                                break
                    if authorized:
                        run_operation(task, "software", state["selected_software"])
                    else:
                        put(s, s.getmaxyx()[0] - 5, 36, tr(lang, "auth_failed"), s.getmaxyx()[1] - 40)
                        s.refresh()
                        time.sleep(0.8)
            elif nav == 6 and state["selected_uninstall"] and not task.active:
                if ask_confirm(s, lang, uninstall=True):
                    authorized = True
                    for item in state["selected_uninstall"]:
                        if requires_sudo("uninstall", item):
                            authorized = authorize_system(s, lang)
                            if not authorized:
                                break
                    if authorized:
                        run_operation(task, "uninstall", state["selected_uninstall"])
                    else:
                        put(s, s.getmaxyx()[0] - 5, 36, tr(lang, "auth_failed"), s.getmaxyx()[1] - 40)
                        s.refresh()
                        time.sleep(0.8)
        # MEASURED is intentionally not used here: RC4 recommendations remain ESTIMATED.


def main():
    curses.wrapper(app)


if __name__ == "__main__":
    main()
