#!/usr/bin/env python3
"""LEONES RC4 persistent TUI.

Strict UI contract:
- language is selected once and remains active for the whole session
- supported languages: Español, English, 中文
- SPACE selects; ENTER executes/confirms
- ENTER accepts both CR/LF and curses.KEY_ENTER
"""
from __future__ import annotations
import curses, json, os, shutil, subprocess, sys, threading
from dataclasses import dataclass, field
from pathlib import Path
from runtime_selection.operation_progress import OperationPhase, OperationProgress, terminal_progress

ROOT=Path(__file__).resolve().parents[1]
RECOMMENDER=ROOT/"scripts/rc4_fitllm_recommend.py"
INSTALLER=ROOT/"scripts/rc4_model_install.py"
INSTALL_SH=ROOT/"install.sh"
UNINSTALL_SH=ROOT/"scripts/uninstall.sh"
MODELS_DIR=ROOT/"models"
PURPOSES=("programming","reasoning","research","chat","multimodal","embedding","general")
SOFTWARE=("fitllm","ods","magnitude","hermes","omh")
NAV_KEYS=("home","state","intent","recommend","models","software","uninstall")
NAV_ES=("INICIO","ESTADO","INTENCIÓN","RECOMENDADOR","LLMs / INSTALACIÓN","SOFTWARE IA","DESINSTALACIÓN")
NAV_EN=("HOME","STATE","INTENT","RECOMMENDER","LLMs / INSTALLATION","AI SOFTWARE","UNINSTALL")
NAV_ZH=("首页","状态","意图","推荐器","LLM / 安装","AI 软件","卸载")
PURPOSE_LABEL={"programming":"PROGRAMMING","reasoning":"REASONING","research":"RESEARCH","chat":"CHAT","multimodal":"MULTIMODAL","embedding":"EMBEDDING","general":"GENERAL"}
SOFTWARE_LABEL={"fitllm":"FitLLM","ods":"ODS","magnitude":"Magnitude","hermes":"Hermes","omh":"OMH"}
TEXT={
"es":{"language":"Idioma: Español","nav":"NAVEGACIÓN","ops":"ACTIVIDAD RC4 / OPERACIÓN / PROGRESO","selection":"SELECCIÓN / INFORMACIÓN PRINCIPAL","action":"ACCIÓN / ESCALADO / PRIVILEGIOS","active":"ACTIVA","idle":"SIN OPERACIONES","phase":"FASE","data":"DATOS","rate":"VELOCIDAD","tab":"TAB cambiar foco","move":"↑/↓ mover","enter":"ENTER ejecutar","space":"SPACE seleccionar","back":"ESC volver","quit":"Q salir","intent":"INTENCIÓN DE USO","intent_help":"Selecciona uno o varios propósitos","details":"CARACTERÍSTICAS DE LA SELECCIÓN","accept":"ACEPTACIÓN","authorize":"AUTORIZACIÓN DEL SISTEMA","selected":"Seleccionado","selected_plural":"seleccionados","first":"Selecciona al menos un elemento con SPACE.","confirm":"¿Confirmar ejecución de los elementos seleccionados? [Y] sí / [N] no","confirm_uninstall":"¿Confirmar DESINSTALACIÓN de los elementos seleccionados? [Y] sí / [N] no","recommend":"RECOMENDACIÓN RC4","estimated":"ESTIMATED · ejecución no autorizada · medición no autorizada"},
"en":{"language":"Language: English","nav":"NAVIGATION","ops":"RC4 ACTIVITY / OPERATION / PROGRESS","selection":"SELECTION / MAIN INFORMATION","action":"ACTION / ESCALATION / PRIVILEGES","active":"ACTIVE","idle":"NO OPERATIONS","phase":"PHASE","data":"DATA","rate":"SPEED","tab":"TAB switch focus","move":"↑/↓ move","enter":"ENTER execute","space":"SPACE select","back":"ESC back","quit":"Q quit","intent":"USE INTENT","intent_help":"Select one or more purposes","details":"SELECTION CHARACTERISTICS","accept":"ACCEPTANCE","authorize":"SYSTEM AUTHORIZATION","selected":"Selected","selected_plural":"selected","first":"Select at least one item with SPACE.","confirm":"Confirm execution of selected items? [Y] yes / [N] no","confirm_uninstall":"Confirm UNINSTALL of selected items? [Y] yes / [N] no","recommend":"RC4 RECOMMENDATION","estimated":"ESTIMATED · execution not authorized · measurement not authorized"},
"zh":{"language":"语言：中文","nav":"导航","ops":"RC4 活动 / 操作 / 进度","selection":"选择 / 主要信息","action":"操作 / 权限 / 授权","active":"运行中","idle":"无操作","phase":"阶段","data":"数据","rate":"速度","tab":"TAB 切换焦点","move":"↑/↓ 移动","enter":"ENTER 执行","space":"SPACE 选择","back":"ESC 返回","quit":"Q 退出","intent":"使用意图","intent_help":"选择一个或多个用途","details":"选择特征","accept":"确认","authorize":"系统授权","selected":"已选择","selected_plural":"已选择","first":"请使用 SPACE 选择至少一个项目。","confirm":"确认执行所选项目？[Y] 是 / [N] 否","confirm_uninstall":"确认卸载所选项目？[Y] 是 / [N] 否","recommend":"RC4 推荐","estimated":"ESTIMATED · 未授权执行 · 未授权测量"}}

def tr(lang,k): return TEXT.get(lang,TEXT["es"]).get(k,k)
def nav_labels(lang): return {"es":NAV_ES,"en":NAV_EN,"zh":NAV_ZH}[lang]
def purpose_label(lang,k):
    if lang=="zh": return {"programming":"编程","reasoning":"推理","research":"研究","chat":"聊天","multimodal":"多模态","embedding":"嵌入","general":"通用"}[k]
    return PURPOSE_LABEL[k]
def put(s,y,x,text,width):
    if width<=0 or y<0 or y>=s.getmaxyx()[0]: return
    try:s.addnstr(y,max(0,x),str(text),max(0,width))
    except curses.error:pass
def box(s,y,x,h,w,title=""):
    if h<3 or w<4:return
    try:
        s.addstr(y,x,"+"+"-"*(w-2)+"+")
        for r in range(y+1,y+h-1): s.addstr(r,x,"|"); s.addstr(r,x+w-1,"|")
        s.addstr(y+h-1,x,"+"+"-"*(w-2)+"+")
        if title:s.addstr(y,x+2,f"[ {title} ]")
    except curses.error:pass
def human(v):
    n=float(v or 0)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB":return f"{n:.1f} {u}"
        n/=1024
def progress(p,w=30):
    if p is None:return "["+"."*w+"]"
    n=max(0,min(w,round(w*p/100)));return "["+"#"*n+"."*(w-n)+"]"
def local_models():
    if not MODELS_DIR.is_dir():return []
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and (p/".leones-installed.json").is_file())
def recommendation_models(sel):
    data=sel.get("recommendation",("",{}))[1]
    return [r.get("model_id",r.get("model","?")) for r in data.get("recommendations",[])[:3]]
def machine_state():
    cpu="unavailable"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu=line.split(":",1)[1].strip();break
    except OSError:pass
    gpu="unavailable"
    if shutil.which("nvidia-smi"):
        try:
            r=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],capture_output=True,text=True,timeout=5)
            if r.returncode==0 and r.stdout.strip():gpu=r.stdout.strip().replace("\n","; ")
        except Exception:pass
    try:
        mem={}
        for line in Path("/proc/meminfo").read_text().splitlines(): k,v=line.split(":",1);mem[k]=int(v.split()[0])*1024
        ram=f"{human(mem['MemTotal']-mem['MemAvailable'])} / {human(mem['MemTotal'])}"
    except Exception:ram="unavailable"
    d=shutil.disk_usage(ROOT)
    return cpu,os.cpu_count() or 1,gpu,ram,f"{human(d.used)} / {human(d.total)}"

class TaskManager:
    def __init__(self):
        self.lock=threading.Lock();self.active=False;self.kind="";self.item="";self.index=0;self.total_items=0;self.percent=None;self.downloaded=0;self.total_bytes=0;self.rate=0.;self.phase="idle";self.results=[];self.progress=None
    def snapshot(self):
        with self.lock:return dict(self.__dict__)
    def start(self,kind,n):
        with self.lock:self.active=True;self.kind=kind;self.index=0;self.total_items=n;self.item="";self.percent=None;self.downloaded=0;self.total_bytes=0;self.rate=0.;self.phase="preparing";self.results=[];self.progress=OperationProgress(kind,OperationPhase.PREPARING,current=0,total=max(1,n))
    def parse(self,line):
        with self.lock:
            f={x.split("=",1)[0]:x.split("=",1)[1] for x in line.split() if "=" in x}
            for k,a,c in (("PROGRESS","percent",float),("DOWNLOADED","downloaded",int),("TOTAL","total_bytes",int),("RATE","rate",float)):
                if k in f:
                    try:setattr(self,a,c(f[k].rstrip("%")))
                    except ValueError:pass
            if line.startswith(("PHASE=","STATUS=")):self.phase=line.split("=",1)[1].strip().lower()
    def run_cmd(self,cmd):
        try:p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        except OSError:return False
        if p.stdout:
            for line in p.stdout:self.parse(line.strip())
        return p.wait()==0
    def finish(self,out):
        with self.lock:self.results=out;ok=all(v for _,v in out);self.active=False;self.phase="completed" if ok else "failed";self.progress=terminal_progress(self.kind,ok)
    def launch(self,kind,items):
        if self.active or not items:return False
        items=list(items);self.start(kind,len(items))
        threading.Thread(target=self._worker,args=(kind,items),daemon=True).start();return True
    def _worker(self,kind,items):
        out=[]
        for i,item in enumerate(items,1):
            with self.lock:self.index=i;self.item=item;self.phase="downloading" if kind=="models" else ("removing" if kind=="uninstall" else "installing")
            if kind=="models":ok=self.run_cmd([sys.executable,str(INSTALLER),"--model-id",item,"--output-dir",str(MODELS_DIR)])
            elif kind=="software":ok=self.run_cmd(["bash",str(INSTALL_SH),f"--{item}"])
            else:ok=self.run_cmd(["bash",str(UNINSTALL_SH),"--yes",f"--{item}"])
            out.append((item,ok))
        self.finish(out)

@dataclass
class Action:
    state:str=""
    lines:list[str]=field(default_factory=list)
    def set(self,state,lines):self.state=state;self.lines=list(lines)

def run_recommendation(purposes):
    cmd=[sys.executable,str(RECOMMENDER),"--json"]
    for p in purposes:cmd += ["--purpose",p]
    try:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=120);data=json.loads(r.stdout);return data.get("status","error"),data
    except Exception as e:return "error",{"message":str(e)}

def language_screen(s):
    focus=0;langs=("es","en","zh");names=("Español","English","中文")
    while True:
        s.erase();h,w=s.getmaxyx();bw=min(64,max(44,w-4));x=max(1,(w-bw)//2);box(s,3,x,14,bw,"LEONES RC4");put(s,5,x+4,"SELECCIONA IDIOMA / SELECT LANGUAGE / 选择语言",bw-8)
        for i,name in enumerate(names):put(s,8+i,x+8,f"{'▶' if i==focus else ' '} [{i+1}] {name}",bw-16)
        put(s,13,x+4,"↑/↓ · ENTER · Q",bw-8);s.refresh();k=s.getch()
        if k in (curses.KEY_UP,ord("k")):focus=(focus-1)%3
        elif k in (curses.KEY_DOWN,ord("j")):focus=(focus+1)%3
        elif k in (10,13,getattr(curses,"KEY_ENTER",343)):return langs[focus]
        elif k in (ord("1"),ord("2"),ord("3")):return langs[int(chr(k))-1]
        elif k in (ord("q"),ord("Q"),27):raise SystemExit

def enter_key(k):return k in (10,13,getattr(curses,"KEY_ENTER",343))
def content_items(nav,sel):
    if nav==2:return list(PURPOSES)
    if nav==3:return recommendation_models(sel)
    if nav==4:return recommendation_models(sel)
    if nav==5:return list(SOFTWARE)
    if nav==6:return list(SOFTWARE)
    return []

def render(s,lang,nav,focus,idx,sel,task,action):
    s.erase();h,w=s.getmaxyx()
    if h<30 or w<100:put(s,1,2,"LEONES RC4 — terminal demasiado pequeña (mín. 100x30)",w-4);s.refresh();return
    box(s,1,1,h-3,w-2,"LEONES RC4");navw=27;box(s,3,3,h-7,navw,tr(lang,"nav"));labels=nav_labels(lang)
    for i,label in enumerate(labels):put(s,5+i*2,6,f"{'▶' if i==nav else ' '} [{i+1}] {label}",navw-6)
    x=32;rw=w-x-4;top=3;th=9;mid=13;mh=max(10,h-25);bot=mid+mh+1;bh=h-bot-4
    box(s,top,x,th,rw,tr(lang,"ops"));box(s,mid,x,mh,rw,tr(lang,"selection"));box(s,bot,x,bh,rw,tr(lang,"action"))
    q=task.snapshot();put(s,5,x+2,f"● {tr(lang,'active') if q['active'] else tr(lang,'idle')}",rw-4);put(s,6,x+2,f"{q['kind']} {q['item']}",rw-4);put(s,7,x+2,f"{tr(lang,'phase')}: {q['phase']}  {q['percent'] if q['percent'] is not None else '—'}%",rw-4);put(s,8,x+2,progress(q['percent']),rw-4);put(s,9,x+2,f"{tr(lang,'data')}: {human(q['downloaded'])}/{human(q['total_bytes'])}  {tr(lang,'rate')}: {human(q['rate'])}/s",rw-4)
    put(s,mid+1,x+2,tr(lang,"language"),rw-4)
    if nav==1:
        cpu,cores,gpu,ram,disk=machine_state();put(s,mid+3,x+2,"ESTADO DE LA MÁQUINA",rw-4);put(s,mid+5,x+3,f"CPU: {cpu}",rw-7);put(s,mid+6,x+3,f"CPU lógicas: {cores}",rw-7);put(s,mid+7,x+3,f"GPU: {gpu}",rw-7);put(s,mid+8,x+3,f"RAM ocupada/total: {ram}",rw-7);put(s,mid+9,x+3,f"DISCO ocupado/total: {disk}",rw-7);models=local_models();put(s,mid+11,x+3,f"LLMs locales: {len(models)}",rw-7);put(s,mid+12,x+3,f"  {', '.join(models) if models else '(ninguno)'}",rw-7)
    elif nav==2:
        put(s,mid+3,x+2,tr(lang,"intent"),rw-4);put(s,mid+4,x+2,tr(lang,"intent_help"),rw-4)
        for i,p in enumerate(PURPOSES):put(s,mid+6+i,x+3,f"{'▶' if focus==1 and idx==i else ' '} {'[x]' if p in sel['intent'] else '[ ]'} {i+1}. {purpose_label(lang,p)}",rw-7)
    elif nav==3:
        put(s,mid+3,x+2,tr(lang,"recommend"),rw-4);put(s,mid+5,x+3,f"STATUS: {sel['recommendation'][0]}",rw-7)
        for i,m in enumerate(recommendation_models(sel)):put(s,mid+7+i,x+3,f"{'▶' if focus==1 and idx==i else ' '} {i+1}. {m}",rw-7)
    elif nav==4:
        put(s,mid+3,x+2,"LLMs / INSTALACIÓN",rw-4);put(s,mid+4,x+2,"SPACE = selección múltiple; ENTER = ejecutar",rw-4)
        for i,m in enumerate(recommendation_models(sel)):put(s,mid+6+i,x+3,f"{'▶' if focus==1 and idx==i else ' '} {'[x]' if m in sel['models'] else '[ ]'} {m}",rw-7)
        if not recommendation_models(sel):put(s,mid+6,x+3,"Primero ejecuta RECOMENDADOR.",rw-7)
    elif nav in (5,6):
        put(s,mid+3,x+2,"SOFTWARE IA" if nav==5 else "DESINSTALACIÓN",rw-4)
        for i,k in enumerate(SOFTWARE):put(s,mid+5+i,x+3,f"{'▶' if focus==1 and idx==i else ' '} {'[x]' if k in sel['software' if nav==5 else 'uninstall'] else '[ ]'} {SOFTWARE_LABEL[k]}",rw-7)
    else:put(s,mid+3,x+2,"LEONES RC4",rw-4)
    put(s,bot+1,x+2,action.state or tr(lang,"details"),rw-4)
    for i,line in enumerate(action.lines[:max(1,bh-4)]):put(s,bot+2+i,x+3,line,rw-7)
    put(s,h-2,2,f"{tr(lang,'tab')} · {tr(lang,'move')} · {tr(lang,'enter')} · {tr(lang,'space')} · {tr(lang,'back')} · {tr(lang,'quit')}",w-4)
    try:curses.curs_set(1)
    except curses.error:pass
    s.refresh()

def ask_confirm(s,lang,text):
    action_text=text
    while True:
        put(s,s.getmaxyx()[0]-4,34,action_text,s.getmaxyx()[1]-36);s.refresh();k=s.getch()
        if k in (ord("y"),ord("Y")):return True
        if k in (ord("n"),ord("N"),27):return False

def app(s):
    curses.curs_set(1);s.keypad(True);lang=language_screen(s);nav=0;focus=0;idx=0;task=TaskManager();action=Action();sel={"intent":set(),"recommendation":("",{}),"models":set(),"software":set(),"uninstall":set()}
    while True:
        render(s,lang,nav,focus,idx,sel,task,action);s.timeout(150);k=s.getch()
        if k in (ord("q"),ord("Q")):break
        if k==9:focus=1-focus;idx=0;continue
        if k in (curses.KEY_UP,ord("k")):
            if focus==0:nav=(nav-1)%len(NAV_KEYS);idx=0
            else:
                items=content_items(nav,sel)
                if items:idx=(idx-1)%len(items)
            continue
        if k in (curses.KEY_DOWN,ord("j")):
            if focus==0:nav=(nav+1)%len(NAV_KEYS);idx=0
            else:
                items=content_items(nav,sel)
                if items:idx=(idx+1)%len(items)
            continue
        if k==ord(" ") and focus==1:
            items=content_items(nav,sel)
            if not items:continue
            item=items[idx]
            if nav==2:
                (sel['intent'].remove(item) if item in sel['intent'] else sel['intent'].add(item));action.set(tr(lang,'intent'),[f"{len(sel['intent'])} {tr(lang,'selected_plural')}"])
            elif nav==4:
                (sel['models'].remove(item) if item in sel['models'] else sel['models'].add(item));action.set(tr(lang,'details'),[f"{len(sel['models'])} {tr(lang,'selected_plural')}",item])
            elif nav==5:
                (sel['software'].remove(item) if item in sel['software'] else sel['software'].add(item));action.set(tr(lang,'details'),[f"{len(sel['software'])} {tr(lang,'selected_plural')}",SOFTWARE_LABEL[item]])
            elif nav==6:
                (sel['uninstall'].remove(item) if item in sel['uninstall'] else sel['uninstall'].add(item));action.set(tr(lang,'details'),[f"{len(sel['uninstall'])} {tr(lang,'selected_plural')}",SOFTWARE_LABEL[item]])
            continue
        if enter_key(k):
            items=content_items(nav,sel)
            if nav==2 and focus==0 or (nav==2 and focus==1 and not sel['intent']):
                if not sel['intent']:action.set(tr(lang,'intent'),[tr(lang,'first')]);continue
                status,data=run_recommendation(sorted(sel['intent']));sel['recommendation']=(status,data);nav=3;focus=0;idx=0;action.set(tr(lang,'recommend'),[f"STATUS: {status}"]);continue
            if nav==3 and focus==1 and items:
                action.set(tr(lang,'details'),[f"{tr(lang,'selected')}: {items[idx]}",tr(lang,'estimated')]);continue
            if nav==4:
                if not sel['models']:action.set(tr(lang,'details'),[tr(lang,'first')]);continue
                if ask_confirm(s,lang,tr(lang,'confirm')):task.launch('models',sorted(sel['models']));action.set(tr(lang,'accept'),[f"{len(sel['models'])} {tr(lang,'selected_plural')}"])
                continue
            if nav==5:
                if not sel['software']:action.set(tr(lang,'details'),[tr(lang,'first')]);continue
                if ask_confirm(s,lang,tr(lang,'confirm')):task.launch('software',sorted(sel['software']));action.set(tr(lang,'accept'),[f"{len(sel['software'])} {tr(lang,'selected_plural')}"])
                continue
            if nav==6:
                if not sel['uninstall']:action.set(tr(lang,'details'),[tr(lang,'first')]);continue
                if ask_confirm(s,lang,tr(lang,'confirm_uninstall')):task.launch('uninstall',sorted(sel['uninstall']));action.set(tr(lang,'accept'),[f"{len(sel['uninstall'])} {tr(lang,'selected_plural')}"])
                continue
            if nav==0:nav=2;idx=0
            continue
        if k==27:
            if focus==1:focus=0;idx=0
            else:nav=0;idx=0

def main():return curses.wrapper(app) or 0
if __name__=="__main__":raise SystemExit(main())
