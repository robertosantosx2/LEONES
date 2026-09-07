#!/usr/bin/env python3
"""RC4 human-choice flow: language -> machine -> purposes -> models -> solution -> cost -> consent."""
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

PURPOSES = (
    ("programming", "programming"), ("reasoning", "reasoning"),
    ("research", "research"), ("chat", "chat"),
    ("multimodal", "multimodal"), ("embedding", "embedding"),
    ("general", "general"),
)
SOLUTIONS = (
    ("personal_assistant", "personal"),
    ("soho", "soho"),
    ("both", "both"),
)

T = {
    "es": {
        "select":"SELECCIONA IDIOMA", "keys":"↑/↓ · ENTER", "nav":"NAVEGACIÓN", "dash":"Panel",
        "machine":"Estado de máquina", "intent":"Intención", "rec":"Recomendador", "evidence":"Evidencia",
        "legacy":"RC2 legado", "settings":"Configuración", "exit":"Salir", "small":"LEONES RC4 TUI -- terminal demasiado pequeña (mín. 92x25)",
        "resize":"Redimensiona la ventana. Q: salir", "system":"ESTADO DEL SISTEMA", "workspace":"ESPACIO DE TRABAJO RC4",
        "focus":"FOCUS", "unknown":"UNKNOWN", "purpose_title":"PROPÓSITOS", "purpose_prompt":"Selecciona uno o varios propósitos:",
        "models_title":"MODELOS", "models_prompt":"MODELOS COMPATIBLES / RECOMENDADOS · SELECCIÓN MÚLTIPLE · SIN LÍMITE ARTIFICIAL",
        "solution_title":"SOLUCIÓN", "solution_prompt":"↑/↓ CAMBIA LA OPCIÓN Y ACTUALIZA SU FICHA", "cost_title":"COSTE DE LA SELECCIÓN",
        "confirm_title":"CONFIRMACIÓN EXPLÍCITA", "functions":"FUNCIONALIDADES:", "usage":"USO HABITUAL:", "install":"INSTALACIÓN:",
        "declared":"DECLARADO", "estimated":"ESTIMADO", "measured":"MEDIDO", "selected":"seleccionado(s)", "disk":"DISCO", "ram":"RAM",
        "cpu":"CPU", "vram":"VRAM", "required":"requerido", "free":"libre", "sufficient":"SUFICIENTE", "insufficient":"INSUFICIENTE",
        "gate":"GATE DISCO", "authorized":"INSTALACIÓN AUTORIZADA=NO", "unknown_gate":"UNKNOWN no pasa el gate · no instalación parcial por defecto",
        "continue":"[ENTER] continuar", "quit":"[Q] salir", "back":"B volver", "move":"↑/↓ mover", "choose":"↑/↓ elegir",
        "space":"ESPACIO seleccionar", "recalc":"R recalcular", "tab":"TAB navegación", "open":"ENTER abrir/continuar",
        "no_install":"NO ejecuta instalación en esta capa", "consent":"ENTER = registrar consentimiento", "memory":"MEMORIA", "total":"TOTAL",
        "available":"LIBRE", "used":"EN USO", "load":"carga 1m", "logical":"lógico", "cpus":"CPUs", "top_mem":"TOP 5 PROCESOS · MEMORIA",
        "top_cpu":"TOP 5 PROCESOS · CPU", "disk_state":"DISCO", "solution_desc":"DESCRIPCIÓN", "components":"COMPONENTES",
        "models_count":"Modelos: {n} seleccionado(s), sin límite artificial", "purposes":"Propósitos: {v}", "solution":"Solución: {v}",
        "both":"PERSONAL + SOHO", "programming":"PROGRAMMING", "reasoning":"REASONING", "research":"RESEARCH", "chat":"CHAT",
        "multimodal":"MULTIMODAL", "embedding":"EMBEDDING", "general":"GENERAL", "personal":"PERSONAL AI ASSISTANT", "soho":"FULL SOHO",
        "personal_desc":"Asistente personal local para un usuario principal.", "soho_desc":"Servicios de IA locales para varios usuarios y servicios compartidos.",
        "personal_functions":"chat local; asistencia personal; acceso a modelos seleccionados; documentos y contexto locales; interacción local de un solo usuario",
        "soho_functions":"servicio multiusuario; servicios de IA locales; acceso a modelos seleccionados; endpoints locales compartidos; operación orientada a servicios",
        "personal_usage":"Uso interactivo y por ráfagas; el consumo depende del modelo, contexto y concurrencia.",
        "soho_usage":"Puede haber uso concurrente y sostenido; el consumo depende de modelos, concurrencia, contexto y servicios.",
    },
    "en": {
        "select":"SELECT LANGUAGE", "keys":"↑/↓ · ENTER", "nav":"NAVIGATION", "dash":"Dashboard", "machine":"Machine State", "intent":"Intent", "rec":"Recommender", "evidence":"Evidence", "legacy":"RC2 legacy", "settings":"Settings", "exit":"Exit", "small":"LEONES RC4 TUI -- terminal too small (min 92x25)", "resize":"Resize the window. Q: quit", "system":"SYSTEM STATE", "workspace":"RC4 WORKSPACE", "focus":"FOCUS", "unknown":"UNKNOWN", "purpose_title":"PURPOSES", "purpose_prompt":"Select one or more purposes:", "models_title":"MODELS", "models_prompt":"COMPATIBLE / RECOMMENDED MODELS · MULTI-SELECTION · NO ARTIFICIAL LIMIT", "solution_title":"SOLUTION", "solution_prompt":"↑/↓ CHANGES THE OPTION AND UPDATES ITS CARD", "cost_title":"SELECTION COST", "confirm_title":"EXPLICIT CONFIRMATION", "functions":"FUNCTIONS:", "usage":"NORMAL USE:", "install":"INSTALLATION:", "declared":"DECLARED", "estimated":"ESTIMATED", "measured":"MEASURED", "selected":"selected", "disk":"DISK", "ram":"RAM", "cpu":"CPU", "vram":"VRAM", "required":"required", "free":"free", "sufficient":"SUFFICIENT", "insufficient":"INSUFFICIENT", "gate":"DISK GATE", "authorized":"INSTALLATION AUTHORIZED=NO", "unknown_gate":"UNKNOWN does not pass the gate · no partial installation by default", "continue":"[ENTER] continue", "quit":"[Q] quit", "back":"B back", "move":"↑/↓ move", "choose":"↑/↓ choose", "space":"SPACE select", "recalc":"R recalculate", "tab":"TAB navigation", "open":"ENTER open/continue", "no_install":"DOES NOT execute installation in this layer", "consent":"ENTER = record consent", "memory":"MEMORY", "total":"TOTAL", "available":"AVAILABLE", "used":"IN USE", "load":"1m load", "logical":"logical", "cpus":"CPUs", "top_mem":"TOP 5 PROCESSES · MEMORY", "top_cpu":"TOP 5 PROCESSES · CPU", "disk_state":"DISK", "solution_desc":"DESCRIPTION", "components":"COMPONENTS", "models_count":"Models: {n} selected, no artificial limit", "purposes":"Purposes: {v}", "solution":"Solution: {v}", "both":"PERSONAL + SOHO", "programming":"PROGRAMMING", "reasoning":"REASONING", "research":"RESEARCH", "chat":"CHAT", "multimodal":"MULTIMODAL", "embedding":"EMBEDDING", "general":"GENERAL", "personal":"PERSONAL AI ASSISTANT", "soho":"FULL SOHO", "personal_desc":"Local personal assistant for one primary user.", "soho_desc":"Local AI services for multiple users and shared services.", "personal_functions":"local chat; personal assistance; selected model access; local documents and context; single-user local interaction", "soho_functions":"multi-user service; local AI services; selected model access; shared local endpoints; service-oriented operation", "personal_usage":"Interactive and bursty use; consumption depends on model, context and concurrency.", "soho_usage":"Concurrent and sustained use is possible; consumption depends on models, concurrency, context and services."},
    "zh": {
        "select":"选择语言", "keys":"↑/↓ · ENTER", "nav":"导航", "dash":"仪表板", "machine":"机器状态", "intent":"意图", "rec":"推荐器", "evidence":"证据", "legacy":"RC2 旧版", "settings":"设置", "exit":"退出", "small":"LEONES RC4 TUI -- 终端太小（最小 92x25）", "resize":"请调整窗口大小。Q：退出", "system":"系统状态", "workspace":"RC4 工作区", "focus":"焦点", "unknown":"未知", "purpose_title":"用途", "purpose_prompt":"选择一个或多个用途：", "models_title":"模型", "models_prompt":"兼容 / 推荐模型 · 多选 · 无人为数量限制", "solution_title":"方案", "solution_prompt":"↑/↓ 更改选项并更新信息", "cost_title":"选择成本", "confirm_title":"明确确认", "functions":"功能：", "usage":"正常使用：", "install":"安装：", "declared":"已声明", "estimated":"估算", "measured":"已测量", "selected":"已选择", "disk":"磁盘", "ram":"内存", "cpu":"CPU", "vram":"显存", "required":"需要", "free":"可用", "sufficient":"足够", "insufficient":"不足", "gate":"磁盘门禁", "authorized":"安装授权=否", "unknown_gate":"未知值不能通过门禁 · 默认不进行部分安装", "continue":"[ENTER] 继续", "quit":"[Q] 退出", "back":"B 返回", "move":"↑/↓ 移动", "choose":"↑/↓ 选择", "space":"空格 选择", "recalc":"R 重新计算", "tab":"TAB 导航", "open":"ENTER 打开/继续", "no_install":"本层不会执行安装", "consent":"ENTER = 记录同意", "memory":"内存", "total":"总计", "available":"可用", "used":"使用中", "load":"1分钟负载", "logical":"逻辑", "cpus":"CPU", "top_mem":"内存占用前5个进程", "top_cpu":"CPU占用前5个进程", "disk_state":"磁盘", "solution_desc":"说明", "components":"组件", "models_count":"模型：已选择 {n} 个，无人为数量限制", "purposes":"用途：{v}", "solution":"方案：{v}", "both":"个人助手 + SOHO", "programming":"编程", "reasoning":"推理", "research":"研究", "chat":"聊天", "multimodal":"多模态", "embedding":"嵌入", "general":"通用", "personal":"个人 AI 助手", "soho":"完整 SOHO", "personal_desc":"面向主要用户的本地个人助手。", "soho_desc":"面向多用户和共享服务的本地 AI 服务。", "personal_functions":"本地聊天；个人助理；访问所选模型；本地文档和上下文；单用户本地交互", "soho_functions":"多用户服务；本地 AI 服务；访问所选模型；共享本地端点；面向服务的运行", "personal_usage":"交互式、突发式使用；资源消耗取决于模型、上下文和并发。", "soho_usage":"可进行并发和持续使用；资源消耗取决于模型、并发、上下文和服务。"},
}

def tr(lang, key, **kwargs):
    return T.get(lang, T["es"]).get(key, key).format(**kwargs)

def human_bytes(value, lang):
    if not isinstance(value, int) or value < 0:
        return tr(lang, "unknown")
    n = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return tr(lang, "unknown")

def catalog():
    try:
        return json.loads(CATALOG.read_text()).get("solutions", {})
    except (OSError, json.JSONDecodeError):
        return {}

def disk_free():
    try:
        return shutil.disk_usage(ROOT).free
    except OSError:
        return None

def model_cost(row):
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    for key in ("size_bytes", "disk_bytes", "size", "disk_size_bytes"):
        value = raw.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None

def run_recommendation(purposes):
    cmd = [sys.executable, str(RECOMMENDER), "--json"]
    for purpose in purposes:
        cmd += ["--purpose", purpose]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False, timeout=90)
        return json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"status": "unavailable", "recommendations": []}

def solution_keys(solution):
    return ["personal_assistant", "soho"] if solution == "both" else [solution]

def solution_text(solution, lang):
    keys = solution_keys(solution)
    data = catalog()
    desc = " ".join(tr(lang, f"{k}_desc") for k in keys)
    funcs = []
    for k in keys:
        funcs.extend(tr(lang, f"{k}_functions").split(";"))
    usage = " ".join(tr(lang, f"{k}_usage") for k in keys)
    return desc, funcs, usage, data

def aggregate(models, solution):
    total = 0
    known = True
    for model in models:
        value = model_cost(model)
        if value is None:
            known = False
        else:
            total += value
    for key in solution_keys(solution):
        value = catalog().get(key, {}).get("disk_bytes")
        if not isinstance(value, int):
            known = False
        else:
            total += value
    return total if known else None

def provenance(value, lang, default="unknown"):
    if isinstance(value, int):
        return tr(lang, "declared")
    if isinstance(value, (float,)):
        return tr(lang, "estimated")
    return tr(lang, default)

def resource_line(info, lang):
    disk = human_bytes(info.get("disk_bytes"), lang)
    ram = human_bytes(info.get("ram_bytes"), lang)
    vram = human_bytes(info.get("vram_bytes"), lang)
    cpu = info.get("cpu_load")
    cpu_text = cpu if isinstance(cpu, (int, float)) else tr(lang, "unknown")
    cpu_prov = tr(lang, "estimated") if isinstance(cpu, (int, float)) else tr(lang, "unknown")
    return f"{tr(lang,'install')} {tr(lang,'disk')}={disk} [{provenance(info.get('disk_bytes'),lang)}] · {tr(lang,'ram')}={ram} [{provenance(info.get('ram_bytes'),lang)}] · {tr(lang,'cpu')}={cpu_text} [{cpu_prov}] · {tr(lang,'vram')}={vram} [{provenance(info.get('vram_bytes'),lang)}]"

def add_box(screen, y, x, height, width, title):
    if height < 3 or width < 4:
        return
    screen.addstr(y, x, "+" + "-" * (width - 2) + "+")
    for row in range(y + 1, y + height - 1):
        screen.addstr(row, x, "|")
        screen.addstr(row, x + width - 1, "|")
    screen.addstr(y + height - 1, x, "+" + "-" * (width - 2) + "+")
    if len(title) + 4 < width:
        screen.addstr(y, x + 2, "[ " + title + " ]")

def put(screen, y, x, text, width):
    if 0 <= y < screen.getmaxyx()[0] and width > 0:
        try:
            screen.addstr(y, x, str(text)[:width])
        except curses.error:
            pass

def language_screen(screen):
    focus = 0
    languages = (("es", "Español"), ("en", "English"), ("zh", "中文"))
    while True:
        screen.erase(); h, w = screen.getmaxyx(); bw = min(70, max(40, w - 4)); x = max(1, (w - bw)//2)
        add_box(screen, 3, x, 12, bw, "LEONES RC4")
        put(screen, 5, x+4, tr(languages[focus][0], "select"), bw-8)
        for i, (_, label) in enumerate(languages):
            put(screen, 8+i, x+8, (">" if i == focus else " ") + f" [{i+1}] {label}", bw-16)
        put(screen, 12, x+4, tr(languages[focus][0], "keys"), bw-8); screen.refresh(); key = screen.getch()
        if key in (curses.KEY_UP, ord("k")): focus = (focus-1) % 3
        elif key in (curses.KEY_DOWN, ord("j")): focus = (focus+1) % 3
        elif key in (10, 13, ord("1"), ord("2"), ord("3")):
            if key in (ord("1"), ord("2"), ord("3")): focus = int(chr(key))-1
            return languages[focus][0]
        elif key in (ord("q"), ord("Q")): raise SystemExit(0)

def machine_state_screen(screen, language):
    while True:
        screen.erase(); h, w = screen.getmaxyx()
        if h < 25 or w < 92:
            put(screen, 1, 2, tr(language,"small"), w-4); put(screen, 3, 2, tr(language,"resize"), w-4); screen.refresh()
            if screen.getch() in (ord("q"), ord("Q")): raise SystemExit(0)
            continue
        title = {"es":"LEONES // ESTADO DE LA MÁQUINA", "en":"LEONES // MACHINE STATE", "zh":"LEONES // 机器状态"}[language]
        add_box(screen, 1, 1, h-4, w-2, title); x=4
        try:
            mem={}
            for line in Path("/proc/meminfo").read_text().splitlines():
                key, rest=line.split(":",1); mem[key]=int(rest.split()[0])*1024
            total=mem["MemTotal"]; available=mem["MemAvailable"]; used=total-available
            put(screen,3,x,f"{tr(language,'memory')} [{tr(language,'measured')}]",w-8)
            put(screen,4,x,f"{tr(language,'total'):10} {human_bytes(total,language)} [{tr(language,'measured')}]",w-8)
            put(screen,5,x,f"{tr(language,'available'):10} {human_bytes(available,language)} [{tr(language,'measured')}]",w-8)
            put(screen,6,x,f"{tr(language,'used'):10} {human_bytes(used,language)} ({used*100//total}%) [{tr(language,'measured')}]",w-8)
        except (OSError,KeyError,ValueError,ZeroDivisionError): put(screen,3,x,f"{tr(language,'memory')} [{tr(language,'unknown')}]",w-8)
        try:
            load=os.getloadavg()[0]; cores=os.cpu_count() or 1
            put(screen,8,x,f"{tr(language,'cpu')} [{tr(language,'measured')}] {tr(language,'load')}={load:.2f} · {load*100/cores:.1f}% {tr(language,'logical')} ({cores} {tr(language,'cpus')})",w-8)
        except OSError: put(screen,8,x,f"{tr(language,'cpu')} [{tr(language,'unknown')}]",w-8)
        try:
            u=shutil.disk_usage(ROOT); put(screen,10,x,f"{tr(language,'disk_state')} [{tr(language,'measured')}] {tr(language,'free')} {human_bytes(u.free,language)} / {tr(language,'total').lower()} {human_bytes(u.total,language)}",w-8)
        except OSError: put(screen,10,x,f"{tr(language,'disk_state')} [{tr(language,'unknown')}]",w-8)
        put(screen,12,x,f"{tr(language,'top_mem')} [{tr(language,'measured')}]",w-8)
        try:
            lines=subprocess.run(["ps","-eo","pid,%mem,rss,comm","--sort=-%mem"],capture_output=True,text=True,check=False,timeout=5).stdout.splitlines()[1:6]
            for i,line in enumerate(lines): put(screen,13+i,x,line,w-8)
        except (OSError,subprocess.TimeoutExpired): put(screen,13,x,tr(language,"unknown"),w-8)
        put(screen,18,x,f"{tr(language,'top_cpu')} [{tr(language,'measured')}]",w-8)
        try:
            lines=subprocess.run(["ps","-eo","pid,%cpu,%mem,comm","--sort=-%cpu"],capture_output=True,text=True,check=False,timeout=5).stdout.splitlines()[1:6]
            for i,line in enumerate(lines): put(screen,19+i,x,line,w-8)
        except (OSError,subprocess.TimeoutExpired): put(screen,19,x,tr(language,"unknown"),w-8)
        put(screen,h-2,x,f"{tr(language,'continue')}   {tr(language,'quit')}",w-8); screen.refresh(); key=screen.getch()
        if key in (ord("q"),ord("Q")): raise SystemExit(0)
        if key in (10,13): return

def draw(screen, phase, purposes, models, selected, solution, cursor, nav_focus, nav_index, language):
    screen.erase(); h,w=screen.getmaxyx()
    if h<25 or w<92:
        put(screen,1,2,tr(language,"small"),w-4); put(screen,3,2,tr(language,"resize"),w-4); screen.refresh(); return
    put(screen,0,max(2,(w-31)//2),"LEONES // AI OPERATING SYSTEM v4",31)
    left=28; rx=left+3; rw=w-rx-2; top=7; by=top+2; mh=h-by-2
    add_box(screen,1,1,h-3,left,tr(language,"nav")+(" <"+tr(language,"focus")+">" if nav_focus else ""))
    nav=[tr(language,k) for k in ("dash","machine","intent","rec","evidence","legacy","settings","exit")]
    put(screen,3,4,("> " if nav_focus and nav_index==0 else "[X] ")+"LEONES RC4",left-6)
    for i,name in enumerate(nav[:5]): put(screen,4+i,6,("> " if nav_focus and nav_index==i+1 else "-> ")+name,left-8)
    for i,name in ((6,nav[5]),(7,nav[6]),(8,nav[7])): put(screen,10+(i-6)*2,4,("> " if nav_focus and nav_index==i else "[ ] ")+name,left-6)
    add_box(screen,1,rx,top,rw,tr(language,"system")); add_box(screen,by,rx,mh,rw,tr(language,"workspace")); x=rx+3; cw=rw-6
    labels=(tr(language,"purpose_title"),tr(language,"models_title"),tr(language,"solution_title"),tr(language,"cost_title"),tr(language,"confirm_title"))
    put(screen,by+2,x,"  ".join((">" if i==phase else " ")+f"{i+1} {v}" for i,v in enumerate(labels)),cw); row=by+4
    if phase==0:
        put(screen,row,x,tr(language,"purpose_prompt"),cw); row+=2
        for i,(key,_) in enumerate(PURPOSES): put(screen,row+i,x,(">" if i==cursor and not nav_focus else " ")+f" [{'X' if key in purposes else ' '}] {tr(language,key)}",cw)
        put(screen,row+len(PURPOSES)+1,x,f"{tr(language,'move')} · {tr(language,'space')} · {tr(language,'continue')}",cw)
    elif phase==1:
        put(screen,row,x,tr(language,"models_prompt"),cw); row+=2
        for i,m in enumerate(models):
            value=model_cost(m); state=tr(language,"declared") if value is not None else tr(language,"unknown")
            put(screen,row+i,x,(">" if i==cursor and not nav_focus else " ")+f" [{'X' if i in selected else ' '}] {i+1:>2} {str(m.get('model_id','?'))[:44]} {tr(language,'disk')}={human_bytes(value,language)} [{state}]",cw)
        put(screen,row+max(8,len(models))+1,x,f"{tr(language,'move')} · {tr(language,'space')} · {tr(language,'continue')} · {tr(language,'recalc')} · {tr(language,'back')}",cw)
    elif phase==2:
        desc,funcs,usage,data=solution_text(solution,language)
        put(screen,row,x,f"{tr(language,'solution_title')} · {tr(language,'solution_prompt')}",cw); row+=2
        for key,label in SOLUTIONS: put(screen,row,x,("> " if key==solution else "  ")+tr(language,label),cw); row+=1
        row+=1; put(screen,row,x,tr(language,"solution_desc"),cw); row+=1; put(screen,row,x,desc,cw); row+=2
        put(screen,row,x,tr(language,"components"),cw); row+=1
        comps=[]
        for key in solution_keys(solution): comps.extend(data.get(key,{}).get("components",[]))
        put(screen,row,x,", ".join(comps) or tr(language,"unknown"),cw); row+=2
        put(screen,row,x,tr(language,"functions"),cw); row+=1
        for function in funcs: put(screen,row,x,"· "+function.strip(),cw); row+=1
        put(screen,row,x,tr(language,"usage")+" "+usage,cw); row+=2
        for key in solution_keys(solution):
            put(screen,row,x,resource_line(data.get(key,{}),language),cw); row+=1
        put(screen,h-3,x,f"{tr(language,'choose')} · {tr(language,'continue')} · {tr(language,'back')}",cw)
    elif phase==3:
        required=aggregate([models[i] for i in sorted(selected)],solution); free=disk_free()
        status=tr(language,"unknown") if required is None or free is None else (tr(language,"sufficient") if free>=required else tr(language,"insufficient"))
        put(screen,row,x,tr(language,"cost_title"),cw); row+=2
        for i in sorted(selected):
            value=model_cost(models[i]); state=tr(language,"declared") if value is not None else tr(language,"unknown")
            put(screen,row,x,f"{models[i].get('model_id','?')}: {human_bytes(value,language)} [{state}]",cw); row+=1
        for key in solution_keys(solution):
            put(screen,row,x,resource_line(catalog().get(key,{}),language),cw); row+=1
        put(screen,row+1,x,f"{tr(language,'required')}={human_bytes(required,language)} · {tr(language,'free')}={human_bytes(free,language)} · {status} [{tr(language,'measured') if free is not None else tr(language,'unknown')} {tr(language,'gate')}]",cw)
        put(screen,row+2,x,tr(language,"authorized"),cw); put(screen,row+4,x,f"{tr(language,'unknown_gate')} · {tr(language,'back')} · {tr(language,'continue')}",cw)
    else:
        required=aggregate([models[i] for i in sorted(selected)],solution); free=disk_free()
        status=tr(language,"sufficient") if required is not None and free is not None and free>=required else (tr(language,"unknown") if required is None or free is None else tr(language,"insufficient"))
        put(screen,row,x,tr(language,"confirm_title"),cw); row+=2
        for line in (tr(language,"purposes",v=", ".join(tr(language,p) for p in purposes)),tr(language,"models_count",n=len(selected)),tr(language,"solution",v=tr(language,"both") if solution=="both" else tr(language,solution)),f"{tr(language,'disk')}: {status} · {tr(language,'required')}={human_bytes(required,language)} · {tr(language,'free')}={human_bytes(free,language)}"):
            put(screen,row,x,line,cw); row+=1
        put(screen,row+2,x,f"{tr(language,'consent')} · {tr(language,'no_install')}",cw); put(screen,row+4,x,f"{tr(language,'back')} · {tr(language,'quit')}",cw)
    put(screen,h-2,3,f"{tr(language,'tab')} · {tr(language,'move')} · {tr(language,'open')} · {tr(language,'back')} · {tr(language,'quit')}",w-6); screen.refresh()

def main():
    def app(screen):
        curses.curs_set(0); screen.keypad(True)
        language=language_screen(screen); machine_state_screen(screen,language)
        phase=0; purposes=[]; models=[]; selected=set(); solution="personal_assistant"; cursor=0; nav_focus=False; nav_index=0
        while True:
            draw(screen,phase,purposes,models,selected,solution,cursor,nav_focus,nav_index,language); key=screen.getch()
            if key in (ord("q"),ord("Q")): return
            if key==9: nav_focus=not nav_focus; continue
            if nav_focus:
                if key in (curses.KEY_UP,ord("k")): nav_index=(nav_index-1)%9
                elif key in (curses.KEY_DOWN,ord("j")): nav_index=(nav_index+1)%9
                elif key in (10,13):
                    if nav_index==8: return
                    if nav_index==2: machine_state_screen(screen,language)
                    nav_focus=False
                continue
            if phase==0:
                if key in (curses.KEY_UP,ord("k")): cursor=(cursor-1)%len(PURPOSES)
                elif key in (curses.KEY_DOWN,ord("j")): cursor=(cursor+1)%len(PURPOSES)
                elif key==ord(" "):
                    purpose=PURPOSES[cursor][0]; purposes.remove(purpose) if purpose in purposes else purposes.append(purpose)
                elif key in (10,13) and purposes: models=run_recommendation(purposes).get("recommendations") or []; selected=set(); cursor=0; phase=1
            elif phase==1:
                if models and key in (curses.KEY_UP,ord("k")): cursor=(cursor-1)%len(models)
                elif models and key in (curses.KEY_DOWN,ord("j")): cursor=(cursor+1)%len(models)
                elif models and key==ord(" "): selected.remove(cursor) if cursor in selected else selected.add(cursor)
                elif key in (ord("r"),ord("R")): models=run_recommendation(purposes).get("recommendations") or []; selected=set(); cursor=0
                elif key in (10,13) and selected: phase=2; cursor=0
                elif key in (ord("b"),ord("B")): phase=0; cursor=0
            elif phase==2:
                if key in (curses.KEY_UP,ord("k"),curses.KEY_DOWN,ord("j")):
                    index=[a for a,_ in SOLUTIONS].index(solution); solution=SOLUTIONS[(index+(1 if key in (curses.KEY_DOWN,ord("j")) else -1))%3][0]
                elif key in (10,13): phase=3
                elif key in (ord("b"),ord("B")): phase=1
            elif phase==3:
                if key in (ord("b"),ord("B")): phase=2
                elif key in (10,13): phase=4
            elif key in (ord("b"),ord("B")): phase=3
    curses.wrapper(app)

if __name__ == "__main__": raise SystemExit(main())
