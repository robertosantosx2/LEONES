#!/usr/bin/env python3
"""LEONES RC4 persistent three-panel TUI.

Normative contract: docs/TUI_RULES_RC4.md
Only the language screen is shown without the persistent navigation frame.
"""
from __future__ import annotations
import curses, json, os, shutil, subprocess, sys, threading
from dataclasses import dataclass, field
from pathlib import Path
from runtime_selection.operation_progress import OperationPhase, OperationProgress, terminal_progress

ROOT=Path(__file__).resolve().parents[1]
RECOMMENDER=ROOT/"scripts/rc4_fitllm_recommend.py"; INSTALLER=ROOT/"scripts/rc4_model_install.py"; INSTALL_SH=ROOT/"install.sh"; UNINSTALL_SH=ROOT/"scripts/uninstall.sh"; MODELS_DIR=ROOT/"models"
PURPOSES=(("programming","PROGRAMMING"),("reasoning","REASONING"),("research","RESEARCH"),("chat","CHAT"),("multimodal","MULTIMODAL"),("embedding","EMBEDDING"),("general","GENERAL"))
SOFTWARE=(("fitllm","FitLLM"),("ods","ODS"),("magnitude","Magnitude"),("hermes","Hermes"),("omh","OMH"))
NAV=(("home","INICIO"),("state","ESTADO"),("intent","INTENCIÓN"),("recommend","RECOMENDADOR"),("models","LLMs / INSTALACIÓN"),("software","SOFTWARE IA"),("uninstall","DESINSTALACIÓN"))
TEXT={"es":{"nav":"NAVEGACIÓN","ops":"ACTIVIDAD RC4 / OPERACIÓN / PROGRESO","selection":"SELECCIÓN / INFORMACIÓN PRINCIPAL","action":"ACCIÓN / ESCALADO / PRIVILEGIOS","active":"ACTIVA","idle":"SIN OPERACIONES","phase":"FASE","data":"DATOS","rate":"VELOCIDAD","tab":"TAB cambiar foco","move":"↑/↓ mover","open":"ENTER abrir","back":"ESC volver","quit":"Q salir","select":"SPACE seleccionar","details":"CARACTERÍSTICAS DE LA SELECCIÓN","accept":"ACEPTACIÓN","authorize":"AUTORIZACIÓN DEL SISTEMA","password":"Contraseña de sudo:","hidden":"Entrada oculta · ENTER confirma","failed_auth":"No se pudo autorizar sudo. Operación cancelada.","intent":"INTENCIÓN DE USO","intent_help":"Selecciona uno o varios propósitos","recommendation":"RECOMENDACIÓN RC4","estimated":"ESTIMATED · ejecución no autorizada · medición no autorizada","measured":"MEASURED · evidencia de ejecución/medición real","home":"Centro de control: puedes navegar mientras las operaciones continúan.","confirm_install":"¿Confirmar instalación de todos los seleccionados? [Y] sí / [N] no","confirm_uninstall":"¿Confirmar DESINSTALACIÓN de todos los seleccionados? [Y] sí / [N] no"},"en":{"nav":"NAVIGATION","ops":"RC4 ACTIVITY / OPERATION / PROGRESS","selection":"SELECTION / MAIN INFORMATION","action":"ACTION / ESCALATION / PRIVILEGES","active":"ACTIVE","idle":"NO OPERATIONS","phase":"PHASE","data":"DATA","rate":"SPEED","tab":"TAB switch focus","move":"↑/↓ move","open":"ENTER open","back":"ESC back","quit":"Q quit","select":"SPACE select","details":"SELECTION CHARACTERISTICS","accept":"ACCEPTANCE","authorize":"SYSTEM AUTHORIZATION","password":"sudo password:","hidden":"Hidden input · ENTER confirms","failed_auth":"sudo authorization failed. Operation cancelled.","intent":"USE INTENT","intent_help":"Select one or more purposes","recommendation":"RC4 RECOMMENDATION","estimated":"ESTIMATED · execution not authorized · measurement not authorized","measured":"MEASURED · real execution/measurement evidence","home":"Control center: you can navigate while operations continue.","confirm_install":"Confirm installation of all selected? [Y] yes / [N] no","confirm_uninstall":"Confirm UNINSTALL of all selected? [Y] yes / [N] no"}}

def t(lang,key): return TEXT.get(lang,TEXT["es"]).get(key,key)
def put(scr,y,x,text,width):
    if width<=0 or y<0 or y>=scr.getmaxyx()[0]: return
    try:scr.addnstr(y,max(0,x),str(text),width)
    except curses.error:pass
def box(scr,y,x,h,w,title=""):
    if h<3 or w<4:return
    try:
        scr.addstr(y,x,"+"+"-"*(w-2)+"+")
        for r in range(y+1,y+h-1):scr.addstr(r,x,"|");scr.addstr(r,x+w-1,"|")
        scr.addstr(y+h-1,x,"+"+"-"*(w-2)+"+")
        if title:scr.addstr(y,x+2,f"[ {title} ]")
    except curses.error:pass
def human_bytes(v):
    n=float(v or 0)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB":return f"{n:.1f} {u}"
        n/=1024
def progress_bar(p,w=28):
    if p is None:return "["+"."*w+"]"
    n=max(0,min(w,round(w*p/100)));return "["+"#"*n+"."*(w-n)+"]"
def local_models():
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and (p/".leones-installed.json").is_file()) if MODELS_DIR.is_dir() else []
def machine_state():
    cpu="estado no disponible"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):cpu=line.split(":",1)[1].strip();break
    except OSError:pass
    gpu="estado no disponible"
    if shutil.which("nvidia-smi"):
        try:
            r=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],capture_output=True,text=True,timeout=5)
            if r.returncode==0 and r.stdout.strip():gpu=r.stdout.strip().replace("\n","; ")
        except Exception:pass
    try:
        mem={}
        for line in Path("/proc/meminfo").read_text().splitlines():k,v=line.split(":",1);mem[k]=int(v.split()[0])*1024
        ram=f"{human_bytes(mem['MemTotal']-mem['MemAvailable'])} / {human_bytes(mem['MemTotal'])}"
    except Exception:ram="estado no disponible"
    du=shutil.disk_usage(ROOT)
    return cpu,os.cpu_count() or 1,gpu,ram,f"{human_bytes(du.used)} / {human_bytes(du.total)}"

class TaskManager:
    def __init__(self):
        self.lock=threading.Lock();self.active=False;self.kind="";self.item="";self.index=0;self.total_items=0;self.percent=None;self.downloaded=0;self.total_bytes=0;self.rate=0.;self.phase="idle";self.results=[];self.progress=None
    def snapshot(self):
        with self.lock:return dict(self.__dict__)
    def start(self,kind,n):
        with self.lock:self.active=True;self.kind=kind;self.item="";self.index=0;self.total_items=n;self.percent=None;self.downloaded=0;self.total_bytes=0;self.rate=0.;self.phase="preparing";self.progress=OperationProgress(kind,OperationPhase.PREPARING,current=0,total=max(1,n))
    def _line(self,line):
        with self.lock:
            f={x.split("=",1)[0]:x.split("=",1)[1] for x in line.split() if "=" in x}
            for key,attr,cast in (("PROGRESS","percent",float),("DOWNLOADED","downloaded",int),("TOTAL","total_bytes",int),("RATE","rate",float)):
                if key in f:
                    try:setattr(self,attr,cast(f[key].rstrip("%")))
                    except ValueError:pass
            if line.startswith(("PHASE=","STATUS=")):self.phase=line.split("=",1)[1].strip().lower()
    def _run(self,cmd):
        try:p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        except OSError:return False
        if p.stdout:
            for line in p.stdout:self._line(line.strip())
        return p.wait()==0
    def finish(self,results):
        with self.lock:self.results=list(results);ok=all(x[1] for x in results);self.active=False;self.phase="completed" if ok else "failed";self.progress=terminal_progress(self.kind,ok)
    def start_models(self,rows):
        if self.active or not rows:return False
        rows=list(rows);self.start("models",len(rows));threading.Thread(target=self._models,args=(rows,),daemon=True).start();return True
    def _models(self,rows):
        out=[];MODELS_DIR.mkdir(exist_ok=True)
        for i,row in enumerate(rows,1):
            model=row.get("model_id","?")
            with self.lock:self.index=i;self.item=model;self.phase="downloading"
            out.append((model,self._run([sys.executable,str(INSTALLER),"--model-id",model,"--output-dir",str(MODELS_DIR)])))
        self.finish(out)
    def start_software(self,items):
        if self.active or not items:return False
        items=list(items);self.start("software",len(items));threading.Thread(target=self._software,args=(items,),daemon=True).start();return True
    def _software(self,items):
        out=[]
        for i,c in enumerate(items,1):
            name=dict(SOFTWARE).get(c,c)
            with self.lock:self.index=i;self.item=name;self.phase="installing"
            out.append((name,self._run(["bash",str(INSTALL_SH),f"--{c}"])))
        self.finish(out)
    def start_uninstall(self,items):
        if self.active or not items:return False
        items=list(items);self.start("uninstall",len(items));threading.Thread(target=self._uninstall,args=(items,),daemon=True).start();return True
    def _uninstall(self,items):
        out=[]
        for i,c in enumerate(items,1):
            name=dict(SOFTWARE).get(c,c)
            with self.lock:self.index=i;self.item=name;self.phase="removing"
            out.append((name,self._run(["bash",str(UNINSTALL_SH),"--yes",f"--{c}"])))
        self.finish(out)

def run_operation(task,kind,items):
    if kind=="models":return task.start_models(items)
    if kind=="software":return task.start_software(items)
    if kind=="uninstall":return task.start_uninstall(items)
    return False

def run_recommendation(purposes):
    cmd=[sys.executable,str(RECOMMENDER),"--json"]
    for purpose in purposes:cmd.extend(("--purpose",purpose))
    try:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=120);data=json.loads(r.stdout);return data.get("status","error"),data
    except Exception as exc:return "error",{"message":str(exc)}

@dataclass
class ActionState:
    state:str="";lines:list[str]=field(default_factory=list);footer:str=""
    def update(self,*,state=None,lines=None,footer=None):
        if state is not None:self.state=state
        if lines is not None:self.lines=list(lines)
        if footer is not None:self.footer=footer

_CTX=None
def set_context(scr,lang,action):
    global _CTX;_CTX=(scr,lang,action)
def clear_context():
    global _CTX;_CTX=None
def confirm(scr,lang,question):
    if _CTX:_CTX[2].update(state=t(lang,"accept"),lines=[question],footer="[Y] sí   [N/ESC] no" if lang=="es" else "[Y] yes   [N/ESC] no")
    scr.timeout(-1)
    while True:
        key=scr.getch()
        if key in (ord("y"),ord("Y")):return True
        if key in (ord("n"),ord("N"),27):return False
def privilege_prompt(scr,lang):
    if os.geteuid()==0 or not shutil.which("sudo"):return True
    if subprocess.run(["sudo","-n","-v"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return True
    if _CTX:_CTX[2].update(state=t(lang,"authorize"),lines=["La operación requiere privilegios de administrador." if lang=="es" else "The operation requires administrator privileges.","[Y] Autorizar   [N/ESC] Cancelar"])
    scr.timeout(-1)
    while True:
        key=scr.getch()
        if key in (ord("n"),ord("N"),27):return False
        if key in (ord("y"),ord("Y")):break
    if _CTX:_CTX[2].update(state=t(lang,"authorize"),lines=[t(lang,"password"),t(lang,"hidden")])
    password="";curses.echo(False)
    try:
        while True:
            key=scr.getch()
            if key in (10,13):break
            if key==27:return False
            if key in (8,127,curses.KEY_BACKSPACE):password=password[:-1]
            elif 32<=key<=126:password+=chr(key)
    finally:curses.echo(True)
    try:r=subprocess.run(["sudo","-S","-v"],input=password+"\n",text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    finally:password=""
    if r.returncode==0:return True
    if _CTX:_CTX[2].update(state=t(lang,"details"),lines=[t(lang,"failed_auth")])
    return False

def language_screen(scr):
    focus=0
    while True:
        scr.erase();h,w=scr.getmaxyx();bw=min(64,max(42,w-4));x=max(1,(w-bw)//2);box(scr,3,x,12,bw,"LEONES RC4");put(scr,5,x+4,"SELECCIONA IDIOMA / SELECT LANGUAGE",bw-8)
        for i,name in enumerate(("Español","English")):put(scr,8+i,x+8,f"{'>' if i==focus else ' '} [{i+1}] {name}",bw-16)
        put(scr,12,x+4,"↑/↓ · ENTER · Q",bw-8);scr.refresh();key=scr.getch()
        if key in (curses.KEY_UP,ord("k")):focus=(focus-1)%2
        elif key in (curses.KEY_DOWN,ord("j")):focus=(focus+1)%2
        elif key in (10,13):return ("es","en")[focus]
        elif key in (ord("1"),ord("2")):return ("es","en")[int(chr(key))-1]
        elif key in (ord("q"),ord("Q"),27):raise SystemExit

def content_items(nav,selection):
    if nav==2:return list(PURPOSES)
    if nav==4:return [(m,m) for m in local_models()]
    if nav in (5,6):return list(SOFTWARE)
    if nav==3:return [(r.get("model_id",r.get("model","?")),r.get("model_id",r.get("model","?"))) for r in selection.get("recommendation",("",{}))[1].get("recommendations",[])[:3]]
    return []

def draw_frame(scr,lang,nav,task,content_focus=False):
    scr.erase();h,w=scr.getmaxyx()
    if h<28 or w<100:put(scr,1,2,"LEONES RC4 — terminal demasiado pequeña (mín. 100x28)",w-4);scr.refresh();return None
    box(scr,1,1,h-3,w-2,"LEONES RC4");navw=25;box(scr,3,3,h-7,navw,t(lang,"nav"))
    for i,(_,label) in enumerate(NAV):put(scr,5+i*2,6,f"{'▶' if i==nav else ' '} [{i+1}] {label}",navw-6)
    x=30;rw=w-x-4;top=3;th=8;mid=12;mh=max(8,h-23);bot=mid+mh+1;bh=h-bot-4
    box(scr,top,x,th,rw,t(lang,"ops"));box(scr,mid,x,mh,rw,t(lang,"selection"));box(scr,bot,x,bh,rw,t(lang,"action"))
    s=task.snapshot();put(scr,5,x+2,f"● {t(lang,'active') if s['active'] else t(lang,'idle')}",rw-4);put(scr,6,x+2,f"{s['kind']} {s['item']}",rw-4);put(scr,7,x+2,f"{t(lang,'phase')}: {s['phase']}  {s['percent'] if s['percent'] is not None else '—'}%",rw-4);put(scr,8,x+2,progress_bar(s['percent']),rw-4);put(scr,9,x+2,f"{t(lang,'data')}: {human_bytes(s['downloaded'])} / {human_bytes(s['total_bytes'])}   {t(lang,'rate')}: {human_bytes(s['rate'])}/s",rw-4)
    if content_focus:put(scr,mid+1,x+2,"[ CONTENIDO ]",rw-4)
    return x,rw,mid,mh,bot,bh

def render_selection(scr,lang,nav,task,selection,action,focus,content_index):
    frame=draw_frame(scr,lang,nav,task,focus==1)
    if not frame:return
    x,rw,mid,mh,bot,bh=frame
    if nav==2:
        put(scr,mid+2,x+2,t(lang,"intent"),rw-4);put(scr,mid+3,x+2,t(lang,"intent_help"),rw-4)
        for i,(key,label) in enumerate(PURPOSES):
            mark="[x]" if key in selection["intent"] else "[ ]";cursor="▶" if focus==1 and i==content_index else " ";put(scr,mid+5+i,x+3,f"{cursor}{mark} {i+1}. {label}",rw-7)
        put(scr,bot+1,x+2,"USER INTENT[]",rw-4);put(scr,bot+2,x+2,"if not selected: Selecciona al menos un propósito.",rw-4)
    elif nav==3:
        put(scr,mid+2,x+2,t(lang,"recommendation"),rw-4);status,data=selection.get("recommendation",("",{}));put(scr,mid+4,x+2,f"STATUS: {status}",rw-4);put(scr,mid+5,x+2,t(lang,"estimated"),rw-4)
        for i,row in enumerate(data.get("recommendations",[])[:3]):put(scr,mid+7+i,x+3,f"{'▶' if focus==1 and i==content_index else ' '}{i+1}. {row.get('model_id',row.get('model','?'))}",rw-7)
    elif nav==4:
        put(scr,mid+2,x+2,"LLMs locales",rw-4);models=local_models()
        for i,m in enumerate(models[:max(1,mh-5)]):put(scr,mid+4+i,x+3,f"{'▶' if focus==1 and i==content_index else ' '}[ ] {m}",rw-7)
        if not models:put(scr,mid+4,x+3,"(ningún modelo instalado)",rw-7)
    elif nav in (5,6):
        put(scr,mid+2,x+2,"SOFTWARE IA" if nav==5 else "DESINSTALACIÓN",rw-4);base=6 if nav==6 else 4
        if nav==6:put(scr,mid+4,x+3,"Selecciona software IA para eliminar.",rw-7)
        for i,(key,label) in enumerate(SOFTWARE):put(scr,mid+base+i,x+3,f"{'▶' if focus==1 and i==content_index else ' '}[ ] {label} ({key})",rw-7)
    elif nav==1:
        cpu,cores,gpu,ram,disk=machine_state();put(scr,mid+2,x+2,"ESTADO DE LA MÁQUINA",rw-4);put(scr,mid+4,x+3,f"CPU: {cpu}",rw-7);put(scr,mid+5,x+3,f"CPU lógicas: {cores}",rw-7);put(scr,mid+6,x+3,f"GPU: {gpu}",rw-7);put(scr,mid+7,x+3,f"RAM ocupada/total: {ram}",rw-7);put(scr,mid+8,x+3,f"DISCO ocupado/total: {disk}",rw-7);put(scr,mid+10,x+3,f"LLMs locales: {len(local_models())}",rw-7)
    else:put(scr,mid+2,x+2,t(lang,"home"),rw-4)
    put(scr,bot+1,x+2,action.state or t(lang,"details"),rw-4)
    for i,line in enumerate(action.lines[:max(1,bh-4)]):put(scr,bot+2+i,x+3,line,rw-7)
    put(scr,scr.getmaxyx()[0]-2,2,f"{t(lang,'tab')} · {t(lang,'move')} · {t(lang,'open')} · {t(lang,'back')} · {t(lang,'quit')} · {t(lang,'select')}",scr.getmaxyx()[1]-4)
    try:curses.curs_set(1)
    except curses.error:pass
    scr.refresh()

def run_app(scr):
    curses.curs_set(1);scr.keypad(True);lang=language_screen(scr);nav=0;focus=0;content_index=0;task=TaskManager();action=ActionState();set_context(scr,lang,action);selection={"intent":set(),"recommendation":("",{})}
    while True:
        render_selection(scr,lang,nav,task,selection,action,focus,content_index);scr.timeout(150);key=scr.getch()
        if key in (ord("q"),ord("Q")):break
        if key==9:
            focus=1-focus;content_index=0
        elif key in (curses.KEY_UP,ord("k")):
            if focus==0:nav=(nav-1)%len(NAV);content_index=0
            else:
                items=content_items(nav,selection)
                if items:content_index=(content_index-1)%len(items)
        elif key in (curses.KEY_DOWN,ord("j")):
            if focus==0:nav=(nav+1)%len(NAV);content_index=0
            else:
                items=content_items(nav,selection)
                if items:content_index=(content_index+1)%len(items)
        elif key in (10,13):
            if focus==0:
                if nav==2:
                    if not selection["intent"]:action.update(state=t(lang,"intent"),lines=["USER INTENT[]: Selecciona al menos un propósito."]);continue
                    status,data=run_recommendation(sorted(selection["intent"]));selection["recommendation"]=(status,data);nav=3;content_index=0
                elif nav in (5,6):
                    items=[k for k,_ in SOFTWARE]
                    if items and confirm(scr,lang,t(lang,"confirm_install" if nav==5 else "confirm_uninstall")) and privilege_prompt(scr,lang):run_operation(task,"software" if nav==5 else "uninstall",items)
            else:
                items=content_items(nav,selection)
                if nav==2 and items:
                    key_name=items[content_index][0];selection["intent"].add(key_name)
                elif nav==3 and items:action.update(state=t(lang,"details"),lines=[f"Seleccionado: {items[content_index][0]}",t(lang,"estimated")])
        elif key==ord(" ") and focus==1:
            items=content_items(nav,selection)
            if nav==2 and items:
                key_name=items[content_index][0]
                if key_name in selection["intent"]:selection["intent"].remove(key_name)
                else:selection["intent"].add(key_name)
            elif nav in (4,5,6) and items:action.update(state=t(lang,"details"),lines=[f"Seleccionado: {items[content_index][1]}"])
        elif key==27:
            if focus==1:focus=0;content_index=0
            else:nav=0
    clear_context()

def main():return curses.wrapper(run_app) or 0
if __name__=="__main__":raise SystemExit(main())
