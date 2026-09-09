#!/usr/bin/env python3
"""LEONES RC4 human-choice TUI.

Single coherent workspace: language -> machine state -> purposes -> models ->
solution -> cost -> explicit confirmation. The navigation panel remains visible
throughout the workspace. This layer informs/calculates only; it never installs.
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
CATALOG = ROOT / "catalogs" / "rc4_solutions.json"
PURPOSES = ("programming", "reasoning", "research", "chat", "multimodal", "embedding", "general")
SOLUTIONS = ("personal_assistant", "soho", "both")
NAV_ITEMS = ("dashboard", "machine", "intent", "recommender", "evidence", "settings", "exit")

T = {
    "es": {
        "language":"IDIOMA", "es":"Español", "en":"Inglés", "zh":"Chino", "nav":"NAVEGACIÓN",
        "dashboard":"Panel", "machine":"Estado de máquina", "intent":"Intención", "recommender":"Recomendador",
        "evidence":"Evidencia", "settings":"Configuración", "exit":"Salir", "system":"ESTADO DEL SISTEMA",
        "workspace":"ESPACIO DE TRABAJO RC4", "focus":"FOCO", "unknown":"DESCONOCIDO", "measured":"MEDIDO",
        "declared":"DECLARADO", "estimated":"ESTIMADO", "purposes":"PROPÓSITOS", "purpose_prompt":"Selecciona uno o varios propósitos:",
        "models":"MODELOS", "models_prompt":"MODELOS COMPATIBLES / RECOMENDADOS · SELECCIÓN MÚLTIPLE · SIN LÍMITE ARTIFICIAL",
        "solution":"SOLUCIÓN", "solution_prompt":"Selecciona la solución de despliegue:", "cost":"COSTE DE LA SELECCIÓN",
        "confirm":"CONFIRMACIÓN EXPLÍCITA", "programming":"PROGRAMACIÓN", "reasoning":"RAZONAMIENTO", "research":"INVESTIGACIÓN",
        "chat":"CHAT / ASISTENTE", "multimodal":"MULTIMODAL", "embedding":"EMBEDDINGS / BÚSQUEDA", "general":"USO GENERAL",
        "personal_assistant":"ASISTENTE IA PERSONAL", "soho":"SOHO COMPLETO", "both":"PERSONAL + SOHO",
        "personal_desc":"Asistente personal local para un usuario principal.", "soho_desc":"Servicios de IA locales para varios usuarios y servicios compartidos.",
        "personal_functions":"chat local; asistencia personal; acceso a modelos seleccionados; documentos y contexto locales; interacción local de un solo usuario",
        "soho_functions":"servicio multiusuario; servicios de IA locales; acceso a modelos seleccionados; endpoints locales compartidos; operación orientada a servicios",
        "personal_usage":"Uso interactivo y por ráfagas; el consumo depende del modelo, contexto y concurrencia.",
        "soho_usage":"Puede haber uso concurrente y sostenido; el consumo depende del modelo, concurrencia, contexto y servicios.",
        "memory":"MEMORIA", "total":"TOTAL", "free":"LIBRE", "used":"EN USO", "cpu":"CPU", "load":"CARGA 1 MIN",
        "logical":"LÓGICOS", "disk":"DISCO", "top_mem":"TOP 5 PROCESOS · MEMORIA", "top_cpu":"TOP 5 PROCESOS · CPU",
        "functions":"FUNCIONALIDADES", "usage":"USO HABITUAL", "install":"INSTALACIÓN", "ram":"RAM", "vram":"VRAM",
        "required":"REQUERIDO", "sufficient":"SUFICIENTE", "insufficient":"INSUFICIENTE", "gate":"GATE DISCO",
        "move":"↑/↓ mover", "space":"ESPACIO seleccionar", "enter":"ENTER abrir/continuar", "tab":"TAB navegación",
        "back":"B volver", "quit":"Q salir", "consent":"ENTER = registrar consentimiento", "no_install":"NO ejecuta instalación en esta capa",
        "models_count":"Modelos: {n} seleccionado(s), sin límite artificial", "unknown_gate":"DESCONOCIDO no pasa el gate · no instalación parcial por defecto",
        "root":"LEONES RC4", "status":"LEONES informa / calcula · el usuario decide",
    },
    "en": {
        "language":"LANGUAGE", "es":"Spanish", "en":"English", "zh":"Chinese", "nav":"NAVIGATION", "dashboard":"Dashboard",
        "machine":"Machine State", "intent":"Intent", "recommender":"Recommender", "evidence":"Evidence", "settings":"Settings", "exit":"Exit",
        "system":"SYSTEM STATE", "workspace":"RC4 WORKSPACE", "focus":"FOCUS", "unknown":"UNKNOWN", "measured":"MEASURED", "declared":"DECLARED", "estimated":"ESTIMATED",
        "purposes":"PURPOSES", "purpose_prompt":"Select one or more purposes:", "models":"MODELS", "models_prompt":"COMPATIBLE / RECOMMENDED MODELS · MULTI-SELECTION · NO ARTIFICIAL LIMIT",
        "solution":"SOLUTION", "solution_prompt":"Select deployment solution:", "cost":"SELECTION COST", "confirm":"EXPLICIT CONFIRMATION",
        "programming":"PROGRAMMING", "reasoning":"REASONING", "research":"RESEARCH", "chat":"CHAT / ASSISTANT", "multimodal":"MULTIMODAL", "embedding":"EMBEDDINGS / SEARCH", "general":"GENERAL USE",
        "personal_assistant":"PERSONAL AI ASSISTANT", "soho":"FULL SOHO", "both":"PERSONAL + SOHO", "personal_desc":"Local personal assistant for one primary user.", "soho_desc":"Local AI services for multiple users and shared services.",
        "personal_functions":"local chat; personal assistance; selected model access; local documents and context; single-user local interaction",
        "soho_functions":"multi-user service; local AI services; selected model access; shared local endpoints; service-oriented operation",
        "personal_usage":"Interactive and bursty use; consumption depends on model, context and concurrency.", "soho_usage":"Concurrent and sustained use is possible; consumption depends on model, concurrency, context and services.",
        "memory":"MEMORY", "total":"TOTAL", "free":"FREE", "used":"IN USE", "cpu":"CPU", "load":"1 MIN LOAD", "logical":"LOGICAL", "disk":"DISK",
        "top_mem":"TOP 5 PROCESSES · MEMORY", "top_cpu":"TOP 5 PROCESSES · CPU", "functions":"FUNCTIONS", "usage":"NORMAL USE", "install":"INSTALLATION", "ram":"RAM", "vram":"VRAM",
        "required":"REQUIRED", "sufficient":"SUFFICIENT", "insufficient":"INSUFFICIENT", "gate":"DISK GATE", "move":"↑/↓ move", "space":"SPACE select", "enter":"ENTER open/continue", "tab":"TAB navigation", "back":"B back", "quit":"Q quit",
        "consent":"ENTER = record consent", "no_install":"DOES NOT execute installation in this layer", "models_count":"Models: {n} selected, no artificial limit", "unknown_gate":"UNKNOWN does not pass the gate · no partial installation by default",
        "root":"LEONES RC4", "status":"LEONES informs / calculates · user decides",
    },
    "zh": {
        "language":"语言", "es":"西班牙语", "en":"英语", "zh":"中文", "nav":"导航", "dashboard":"仪表板", "machine":"机器状态", "intent":"意图", "recommender":"推荐器", "evidence":"证据", "settings":"设置", "exit":"退出",
        "system":"系统状态", "workspace":"RC4 工作区", "focus":"焦点", "unknown":"未知", "measured":"已测量", "declared":"已声明", "estimated":"估算", "purposes":"用途", "purpose_prompt":"选择一个或多个用途：",
        "models":"模型", "models_prompt":"兼容 / 推荐模型 · 多选 · 无人为数量限制", "solution":"方案", "solution_prompt":"选择部署方案：", "cost":"选择成本", "confirm":"明确确认",
        "programming":"编程", "reasoning":"推理", "research":"研究", "chat":"聊天 / 助手", "multimodal":"多模态", "embedding":"嵌入 / 搜索", "general":"通用用途", "personal_assistant":"个人 AI 助手", "soho":"完整 SOHO", "both":"个人助手 + SOHO",
        "personal_desc":"面向主要用户的本地个人助手。", "soho_desc":"面向多用户和共享服务的本地 AI 服务。", "personal_functions":"本地聊天；个人助理；访问所选模型；本地文档和上下文；单用户本地交互", "soho_functions":"多用户服务；本地 AI 服务；访问所选模型；共享本地端点；面向服务的运行",
        "personal_usage":"交互式、突发式使用；资源消耗取决于模型、上下文和并发。", "soho_usage":"可进行并发和持续使用；资源消耗取决于模型、并发、上下文和服务。", "memory":"内存", "total":"总计", "free":"可用", "used":"使用中", "cpu":"CPU", "load":"1分钟负载", "logical":"逻辑", "disk":"磁盘",
        "top_mem":"内存占用前5个进程", "top_cpu":"CPU占用前5个进程", "functions":"功能", "usage":"正常使用", "install":"安装", "ram":"内存", "vram":"显存", "required":"需要", "sufficient":"足够", "insufficient":"不足", "gate":"磁盘门禁",
        "move":"↑/↓ 移动", "space":"空格 选择", "enter":"ENTER 打开/继续", "tab":"TAB 导航", "back":"B 返回", "quit":"Q 退出", "consent":"ENTER = 记录同意", "no_install":"本层不会执行安装", "models_count":"模型：已选择 {n} 个，无人为数量限制", "unknown_gate":"未知值不能通过门禁 · 默认不进行部分安装",
        "root":"LEONES RC4", "status":"LEONES 提供信息 / 计算 · 用户决定",
    },
}


def tr(lang: str, key: str, **kw: object) -> str:
    return T.get(lang, T["es"]).get(key, key).format(**kw)


def hb(value: object, lang: str) -> str:
    if not isinstance(value, int) or value < 0:
        return tr(lang, "unknown")
    n = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return tr(lang, "unknown")


def put(s: curses.window, y: int, x: int, text: object, width: int | None = None) -> None:
    if width is None:
        width = max(0, s.getmaxyx()[1] - x - 1)
    if 0 <= y < s.getmaxyx()[0] and width > 0:
        try:
            s.addstr(y, x, str(text)[:width])
        except curses.error:
            pass


def box(s: curses.window, y: int, x: int, h: int, w: int, title: str) -> None:
    if h < 3 or w < 4:
        return
    try:
        s.addstr(y, x, "+" + "-" * (w - 2) + "+")
        for r in range(y + 1, y + h - 1):
            s.addstr(r, x, "|"); s.addstr(r, x + w - 1, "|")
        s.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
        if len(title) + 4 < w:
            s.addstr(y, x + 2, "[ " + title + " ]")
    except curses.error:
        pass


def machine_data() -> dict:
    data = {"mem": None, "cpu": None, "disk": None, "memtop": [], "cputop": []}
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, rest = line.split(":", 1); info[key] = int(rest.split()[0]) * 1024
        data["mem"] = (info["MemTotal"], info["MemAvailable"], info["MemTotal"] - info["MemAvailable"])
    except Exception:
        pass
    try:
        data["cpu"] = (os.getloadavg()[0], os.cpu_count() or 1)
    except OSError:
        pass
    try:
        data["disk"] = shutil.disk_usage(ROOT)
    except OSError:
        pass
    for key, cmd in (("memtop", ["ps", "-eo", "pid,%mem,rss,comm", "--sort=-%mem"]), ("cputop", ["ps", "-eo", "pid,%cpu,%mem,comm", "--sort=-%cpu"])):
        try:
            data[key] = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.splitlines()[1:6]
        except Exception:
            pass
    return data


def catalog() -> dict:
    try:
        return json.loads(CATALOG.read_text()).get("solutions", {})
    except Exception:
        return {}


def model_cost(model: dict) -> int | None:
    raw = model.get("raw") if isinstance(model.get("raw"), dict) else {}
    for key in ("size_bytes", "disk_bytes", "size", "disk_size_bytes"):
        value = raw.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None


def recommend(purposes: list[str]) -> list[dict]:
    cmd = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes:
        cmd += ["--purpose", purpose]
    try:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=90)
        return json.loads(result.stdout).get("recommendations") or []
    except Exception:
        return []


def solution_keys(solution: str) -> tuple[str, ...]:
    return ("personal_assistant", "soho") if solution == "both" else (solution,)


def solution_info(solution: str, lang: str) -> tuple[str, list[str], str]:
    keys = solution_keys(solution)
    desc_keys = {"personal_assistant": "personal_desc", "soho": "soho_desc"}
    func_keys = {"personal_assistant": "personal_functions", "soho": "soho_functions"}
    usage_keys = {"personal_assistant": "personal_usage", "soho": "soho_usage"}
    desc = " ".join(tr(lang, desc_keys[k]) for k in keys)
    functions: list[str] = []
    for key in keys:
        functions.extend(tr(lang, func_keys[key]).split(";"))
    usage = " ".join(tr(lang, usage_keys[k]) for k in keys)
    return desc, functions, usage


def aggregate(models: list[dict], selected: set[int], solution: str) -> int | None:
    total = 0
    for index in selected:
        value = model_cost(models[index])
        if value is None:
            return None
        total += value
    for key in solution_keys(solution):
        value = catalog().get(key, {}).get("disk_bytes")
        if not isinstance(value, int):
            return None
        total += value
    return total


def provenance(value: object, lang: str) -> str:
    return tr(lang, "declared") if isinstance(value, int) else tr(lang, "unknown")


def nav_draw(s: curses.window, lang: str, navidx: int, navfocus: bool, phase: int, width: int, height: int) -> None:
    box(s, 1, 1, height - 3, width, tr(lang, "nav"))
    put(s, 3, 3, "[X] " + tr(lang, "root"), width - 6)
    for i, key in enumerate(NAV_ITEMS):
        marker = ">" if navfocus and i == navidx else " "
        active = "*" if (not navfocus and ((key == "intent" and phase == 0) or (key == "recommender" and phase == 1) or (key == "dashboard" and phase == 2) or (key == "evidence" and phase in (3, 4)))) else " "
        put(s, 5 + i, 4, f"{marker}{active} {tr(lang, key)}", width - 7)
    put(s, height - 5, 3, tr(lang, "tab"), width - 5)


def system_summary(s: curses.window, lang: str, x: int, y: int, width: int) -> None:
    data = machine_data()
    box(s, y, x, 6, width, tr(lang, "system"))
    if data["mem"]:
        total, free, used = data["mem"]
        put(s, y + 1, x + 2, f"{tr(lang,'memory')} [{tr(lang,'measured')}]: {hb(total,lang)} {tr(lang,'total').lower()} · {hb(free,lang)} {tr(lang,'free').lower()} · {hb(used,lang)} {tr(lang,'used').lower()}", width - 4)
    else:
        put(s, y + 1, x + 2, f"{tr(lang,'memory')} [{tr(lang,'unknown')}]: {tr(lang,'unknown')}", width - 4)
    if data["cpu"]:
        load, cores = data["cpu"]
        put(s, y + 2, x + 2, f"{tr(lang,'cpu')} [{tr(lang,'measured')}]: {load:.2f} {tr(lang,'load')} · {cores} {tr(lang,'logical')}", width - 4)
    else:
        put(s, y + 2, x + 2, f"{tr(lang,'cpu')} [{tr(lang,'unknown')}]: {tr(lang,'unknown')}", width - 4)
    if data["disk"]:
        put(s, y + 3, x + 2, f"{tr(lang,'disk')} [{tr(lang,'measured')}]: {hb(data['disk'].free,lang)} {tr(lang,'free').lower()} / {hb(data['disk'].total,lang)} {tr(lang,'total').lower()}", width - 4)
    else:
        put(s, y + 3, x + 2, f"{tr(lang,'disk')} [{tr(lang,'unknown')}]: {tr(lang,'unknown')}", width - 4)
    put(s, y + 4, x + 2, tr(lang, "status"), width - 4)


def draw_machine_detail(s: curses.window, lang: str, x: int, y: int, width: int, height: int) -> None:
    data = machine_data()
    box(s, y, x, height, width, tr(lang, "machine"))
    row = y + 2
    if data["mem"]:
        total, free, used = data["mem"]
        put(s, row, x + 2, f"{tr(lang,'memory')} [{tr(lang,'measured')}]: {hb(total,lang)} {tr(lang,'total').lower()} · {hb(free,lang)} {tr(lang,'free').lower()} · {hb(used,lang)} {tr(lang,'used').lower()}", width - 4); row += 2
    if data["cpu"]:
        load, cores = data["cpu"]
        put(s, row, x + 2, f"{tr(lang,'cpu')} [{tr(lang,'measured')}]: {load:.2f} {tr(lang,'load')} · {cores} {tr(lang,'logical')}", width - 4); row += 2
    if data["disk"]:
        put(s, row, x + 2, f"{tr(lang,'disk')} [{tr(lang,'measured')}]: {hb(data['disk'].free,lang)} {tr(lang,'free').lower()} / {hb(data['disk'].total,lang)} {tr(lang,'total').lower()}", width - 4); row += 2
    put(s, row, x + 2, f"{tr(lang,'top_mem')} [{tr(lang,'measured')}]", width - 4); row += 1
    for line in data["memtop"]:
        put(s, row, x + 2, line, width - 4); row += 1
    row += 1
    put(s, row, x + 2, f"{tr(lang,'top_cpu')} [{tr(lang,'measured')}]", width - 4); row += 1
    for line in data["cputop"]:
        if row >= y + height - 2: break
        put(s, row, x + 2, line, width - 4); row += 1


def machine_screen(s: curses.window, lang: str) -> None:
    """Compatibility entry point for the detailed machine-state view."""
    s.erase(); height, width = s.getmaxyx()
    draw_machine_detail(s, lang, 1, 1, width - 2, height - 3)
    put(s, height - 2, 3, tr(lang, "back") + " · " + tr(lang, "quit"), width - 6)
    s.refresh()
    while True:
        key = s.getch()
        if key in (ord("b"), ord("B"), 10, 13): return
        if key in (ord("q"), ord("Q")): raise SystemExit(0)


def draw_workspace(s: curses.window, phase: int, purposes: list[str], models: list[dict], selected: set[int], solution: str, cursor: int, navfocus: bool, navidx: int, lang: str) -> None:
    s.erase(); height, total_width = s.getmaxyx()
    if height < 25 or total_width < 92:
        put(s, 1, 2, "LEONES RC4 · " + tr(lang, "unknown"), total_width - 4); s.refresh(); return
    nav_width = 26; main_x = nav_width + 2; main_width = total_width - main_x - 2
    title = "LEONES // AI OPERATING SYSTEM v4"
    put(s, 0, max(2, (total_width - len(title)) // 2), title, total_width - 4)
    nav_draw(s, lang, navidx, navfocus, phase, nav_width, height)
    phase_key = "purposes" if phase == 0 else "models" if phase == 1 else "solution" if phase == 2 else "cost" if phase == 3 else "confirm"
    put(s, 2, main_x, tr(lang, "workspace") + " · " + tr(lang, "focus") + ": " + (tr(lang, "nav") if navfocus else tr(lang, phase_key).lower()), main_width)
    system_summary(s, lang, main_x, 4, main_width)
    content_y = 11; content_h = height - 14
    box(s, content_y, main_x, content_h, main_width, tr(lang, phase_key))
    row = content_y + 2
    if phase == 0:
        put(s, row, main_x + 2, tr(lang, "purpose_prompt"), main_width - 4); row += 2
        for i, purpose in enumerate(PURPOSES):
            put(s, row + i, main_x + 4, (">" if i == cursor and not navfocus else " ") + (" [X] " if purpose in purposes else " [ ] ") + tr(lang, purpose), main_width - 8)
    elif phase == 1:
        put(s, row, main_x + 2, tr(lang, "models_prompt"), main_width - 4); row += 2
        if not models: put(s, row, main_x + 4, tr(lang, "unknown_gate"), main_width - 8)
        for i, model in enumerate(models):
            size = model_cost(model); mark = "[X]" if i in selected else "[ ]"
            put(s, row + i, main_x + 4, (">" if i == cursor and not navfocus else " ") + f" {mark} {str(model.get('model_id','?'))[:48]}  DISCO={hb(size,lang)} [{provenance(size,lang)}]", main_width - 8)
    elif phase == 2:
        put(s, row, main_x + 2, tr(lang, "solution_prompt"), main_width - 4); row += 2
        for i, key in enumerate(SOLUTIONS):
            put(s, row + i, main_x + 4, (">" if i == cursor and not navfocus else " ") + " " + tr(lang, key), main_width - 8)
        desc, functions, usage = solution_info(solution, lang)
        put(s, row + 5, main_x + 2, desc, main_width - 4)
        put(s, row + 7, main_x + 2, tr(lang, "functions") + ": " + "; ".join(functions), main_width - 4)
        put(s, row + 9, main_x + 2, tr(lang, "usage") + ": " + usage, main_width - 4)
    elif phase == 3:
        data = machine_data(); required = aggregate(models, selected, solution); free = data["disk"].free if data["disk"] else None
        status = tr(lang, "sufficient") if required is not None and free is not None and free >= required else tr(lang, "insufficient") if required is not None and free is not None else tr(lang, "unknown")
        put(s, row, main_x + 2, tr(lang, "cost"), main_width - 4); row += 2
        for i in sorted(selected):
            size = model_cost(models[i]); put(s, row, main_x + 4, f"{models[i].get('model_id','?')}: {hb(size,lang)} [{provenance(size,lang)}]", main_width - 8); row += 1
        put(s, row + 1, main_x + 2, f"MODELOS + {tr(lang,'solution')}: {hb(required,lang)} · {tr(lang,'disk')} {status}", main_width - 4)
        put(s, row + 3, main_x + 2, f"{tr(lang,'disk')} {tr(lang,'free').lower()}: {hb(free,lang)} [{tr(lang,'measured')}]")
        put(s, row + 5, main_x + 2, tr(lang, "unknown_gate"), main_width - 4)
    else:
        required = aggregate(models, selected, solution); data = machine_data(); free = data["disk"].free if data["disk"] else None
        status = tr(lang, "sufficient") if required is not None and free is not None and free >= required else tr(lang, "insufficient") if required is not None and free is not None else tr(lang, "unknown")
        put(s, row, main_x + 2, tr(lang, "confirm"), main_width - 4); row += 2
        put(s, row, main_x + 4, tr(lang, "purpose_prompt") + " " + ", ".join(tr(lang, p) for p in purposes), main_width - 8); row += 1
        put(s, row, main_x + 4, tr(lang, "models_count", n=len(selected)), main_width - 8); row += 1
        put(s, row, main_x + 4, f"{tr(lang,'solution')}: {tr(lang, solution)}", main_width - 8); row += 1
        put(s, row, main_x + 4, f"{tr(lang,'disk')}: {status} · {tr(lang,'required').lower()}={hb(required,lang)} · {tr(lang,'free').lower()}={hb(free,lang)}", main_width - 8); row += 2
        put(s, row, main_x + 4, tr(lang, "consent"), main_width - 8); row += 2
        put(s, row, main_x + 4, tr(lang, "no_install"), main_width - 8)
    put(s, height - 2, 3, tr(lang, "move") + " · " + tr(lang, "space") + " · " + tr(lang, "enter") + " · " + tr(lang, "back") + " · " + tr(lang, "quit"), total_width - 6)
    s.refresh()


def language_screen(s: curses.window) -> str:
    languages = ("es", "en", "zh"); index = 0
    while True:
        s.erase(); height, width = s.getmaxyx(); bw = min(70, width - 4); x = max(1, (width - bw) // 2)
        box(s, 3, x, 12, bw, "LEONES RC4"); lang = languages[index]
        put(s, 5, x + 4, tr(lang, "language"), bw - 8)
        for i, key in enumerate(languages): put(s, 8 + i, x + 8, (">" if i == index else " ") + f" {i+1}. {tr(lang,key)}", bw - 16)
        put(s, 12, x + 4, tr(lang, "move") + " · ENTER", bw - 8); s.refresh(); key = s.getch()
        if key in (curses.KEY_UP, ord("k")): index = (index - 1) % 3
        elif key in (curses.KEY_DOWN, ord("j")): index = (index + 1) % 3
        elif key in (10, 13, ord("1"), ord("2"), ord("3")):
            if key in (ord("1"), ord("2"), ord("3")): index = key - ord("1")
            return languages[index]
        elif key in (ord("q"), ord("Q")): raise SystemExit(0)


def main() -> int:
    def app(s: curses.window) -> None:
        curses.curs_set(0); s.keypad(True)
        lang = language_screen(s)
        phase = 0; purposes: list[str] = []; models: list[dict] = []; selected: set[int] = set()
        solution = "personal_assistant"; cursor = 0; navfocus = False; navidx = 0
        while True:
            draw_workspace(s, phase, purposes, models, selected, solution, cursor, navfocus, navidx, lang)
            key = s.getch()
            if key in (ord("q"), ord("Q")): return
            if key == 9:
                navfocus = not navfocus; continue
            if navfocus:
                if key in (curses.KEY_UP, ord("k")): navidx = (navidx - 1) % len(NAV_ITEMS)
                elif key in (curses.KEY_DOWN, ord("j")): navidx = (navidx + 1) % len(NAV_ITEMS)
                elif key in (10, 13):
                    target = NAV_ITEMS[navidx]
                    if target == "exit": return
                    if target == "machine":
                        machine_screen(s, lang); navfocus = True
                    elif target == "intent": phase = 0; cursor = 0; navfocus = False
                    elif target == "recommender": phase = 1 if models else 0; cursor = 0; navfocus = False
                    elif target == "dashboard": phase = 2 if models else 0; cursor = 0; navfocus = False
                    elif target == "evidence": phase = 3 if models else 0; cursor = 0; navfocus = False
                    elif target == "settings": navfocus = False
                continue
            if phase == 0:
                if key in (curses.KEY_UP, ord("k")): cursor = (cursor - 1) % len(PURPOSES)
                elif key in (curses.KEY_DOWN, ord("j")): cursor = (cursor + 1) % len(PURPOSES)
                elif key == ord(" "):
                    p = PURPOSES[cursor]; purposes.remove(p) if p in purposes else purposes.append(p)
                elif key in (10, 13) and purposes:
                    models = recommend(purposes); selected = set(); cursor = 0; phase = 1
            elif phase == 1:
                if key in (curses.KEY_UP, ord("k")) and models: cursor = (cursor - 1) % len(models)
                elif key in (curses.KEY_DOWN, ord("j")) and models: cursor = (cursor + 1) % len(models)
                elif key == ord(" ") and models: selected.remove(cursor) if cursor in selected else selected.add(cursor)
                elif key in (ord("r"), ord("R")): models = recommend(purposes); selected = set(); cursor = 0
                elif key in (10, 13) and selected: phase = 2; cursor = SOLUTIONS.index(solution)
                elif key in (ord("b"), ord("B")): phase = 0; cursor = 0
            elif phase == 2:
                if key in (curses.KEY_UP, ord("k")): cursor = (cursor - 1) % len(SOLUTIONS); solution = SOLUTIONS[cursor]
                elif key in (curses.KEY_DOWN, ord("j")): cursor = (cursor + 1) % len(SOLUTIONS); solution = SOLUTIONS[cursor]
                elif key in (10, 13): phase = 3; cursor = 0
                elif key in (ord("b"), ord("B")): phase = 1; cursor = 0
            elif phase == 3:
                if key in (ord("b"), ord("B")): phase = 2; cursor = SOLUTIONS.index(solution)
                elif key in (10, 13): phase = 4; cursor = 0
            else:
                if key in (ord("b"), ord("B")): phase = 3
                elif key in (10, 13): pass
    curses.wrapper(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
