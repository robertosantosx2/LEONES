#!/usr/bin/env python3
"""LEONES RC4 retro TUI.

Startup flow: language -> machine state -> optional maintenance -> TUI.
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
PURPOSES = (("programming", "PROGRAMMING"), ("reasoning", "REASONING"), ("research", "RESEARCH"), ("chat", "CHAT"), ("multimodal", "MULTIMODAL"), ("embedding", "EMBEDDING"), ("general", "GENERAL"))

T = {
    "es": {"lang":"SELECCIONA IDIOMA", "nav":"NAVEGACIÓN", "dash":"Panel", "machine":"Estado de máquina", "intent":"Intención", "rec":"Recomendador", "evidence":"Evidencia", "legacy":"RC2 legado", "settings":"Configuración", "exit":"Salir", "status":"ESTADO DEL SISTEMA", "network":"RED: ACTIVA", "runtime":"RUNTIME: llama.cpp / límite de medición local", "evidence_line":"EVIDENCIA: HF + Artificial Analysis / ESTIMADA", "workspace":"ESPACIO DE TRABAJO RC4", "intent_req":"USER INTENT[]  --  SELECCIÓN MÚLTIPLE  --  OBLIGATORIA", "intent_help":"Selecciona los propósitos y pulsa ENTER para recomendar.", "running":"CONSULTANDO EVIDENCIA + LLMFit ...", "no_candidates":"Sin candidatos", "empty":"Selecciona al menos un propósito antes de recomendar.", "footer":"TAB navegación  ↑/↓ mover  ESPACIO seleccionar  ENTER recomendar  R repetir  Q salir", "nav_help":"TAB entrar/salir de navegación  ↑/↓ mover  ENTER abrir", "small":"LEONES RC4 TUI -- terminal demasiado pequeña (mín. 92x25)", "resize":"Redimensiona la ventana. Q: salir", "maintenance":"MANTENIMIENTO", "maint_title":"ACTUALIZAR / DESINSTALAR", "maint_info":"LEONES calcula el inventario antes de cualquier cambio.", "maint_safe":"La acción destructiva sigue siendo opt-in y requiere confirmación.", "back":"[ENTER] volver", "select":"SELECCIONA IDIOMA", "keys":"↑/↓ · ENTER", "unknown":"desconocido", "not_detected":"no detectada"},
    "en": {"lang":"SELECT LANGUAGE", "nav":"NAVIGATION", "dash":"Dashboard", "machine":"Machine State", "intent":"Intent", "rec":"Recommender", "evidence":"Evidence", "legacy":"RC2 legacy", "settings":"Settings", "exit":"Exit", "status":"SYSTEM STATUS", "network":"NETWORK: UP", "runtime":"RUNTIME: llama.cpp / local measurement boundary", "evidence_line":"EVIDENCE: HF + Artificial Analysis / ESTIMATED", "workspace":"RC4 WORKSPACE", "intent_req":"USER INTENT[]  --  MULTI SELECT  --  REQUIRED", "intent_help":"Select purposes, then press ENTER to recommend.", "running":"QUERYING EVIDENCE + LLMFit ...", "no_candidates":"No candidates", "empty":"Select at least one purpose before recommending.", "footer":"TAB navigation  ↑/↓ move  SPACE select  ENTER recommend  R rerun  Q quit", "nav_help":"TAB enter/leave navigation  ↑/↓ move  ENTER open", "small":"LEONES RC4 TUI -- terminal too small (min 92x25)", "resize":"Resize the window. Q: quit", "maintenance":"MAINTENANCE", "maint_title":"UPDATE / UNINSTALL", "maint_info":"LEONES calculates inventory before any change.", "maint_safe":"Destructive action remains opt-in and requires confirmation.", "back":"[ENTER] back", "select":"SELECT LANGUAGE", "keys":"↑/↓ · ENTER", "unknown":"unknown", "not_detected":"not detected"},
    "zh": {"lang":"选择语言", "nav":"导航", "dash":"仪表板", "machine":"机器状态", "intent":"意图", "rec":"推荐器", "evidence":"证据", "legacy":"RC2 旧版", "settings":"设置", "exit":"退出", "status":"系统状态", "network":"网络：正常", "runtime":"运行时：llama.cpp / 本地测量边界", "evidence_line":"证据：HF + Artificial Analysis / 估算", "workspace":"RC4 工作区", "intent_req":"USER INTENT[]  --  多选  --  必填", "intent_help":"选择用途，然后按 ENTER 获取推荐。", "running":"正在查询证据 + LLMFit ...", "no_candidates":"没有候选模型", "empty":"请至少选择一个用途后再推荐。", "footer":"TAB 导航  ↑/↓移动  空格选择  ENTER推荐  R重试  Q退出", "nav_help":"TAB 进入/离开导航  ↑/↓移动  ENTER打开", "small":"LEONES RC4 TUI -- 终端太小（最小 92x25）", "resize":"请调整窗口大小。Q：退出", "maintenance":"维护", "maint_title":"更新 / 卸载", "maint_info":"LEONES 会在任何更改前计算库存。", "maint_safe":"破坏性操作必须主动选择并确认。", "back":"[ENTER] 返回", "select":"选择语言", "keys":"↑/↓ · ENTER", "unknown":"未知", "not_detected":"未检测到"},
}


def tr(language: str, key: str) -> str:
    return T.get(language, T["es"]).get(key, T["es"].get(key, key))


def memory_stats() -> tuple[int, int, int]:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0]) * 1024
        total, available = values["MemTotal"], values["MemAvailable"]
        used = total - available
        return used, total, round(used * 100 / total)
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return 0, 0, 0


def memory_percent() -> int: return memory_stats()[2]


def cpu_percent() -> int:
    try: return min(100, round(os.getloadavg()[0] * 100 / (os.cpu_count() or 1)))
    except OSError: return 0


def disk_stats() -> tuple[int, int, int]:
    try:
        u = shutil.disk_usage(ROOT)
        return u.used, u.total, round(u.used * 100 / u.total)
    except OSError: return 0, 0, 0


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB": return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def machine_hardware() -> list[str]:
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip(); break
    except OSError: pass
    cores = os.cpu_count() or 1
    gpu = "not detected"
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, check=False, timeout=5)
            if out.returncode == 0 and out.stdout.strip(): gpu = out.stdout.strip().replace("\n", "; ")
        except (OSError, subprocess.TimeoutExpired): pass
    return [f"CPU     {cpu} ({cores} logical CPUs)", f"GPU     {gpu}"]


def load_inventory() -> dict:
    try:
        p = subprocess.run([sys.executable, str(INVENTORY), "--json"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=20)
        return json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError): return {"components": []}


def agent_names() -> list[str]:
    names = []
    for directory in (ROOT / "agents", ROOT / ".leones" / "agents"):
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if not child.name.startswith(".") and (child.is_dir() or child.suffix in {".py", ".sh", ".json", ".yaml", ".yml"}): names.append(child.stem if child.is_file() else child.name)
    return list(dict.fromkeys(names))


def add_box(stdscr, y, x, h, w, title):
    if h < 3 or w < 4: return
    stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
    for row in range(y + 1, y + h - 1): stdscr.addstr(row, x, "|"); stdscr.addstr(row, x + w - 1, "|")
    stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
    label = "[ " + title + " ]"
    if len(label) < w - 4: stdscr.addstr(y, x + 2, label)


def put(stdscr, y, x, text, width):
    if width > 0 and 0 <= y < stdscr.getmaxyx()[0]:
        try: stdscr.addstr(y, x, text[:width])
        except curses.error: pass


def wait_key(stdscr): stdscr.refresh(); return stdscr.getch()


def language_screen(stdscr):
    focus = 0; languages = (("es", "Español"), ("en", "English"), ("zh", "中文"))
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx(); box_w = min(70, max(40, w - 4)); x = max(1, (w - box_w) // 2)
        add_box(stdscr, 3, x, 12, box_w, "LEONES RC4")
        put(stdscr, 5, x + 4, tr(languages[focus][0], "select"), box_w - 8)
        for i, (_, label) in enumerate(languages): put(stdscr, 8 + i, x + 8, f"{'>' if i == focus else ' '} [{i + 1}] {label}", box_w - 16)
        put(stdscr, 12, x + 4, tr(languages[focus][0], "keys"), box_w - 8)
        key = wait_key(stdscr)
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % 3
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % 3
        elif key in (10, 13, ord("1"), ord("2"), ord("3")):
            if key in (ord("1"), ord("2"), ord("3")): focus = int(chr(key)) - 1
            return languages[focus][0]


def machine_state_screen(stdscr, language):
    inv = load_inventory(); used, total, mem_pct = memory_stats(); disk_used, disk_total, disk_pct = disk_stats(); agents = agent_names(); components = inv.get("components", [])
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        if h < 25 or w < 92:
            put(stdscr, 1, 2, tr(language, "small"), w - 4); put(stdscr, 3, 2, tr(language, "resize"), w - 4)
            if wait_key(stdscr) in (ord("q"), ord("Q")): raise SystemExit(0)
            continue
        title = {"es":"LEONES // ESTADO DE LA MÁQUINA", "en":"LEONES // MACHINE STATE", "zh":"LEONES // 机器状态"}[language]
        box = {"es":"ESTADO DE LA MÁQUINA", "en":"MACHINE STATE", "zh":"机器状态"}[language]
        put(stdscr, 0, max(2, (w - len(title)) // 2), title, len(title)); add_box(stdscr, 1, 1, h - 4, w - 2, box); x = 4
        labels = {"es":("HARDWARE","RECURSOS EN USO","SOFTWARE IA INSTALADO","DISCO","Agentes"), "en":("HARDWARE","RESOURCES IN USE","INSTALLED AI SOFTWARE","DISK","Agents"), "zh":("硬件","正在使用的资源","已安装的 AI 软件","磁盘","智能体")}[language]
        put(stdscr, 3, x, labels[0], w - 8)
        for i, line in enumerate(machine_hardware()): put(stdscr, 4 + i, x, line.replace("not detected", tr(language, "not_detected")), w - 8)
        put(stdscr, 7, x, labels[1], w - 8); put(stdscr, 8, x, f"RAM     {human_bytes(used)} / {human_bytes(total)}   [{mem_pct:>3}%]", w - 8); put(stdscr, 9, x, f"CPU     {cpu_percent():>3}%", w - 8); put(stdscr, 10, x, f"{labels[3]:<8}{human_bytes(disk_used)} / {human_bytes(disk_total)}   [{disk_pct:>3}%]", w - 8); put(stdscr, 12, x, labels[2], w - 8)
        row = 13
        for c in components:
            if c.get("installed"):
                name = c["display_name"]
                if name == "LLMs locales (Ollama models)": name = {"es":name,"en":"Local LLMs (Ollama models)","zh":"本地 LLM（Ollama 模型）"}[language]
                elif name == "LEONES (estado local .leones/)": name = {"es":name,"en":"LEONES (local .leones/ state)","zh":"LEONES（本地 .leones/ 状态）"}[language]
                detail = " :: " + ", ".join(c["models"]) if c.get("models") else ""; put(stdscr, row, x, f"● {name}{detail}", w - 8); row += 1
        put(stdscr, row, x, f"● {labels[4]} ({len(agents)}) :: {', '.join(agents) if agents else {'es':'ninguno detectado','en':'none detected','zh':'未检测到'}[language]}", w - 8); row += 2
        put(stdscr, row, x, {"es":"[ENTER] continuar   [M] mantenimiento   [Q] salir", "en":"[ENTER] continue   [M] maintenance   [Q] quit", "zh":"[ENTER] 继续   [M] 维护   [Q] 退出"}[language], w - 8)
        key = wait_key(stdscr)
        if key in (ord("q"), ord("Q")): raise SystemExit(0)
        if key in (10, 13): return
        if key in (ord("m"), ord("M")): maintenance_screen(stdscr, inv, language)


def maintenance_screen(stdscr, inv, language):
    stdscr.erase(); h, w = stdscr.getmaxyx(); add_box(stdscr, 2, 2, min(h - 5, 30), w - 4, tr(language, "maintenance")); x = 5; row = 4
    put(stdscr, row, x, tr(language, "maint_title"), w - 10); row += 2
    for c in inv.get("components", []):
        if c.get("installed"):
            suffix = " [desinstalable]" if c.get("uninstallable") else " [runtime/protegido]"
            if language == "en": suffix = " [uninstallable]" if c.get("uninstallable") else " [runtime/protected]"
            if language == "zh": suffix = " [可卸载]" if c.get("uninstallable") else " [运行时/受保护]"
            put(stdscr, row, x, f"{c['display_name']}{suffix}", w - 10); row += 1
    row += 1; put(stdscr, row, x, tr(language, "maint_info"), w - 10); put(stdscr, row + 1, x, tr(language, "maint_safe"), w - 10); put(stdscr, row + 3, x, tr(language, "back"), w - 10); wait_key(stdscr)


def run_recommendation(purposes):
    command = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes: command.extend(["--purpose", purpose])
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False); data = json.loads(completed.stdout); return data.get("status", "error"), data
    except (OSError, json.JSONDecodeError) as exc: return "error", {"message": str(exc)}


def draw(stdscr, selected, status, result, focus, nav_focus=False, nav_index=0, language="es"):
    stdscr.erase(); height, width = stdscr.getmaxyx()
    if height < 25 or width < 92: put(stdscr, 1, 2, tr(language, "small"), width - 4); put(stdscr, 3, 2, tr(language, "resize"), width - 4); stdscr.refresh(); return
    title = "LEONES // AI OPERATING SYSTEM v4"; put(stdscr, 0, max(2, (width - len(title)) // 2), title, len(title)); left_w = 27; right_x = left_w + 3; right_w = width - right_x - 2; top_h = 7; bottom_y = top_h + 2; main_h = height - bottom_y - 2
    nav_title = tr(language, "nav") + (" <FOCUS>" if nav_focus else "")
    add_box(stdscr, 1, 1, height - 3, left_w, nav_title); nav = [tr(language, "dash"), tr(language, "machine"), tr(language, "intent"), tr(language, "rec"), tr(language, "evidence"), tr(language, "legacy"), tr(language, "settings"), tr(language, "exit")]
    put(stdscr, 3, 4, ("> " if nav_focus and nav_index == 0 else "[X] ") + "LEONES RC4", left_w - 6)
    for i, item in enumerate(nav[:5]): put(stdscr, 4 + i, 6, ("> " if nav_focus and nav_index == i + 1 else "-> ") + item, left_w - 8)
    put(stdscr, 10, 4, ("> " if nav_focus and nav_index == 6 else "[ ] ") + tr(language, "legacy"), left_w - 6); put(stdscr, 12, 4, ("> " if nav_focus and nav_index == 7 else "[ ] ") + tr(language, "settings"), left_w - 6); put(stdscr, 14, 4, ("> " if nav_focus and nav_index == 8 else "[ ] ") + tr(language, "exit"), left_w - 6)
    add_box(stdscr, 1, right_x, top_h, right_w, tr(language, "status")); put(stdscr, 3, right_x + 3, f"CPU: {cpu_percent():>3}%   MEM: {memory_percent():>3}%   {tr(language, 'network')}", right_w - 6); put(stdscr, 4, right_x + 3, tr(language, "runtime"), right_w - 6); put(stdscr, 5, right_x + 3, tr(language, "evidence_line"), right_w - 6)
    add_box(stdscr, bottom_y, right_x, main_h, right_w, tr(language, "workspace")); inner_x = right_x + 3; content_w = right_w - 6; put(stdscr, bottom_y + 2, inner_x, tr(language, "intent_req"), content_w); put(stdscr, bottom_y + 3, inner_x, tr(language, "intent_help"), content_w)
    for idx, (key, label) in enumerate(PURPOSES): put(stdscr, bottom_y + 5 + idx, inner_x, f"{'>' if not nav_focus and idx == focus else ' '} [{'X' if key in selected else ' '}] {idx + 1}. {label}", content_w)
    status_y = bottom_y + 5 + len(PURPOSES) + 1
    if status == "running": put(stdscr, status_y, inner_x, "JOB: #RC4 -- " + tr(language, "running"), content_w)
    elif result:
        put(stdscr, status_y, inner_x, f"JOB: #RC4 -- {status.upper()}", content_w); rows = result.get("recommendations") or []
        for n, row in enumerate(rows[:3], 1): put(stdscr, status_y + n, inner_x, f"[{n}] {row.get('model_id', '?')}  ::  ESTIMATED", content_w)
        if not rows: put(stdscr, status_y + 1, inner_x, result.get("message", tr(language, "no_candidates")), content_w)
    put(stdscr, height - 2, 2, tr(language, "nav_help") if nav_focus else tr(language, "footer"), width - 4); stdscr.refresh()


def main():
    selected = set(); focus = 0; status = "ready"; result = None; nav_focus = False; nav_index = 0
    nav_count = 9
    def app(stdscr):
        nonlocal focus, status, result, nav_focus, nav_index
        curses.curs_set(0); stdscr.keypad(True); language = language_screen(stdscr); machine_state_screen(stdscr, language)
        while True:
            draw(stdscr, selected, status, result, focus, nav_focus, nav_index, language); key = stdscr.getch()
            if key in (ord("q"), ord("Q")): return
            if key == 9:
                nav_focus = not nav_focus
                continue
            if nav_focus:
                if key in (curses.KEY_UP, ord("k")): nav_index = (nav_index - 1) % nav_count
                elif key in (curses.KEY_DOWN, ord("j")): nav_index = (nav_index + 1) % nav_count
                elif key in (10, 13):
                    if nav_index == 8: return
                    if nav_index == 0: nav_focus = False
                    elif nav_index == 1: machine_state_screen(stdscr, language); nav_focus = False
                    elif nav_index == 2: nav_focus = False; focus = 0
                    elif nav_index in (3, 4): nav_focus = False
                    elif nav_index in (5, 6): nav_focus = False
                continue
            if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % len(PURPOSES)
            elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % len(PURPOSES)
            elif key == ord(" "):
                name = PURPOSES[focus][0]; selected.remove(name) if name in selected else selected.add(name)
            elif key in (ord("r"), ord("R"), 10, 13):
                if not selected: status = "insufficient"; result = {"message": tr(language, "empty")}; continue
                status = "running"; draw(stdscr, selected, status, None, focus, nav_focus, nav_index, language); status, result = run_recommendation([p for p, _ in PURPOSES if p in selected])
    curses.wrapper(app); return 0


if __name__ == "__main__": raise SystemExit(main())
