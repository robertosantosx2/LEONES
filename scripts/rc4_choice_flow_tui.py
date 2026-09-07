#!/usr/bin/env python3
"""RC4 human-choice flow with the canonical retro TUI shell.

Flow: language -> machine state -> purposes -> models -> solution -> costs -> consent.
The TUI informs and calculates. It never installs anything. Model choice is
uncapped; installation remains unauthorized until explicit confirmation.
"""
from __future__ import annotations

import curses
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDER = ROOT / "scripts" / "rc4_fitllm_recommend.py"
CATALOG = ROOT / "catalogs" / "rc4_solutions.json"
PURPOSES = (("programming", "PROGRAMMING"), ("reasoning", "REASONING"), ("research", "RESEARCH"), ("chat", "CHAT"), ("multimodal", "MULTIMODAL"), ("embedding", "EMBEDDING"), ("general", "GENERAL"))
SOLUTIONS = (("personal_assistant", "PERSONAL AI ASSISTANT"), ("soho", "FULL SOHO"), ("both", "BOTH"))

T = {
    "es": {"select":"SELECCIONA IDIOMA", "keys":"↑/↓ · ENTER", "nav":"NAVEGACIÓN", "dash":"Panel", "machine":"Estado de máquina", "intent":"Intención", "rec":"Recomendador", "evidence":"Evidencia", "legacy":"RC2 legado", "settings":"Configuración", "exit":"Salir", "status":"ESTADO DEL SISTEMA", "network":"RED: ACTIVA", "runtime":"RUNTIME: llama.cpp / límite de medición local", "evidence_line":"EVIDENCIA: HF + Artificial Analysis / ESTIMADA", "workspace":"ESPACIO DE TRABAJO RC4", "footer":"TAB navegación  ↑/↓ mover  ESPACIO seleccionar  ENTER continuar  B volver  R repetir  Q salir", "nav_help":"TAB entrar/salir de navegación  ↑/↓ mover  ENTER abrir  B volver  Q salir", "small":"LEONES RC4 TUI -- terminal demasiado pequeña (mín. 92x25)", "resize":"Redimensiona la ventana. Q: salir"},
    "en": {"select":"SELECT LANGUAGE", "keys":"↑/↓ · ENTER", "nav":"NAVIGATION", "dash":"Dashboard", "machine":"Machine State", "intent":"Intent", "rec":"Recommender", "evidence":"Evidence", "legacy":"RC2 legacy", "settings":"Settings", "exit":"Exit", "status":"SYSTEM STATUS", "network":"NETWORK: UP", "runtime":"RUNTIME: llama.cpp / local measurement boundary", "evidence_line":"EVIDENCE: HF + Artificial Analysis / ESTIMATED", "workspace":"RC4 WORKSPACE", "footer":"TAB navigation  ↑/↓ move  SPACE select  ENTER continue  B back  R rerun  Q quit", "nav_help":"TAB enter/leave navigation  ↑/↓ move  ENTER open  B back  Q quit", "small":"LEONES RC4 TUI -- terminal too small (min 92x25)", "resize":"Resize the window. Q: quit"},
    "zh": {"select":"选择语言", "keys":"↑/↓ · ENTER", "nav":"导航", "dash":"仪表板", "machine":"机器状态", "intent":"意图", "rec":"推荐器", "evidence":"证据", "legacy":"RC2 旧版", "settings":"设置", "exit":"退出", "status":"系统状态", "network":"网络：正常", "runtime":"运行时：llama.cpp / 本地测量边界", "evidence_line":"证据：HF + Artificial Analysis / 估算", "workspace":"RC4 工作区", "footer":"TAB 导航  ↑/↓移动  空格选择  ENTER继续  B返回  R重试  Q退出", "nav_help":"TAB 进入/离开导航  ↑/↓移动  ENTER打开  B返回  Q退出", "small":"LEONES RC4 TUI -- 终端太小（最小 92x25）", "resize":"请调整窗口大小。Q：退出"},
}


def tr(language: str, key: str) -> str:
    return T.get(language, T["es"]).get(key, key)


def human_bytes(value: int | None) -> str:
    if value is None: return "UNKNOWN"
    n = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB": return f"{n:.1f} {unit}"
        n /= 1024
    return "UNKNOWN"


def disk_free() -> int | None:
    try: return shutil.disk_usage(ROOT).free
    except OSError: return None


def run_recommendation(purposes: list[str]) -> dict:
    cmd = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes: cmd += ["--purpose", purpose]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False, timeout=90)
        return json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"status": "unavailable", "recommendations": [], "message": "Recommendation unavailable."}


def model_cost(row: dict) -> tuple[int | None, dict]:
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    candidates = (raw.get("size_bytes"), raw.get("disk_bytes"), raw.get("size"), raw.get("disk_size_bytes"))
    size = next((v for v in candidates if isinstance(v, int) and v >= 0), None)
    return size, {"artifact_bytes": size, "runtime_dependencies": None, "data": None, "margin": None, "state": "ESTIMATED" if size is not None else "UNKNOWN"}


def aggregate(selected: list[dict], solution: str) -> tuple[int | None, list[dict]]:
    details = []; known = True; total = 0
    for row in selected:
        size, detail = model_cost(row); details.append(detail)
        if size is None: known = False
        else: total += size
    try: catalog = json.loads(CATALOG.read_text())
    except (OSError, json.JSONDecodeError): catalog = {"solutions": {}}
    keys = ["personal_assistant", "soho"] if solution == "both" else [solution]
    for key in keys:
        value = catalog.get("solutions", {}).get(key, {}).get("disk_bytes")
        if not isinstance(value, int): known = False
        else: total += value
    return (total if known else None), details


def add_box(stdscr, y: int, x: int, h: int, w: int, title: str) -> None:
    if h < 3 or w < 4: return
    stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
    for row in range(y + 1, y + h - 1): stdscr.addstr(row, x, "|"); stdscr.addstr(row, x + w - 1, "|")
    stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
    label = "[ " + title + " ]"
    if len(label) < w - 4: stdscr.addstr(y, x + 2, label)


def put(stdscr, y: int, x: int, text: str, width: int) -> None:
    if width > 0 and 0 <= y < stdscr.getmaxyx()[0]:
        try: stdscr.addstr(y, x, text[:width])
        except curses.error: pass


def language_screen(stdscr) -> str:
    focus = 0; languages = (("es", "Español"), ("en", "English"), ("zh", "中文"))
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx(); box_w = min(70, max(40, w - 4)); x = max(1, (w - box_w) // 2)
        add_box(stdscr, 3, x, 12, box_w, "LEONES RC4")
        put(stdscr, 5, x + 4, tr(languages[focus][0], "select"), box_w - 8)
        for i, (_, label) in enumerate(languages): put(stdscr, 8 + i, x + 8, f"{'>' if i == focus else ' '} [{i + 1}] {label}", box_w - 16)
        put(stdscr, 12, x + 4, tr(languages[focus][0], "keys"), box_w - 8)
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")): focus = (focus - 1) % 3
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus + 1) % 3
        elif key in (10, 13, ord("1"), ord("2"), ord("3")):
            if key in (ord("1"), ord("2"), ord("3")): focus = int(chr(key)) - 1
            return languages[focus][0]
        elif key in (ord("q"), ord("Q")): raise SystemExit(0)


def machine_state_screen(stdscr, language: str) -> None:
    while True:
        stdscr.erase(); h, w = stdscr.getmaxyx()
        if h < 25 or w < 92:
            put(stdscr, 1, 2, tr(language, "small"), w - 4); put(stdscr, 3, 2, tr(language, "resize"), w - 4); stdscr.refresh()
            if stdscr.getch() in (ord("q"), ord("Q")): raise SystemExit(0)
            continue
        title = {"es":"LEONES // ESTADO DE LA MÁQUINA", "en":"LEONES // MACHINE STATE", "zh":"LEONES // 机器状态"}[language]
        add_box(stdscr, 1, 1, h - 4, w - 2, title); put(stdscr, 3, 4, "Hardware / recursos disponibles", w - 8)
        try:
            free = shutil.disk_usage(ROOT).free; total = shutil.disk_usage(ROOT).total
            put(stdscr, 5, 4, f"DISCO LIBRE   {human_bytes(free)} / {human_bytes(total)}", w - 8)
        except OSError: put(stdscr, 5, 4, "DISCO LIBRE   UNKNOWN", w - 8)
        put(stdscr, 7, 4, "RUNTIME        llama.cpp / medición local", w - 8)
        put(stdscr, 9, 4, "EVIDENCIA      Hugging Face + Artificial Analysis / ESTIMATED", w - 8)
        put(stdscr, h - 7, 4, "La máquina ya está medida; no se vuelve a medir aquí.", w - 8)
        put(stdscr, h - 5, 4, "[ENTER] continuar   [Q] salir", w - 8); stdscr.refresh()
        key = stdscr.getch()
        if key in (ord("q"), ord("Q")): raise SystemExit(0)
        if key in (10, 13): return


def draw(stdscr, phase: int, purposes: list[str], models: list[dict], selected: set[int], solution: str, focus: int, nav_focus: bool, nav_index: int, language: str) -> None:
    stdscr.erase(); height, width = stdscr.getmaxyx()
    if height < 25 or width < 92:
        put(stdscr, 1, 2, tr(language, "small"), width - 4); put(stdscr, 3, 2, tr(language, "resize"), width - 4); stdscr.refresh(); return
    title = "LEONES // AI OPERATING SYSTEM v4"; put(stdscr, 0, max(2, (width - len(title)) // 2), title, len(title))
    left_w = 27; right_x = left_w + 3; right_w = width - right_x - 2; top_h = 7; bottom_y = top_h + 2; main_h = height - bottom_y - 2
    nav_title = tr(language, "nav") + (" <FOCUS>" if nav_focus else "")
    add_box(stdscr, 1, 1, height - 3, left_w, nav_title)
    nav = [tr(language, "dash"), tr(language, "machine"), tr(language, "intent"), tr(language, "rec"), tr(language, "evidence"), tr(language, "legacy"), tr(language, "settings"), tr(language, "exit")]
    put(stdscr, 3, 4, ("> " if nav_focus and nav_index == 0 else "[X] ") + "LEONES RC4", left_w - 6)
    for i, item in enumerate(nav[:5]): put(stdscr, 4 + i, 6, ("> " if nav_focus and nav_index == i + 1 else "-> ") + item, left_w - 8)
    put(stdscr, 10, 4, ("> " if nav_focus and nav_index == 6 else "[ ] ") + tr(language, "legacy"), left_w - 6)
    put(stdscr, 12, 4, ("> " if nav_focus and nav_index == 7 else "[ ] ") + tr(language, "settings"), left_w - 6)
    put(stdscr, 14, 4, ("> " if nav_focus and nav_index == 8 else "[ ] ") + tr(language, "exit"), left_w - 6)
    add_box(stdscr, 1, right_x, top_h, right_w, tr(language, "status")); put(stdscr, 3, right_x + 3, tr(language, "network"), right_w - 6); put(stdscr, 4, right_x + 3, tr(language, "runtime"), right_w - 6); put(stdscr, 5, right_x + 3, tr(language, "evidence_line"), right_w - 6)
    add_box(stdscr, bottom_y, right_x, main_h, right_w, tr(language, "workspace")); inner_x = right_x + 3; content_w = right_w - 6
    labels = ["1 PROPÓSITOS", "2 MODELOS", "3 SOLUCIÓN", "4 COSTES", "5 CONFIRMACIÓN"]
    put(stdscr, bottom_y + 2, inner_x, "  ".join((">" if i == phase else " ") + x for i, x in enumerate(labels)), content_w)
    row = bottom_y + 4
    if phase == 0:
        put(stdscr, row, inner_x, "Selecciona uno o varios propósitos:", content_w); row += 2
        for i, (key, name) in enumerate(PURPOSES): put(stdscr, row + i, inner_x, f"{'>' if i == focus and not nav_focus else ' '} [{'X' if key in purposes else ' '}] {name}", content_w)
        put(stdscr, row + len(PURPOSES) + 1, inner_x, "↑/↓ mover · ESPACIO seleccionar · ENTER continuar", content_w)
    elif phase == 1:
        put(stdscr, row, inner_x, "Modelos compatibles / recomendados · selección múltiple · sin límite artificial:", content_w); row += 2
        if not models: put(stdscr, row, inner_x, "Sin candidatos disponibles; B para volver y cambiar propósitos.", content_w)
        for i, model in enumerate(models):
            size, _ = model_cost(model); put(stdscr, row + i, inner_x, f"{'>' if i == focus and not nav_focus else ' '} [{'X' if i in selected else ' '}] {i + 1:>2} {str(model.get('model_id', '?'))[:44]}  DISCO={human_bytes(size)}  ESTIMATED", content_w)
        put(stdscr, row + max(8, len(models)) + 1, inner_x, "↑/↓ mover · ESPACIO seleccionar · ENTER continuar · R recalcular", content_w)
    elif phase == 2:
        put(stdscr, row, inner_x, "¿Qué quieres instalar?", content_w); row += 2
        for i, (_, name) in enumerate(SOLUTIONS): put(stdscr, row + i, inner_x, f"{'>' if i == focus and not nav_focus else ' '} {name}", content_w)
        put(stdscr, row + 5, inner_x, "↑/↓ elegir · ENTER continuar · B volver", content_w)
    elif phase == 3:
        required, _ = aggregate([models[i] for i in sorted(selected)], solution); free = disk_free(); state = "UNKNOWN" if required is None or free is None else ("SUFICIENTE" if free >= required else "INSUFICIENTE")
        put(stdscr, row, inner_x, "COSTE DE LA SELECCIÓN", content_w); row += 2
        for i in sorted(selected):
            size, _ = model_cost(models[i]); put(stdscr, row, inner_x, f"{models[i].get('model_id', '?')}: artefacto {human_bytes(size)}  [ESTIMATED/UNKNOWN]", content_w); row += 1
        put(stdscr, row + 1, inner_x, f"MODELOS + SOLUCIÓN: {human_bytes(required)}", content_w); row += 3; put(stdscr, row, inner_x, f"DISCO LIBRE ACTUAL: {human_bytes(free)}", content_w); row += 1; put(stdscr, row, inner_x, f"GATE DISCO: {state}  ·  instalación autorizada: NO", content_w); row += 2
        put(stdscr, row, inner_x, "UNKNOWN no pasa el gate · no se instala parcialmente por defecto.", content_w); put(stdscr, row + 2, inner_x, "ENTER continuar · B volver", content_w)
    else:
        required, _ = aggregate([models[i] for i in sorted(selected)], solution); free = disk_free(); state = "SUFICIENTE" if required is not None and free is not None and free >= required else ("UNKNOWN" if required is None or free is None else "INSUFICIENTE")
        put(stdscr, row, inner_x, "CONFIRMACIÓN EXPLÍCITA", content_w); row += 2; put(stdscr, row, inner_x, f"Propósitos: {', '.join(purposes)}", content_w); row += 1; put(stdscr, row, inner_x, f"Modelos: {len(selected)} seleccionado(s), sin límite artificial", content_w); row += 1; put(stdscr, row, inner_x, f"Solución: {solution.upper()}", content_w); row += 1; put(stdscr, row, inner_x, f"Disco: {state} · requerido={human_bytes(required)} · libre={human_bytes(free)}", content_w); row += 2
        put(stdscr, row, inner_x, "[ENTER] CONFIRMAR INSTALACIÓN  ·  [B] volver  ·  [Q] salir", content_w); row += 2; put(stdscr, row, inner_x, "La confirmación aún NO ejecuta aquí: esta capa registra consentimiento y delega al instalador autorizado.", content_w)
    put(stdscr, height - 2, 2, tr(language, "nav_help") if nav_focus else tr(language, "footer"), width - 4); stdscr.refresh()


def main() -> int:
    state = {"phase": 0, "purposes": [], "models": [], "selected": set(), "solution": "personal_assistant", "focus": 0, "nav_focus": False, "nav_index": 0, "language": "es"}
    def app(stdscr):
        curses.curs_set(0); stdscr.keypad(True); state["language"] = language_screen(stdscr); machine_state_screen(stdscr, state["language"])
        while True:
            draw(stdscr, state["phase"], state["purposes"], state["models"], state["selected"], state["solution"], state["focus"], state["nav_focus"], state["nav_index"], state["language"])
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")): return
            if key == 9: state["nav_focus"] = not state["nav_focus"]; continue
            if state["nav_focus"]:
                if key in (curses.KEY_UP, ord("k")): state["nav_index"] = (state["nav_index"] - 1) % 9
                elif key in (curses.KEY_DOWN, ord("j")): state["nav_index"] = (state["nav_index"] + 1) % 9
                elif key in (10, 13):
                    if state["nav_index"] == 8: return
                    if state["nav_index"] == 0: state["nav_focus"] = False
                    elif state["nav_index"] == 1: machine_state_screen(stdscr, state["language"]); state["nav_focus"] = False
                    elif state["nav_index"] == 2: state["phase"] = 0; state["focus"] = 0; state["nav_focus"] = False
                    elif state["nav_index"] == 3: state["nav_focus"] = False
                    elif state["nav_index"] == 4: state["nav_focus"] = False
                    elif state["nav_index"] in (5, 6): state["nav_focus"] = False
                elif key in (ord("b"), ord("B")): state["nav_focus"] = False
                continue
            phase = state["phase"]
            if key in (ord("b"), ord("B")):
                if phase > 0: state["phase"] -= 1; state["focus"] = 0
                continue
            if phase == 0:
                if key in (curses.KEY_UP, ord("k")): state["focus"] = (state["focus"] - 1) % len(PURPOSES)
                elif key in (curses.KEY_DOWN, ord("j")): state["focus"] = (state["focus"] + 1) % len(PURPOSES)
                elif key == ord(" "):
                    p = PURPOSES[state["focus"]][0]; state["purposes"].remove(p) if p in state["purposes"] else state["purposes"].append(p)
                elif key in (10, 13) and state["purposes"]:
                    result = run_recommendation(state["purposes"]); state["models"] = result.get("recommendations") or []; state["selected"] = set(); state["focus"] = 0; state["phase"] = 1
            elif phase == 1:
                if state["models"]:
                    if key in (curses.KEY_UP, ord("k")): state["focus"] = (state["focus"] - 1) % len(state["models"])
                    elif key in (curses.KEY_DOWN, ord("j")): state["focus"] = (state["focus"] + 1) % len(state["models"])
                    elif key == ord(" "): state["selected"].remove(state["focus"]) if state["focus"] in state["selected"] else state["selected"].add(state["focus"])
                    elif key in (ord("r"), ord("R")):
                        result = run_recommendation(state["purposes"]); state["models"] = result.get("recommendations") or []; state["selected"] = set(); state["focus"] = 0
                    elif key in (10, 13) and state["selected"]: state["phase"] = 2; state["focus"] = next((i for i, (k, _) in enumerate(SOLUTIONS) if k == state["solution"]), 0)
            elif phase == 2:
                if key in (curses.KEY_UP, ord("k")): state["focus"] = (state["focus"] - 1) % len(SOLUTIONS)
                elif key in (curses.KEY_DOWN, ord("j")): state["focus"] = (state["focus"] + 1) % len(SOLUTIONS)
                elif key in (10, 13): state["solution"] = SOLUTIONS[state["focus"]][0]; state["phase"] = 3; state["focus"] = 0
            elif phase == 3:
                if key in (10, 13): state["phase"] = 4
            else:
                if key in (10, 13):
                    # Deliberately no installer call in this milestone.
                    state["phase"] = 4
    curses.wrapper(app); return 0


if __name__ == "__main__": raise SystemExit(main())
