#!/usr/bin/env python3
"""LEONES RC4 persistent three-panel TUI.

Normative contract: docs/TUI_RULES_RC4.md
Only the language screen is shown without the persistent navigation frame.
"""
from __future__ import annotations
import curses, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path
from runtime_selection.operation_progress import OperationProgress, OperationPhase, terminal_progress

ROOT=Path(__file__).resolve().parents[1]
RECOMMENDER=ROOT/"scripts/rc4_fitllm_recommend.py"
INSTALLER=ROOT/"scripts/rc4_model_install.py"
INVENTORY=ROOT/"scripts/rc4_component_inventory.py"
INSTALL_SH=ROOT/"install.sh"
UNINSTALL_SH=ROOT/"scripts/uninstall.sh"
MODELS_DIR=ROOT/"models"
PURPOSES=(("programming","PROGRAMMING"),("reasoning","REASONING"),("research","RESEARCH"),("chat","CHAT"),("multimodal","MULTIMODAL"),("embedding","EMBEDDING"),("general","GENERAL"))
SOFTWARE=(("fitllm","FitLLM"),("ods","ODS"),("magnitude","Magnitude"),("hermes","Hermes"),("omh","OMH"))
NAV=(("home","INICIO"),("state","ESTADO"),("intent","INTENCIÓN"),("recommend","RECOMENDADOR"),("models","LLMs / INSTALACIÓN"),("software","SOFTWARE IA"),("uninstall","DESINSTALACIÓN"))
TEXT={
"es":{"nav":"NAVEGACIÓN","ops":"ACTIVIDAD RC4 / OPERACIÓN / PROGRESO","selection":"SELECCIÓN / INFORMACIÓN PRINCIPAL","action":"ACCIÓN / ESCALADO / PRIVILEGIOS","active":"ACTIVA","idle":"SIN OPERACIONES","phase":"FASE","data":"DATOS","rate":"VELOCIDAD","tab":"TAB cambiar foco","move":"↑/↓ mover","open":"ENTER abrir","back":"ESC volver","quit":"Q salir","select":"SPACE select","details":"CARACTERÍSTICAS DE LA SELECCIÓN","accept":"ACEPTACIÓN","authorize":"AUTORIZACIÓN DEL SISTEMA","password":"Contraseña de sudo:","hidden":"Entrada oculta · ENTER confirma","cancelled":"Operación cancelada.","authorized":"Privilegios autorizados. Operación iniciada en segundo plano.","failed_auth":"No se pudo autorizar sudo. Operación cancelada.","requirements":"REQUISITOS","destination":"DESTINO","dependencies":"DEPENDENCIAS","consequences":"CONSECUENCIAS","state":"ESTADO","intent":"INTENCIÓN DE USO","intent_help":"Selecciona uno o varios propósitos","recommendation":"RECOMENDACIÓN RC4","estimated":"ESTIMATED · ejecución no autorizada · medición no autorizada","measured":"MEASURED · evidencia de ejecución/medición real","home":"Centro de control: puedes navegar mientras las operaciones continúan.","confirm_install":"¿Confirmar instalación de todos los seleccionados? [Y] sí / [N] no","confirm_uninstall":"¿Confirmar DESINSTALACIÓN de todos los seleccionados? [Y] sí / [N] no"},
"en":{"nav":"NAVIGATION","ops":"RC4 ACTIVITY / OPERATION / PROGRESS","selection":"SELECTION / MAIN INFORMATION","action":"ACTION / ESCALATION / PRIVILEGES","active":"ACTIVE","idle":"NO OPERATIONS","phase":"PHASE","data":"DATA","rate":"SPEED","tab":"TAB switch focus","move":"↑/↓ move","open":"ENTER open","back":"ESC back","quit":"Q quit","select":"SPACE select","details":"SELECTION CHARACTERISTICS","accept":"ACCEPTANCE","authorize":"SYSTEM AUTHORIZATION","password":"sudo password:","hidden":"Hidden input · ENTER confirms","cancelled":"Operation cancelled.","authorized":"Privileges authorized. Operation started in background.","failed_auth":"sudo authorization failed. Operation cancelled.","requirements":"REQUIREMENTS","destination":"DESTINATION","dependencies":"DEPENDENCIES","consequences":"CONSEQUENCES","state":"STATE","intent":"USE INTENT","intent_help":"Select one or more purposes","recommendation":"RC4 RECOMMENDATION","estimated":"ESTIMATED · execution not authorized · measurement not authorized","measured":"MEASURED · real execution/measurement evidence","home":"Control center: you can navigate while operations continue.","confirm_install":"Confirm installation of all selected? [Y] yes / [N] no","confirm_uninstall":"Confirm UNINSTALL of all selected? [Y] yes / [N] no"}}

def t(lang,k): return TEXT.get(lang,TEXT["es"]).get(k,k)
def put(s,y,x,text,width):
    if width<=0 or y<0 or y>=s.getmaxyx()[0]: return
    try: s.addnstr(y,max(0,x),str(text),width)
    except curses.error: pass
def box(s,y,x,h,w,title=""):
    if h<3 or w<4: return
    try:
        s.addstr(y,x,"+"+"-"*(w-2)+"+")
        for r in range(y+1,y+h-1): s.addstr(r,x,"|"); s.addstr(r,x+w-1,"|")
        s.addstr(y+h-1,x,"+"+"-"*(w-2)+"+")
        if title: s.addstr(y,x+2,f"[ {title} ]")
    except curses.error: pass
def human_bytes(v):
    n=float(v or 0)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB": return f"{n:.1f} {u}"
        n/=1024
def progress_bar(p,w=28):
    if p is None: return "["+"."*w+"]"
    n=max(0,min(w,round(w*p/100))); return "["+"#"*n+"."*(w-n)+"]"
def inventory():
    try:
        r=subprocess.run([sys.executable,str(INVENTORY),"--json"],cwd=ROOT,capture_output=True,text=True,timeout=20)
        return json.loads(r.stdout)
    except Exception: return {"components":[]}
def local_models():
    return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and (p/".leones-installed.json").is_file()) if MODELS_DIR.is_dir() else []
def machine_state():
    cpu="estado no disponible"; gpu="estado no disponible"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"): cpu=line.split(":",1)[1].strip(); break
    except OSError: pass
    if shutil.which("nvidia-smi"):
        try:
            r=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],capture_output=True,text=True,timeout=5)
            if r.returncode==0 and r.stdout.strip(): gpu=r.stdout.strip().replace("\n","; ")
        except Exception: pass
    try:
        mem={}
        for line in Path("/proc/meminfo").read_text().splitlines(): k,v=line.split(":",1); mem[k]=int(v.split()[0])*1024
        ram=f"{human_bytes(mem['MemTotal']-mem['MemAvailable'])} / {human_bytes(mem['MemTotal'])}"
    except Exception: ram="estado no disponible"
    du=shutil.disk_usage(ROOT)
    return cpu,os.cpu_count() or 1,gpu,ram,f"{human_bytes(du.used)} / {human_bytes(du.total)}"

class TaskManager:
    def __init__(self):
        self.lock=threading.Lock(); self.active=False; self.kind=""; self.item=""; self.index=0; self.total_items=0; self.percent=None; self.downloaded=0; self.total_bytes=0; self.rate=0.; self.phase="idle"; self.results=[]; self.progress=None
    def snapshot(self):
        with self.lock: return dict(self.__dict__)
    def start(self,kind,n):
        with self.lock:
            self.active=True; self.kind=kind; self.item=""; self.index=0; self.total_items=n; self.percent=None; self.downloaded=0; self.total_bytes=0; self.rate=0.; self.phase="preparing"; self.progress=OperationProgress(kind,OperationPhase.PREPARING,current=0,total=max(1,n))
    def _line(self,line):
        with self.lock:
            fields={x.split("=",1)[0]:x.split("=",1)[1] for x in line.split() if "=" in x}
            if "PROGRESS" in fields:
                try:self.percent=float(fields["PROGRESS"].rstrip("%"))
                except ValueError:pass
            if "DOWNLOADED" in fields:
                try:self.downloaded=int(fields["DOWNLOADED"])
                except ValueError:pass
            if "TOTAL" in fields:
                try:self.total_bytes=int(fields["TOTAL"])
                except ValueError:pass
            if "RATE" in fields:
                try:self.rate=float(fields["RATE"])
                except ValueError:pass
            if line.startswith("PHASE=") or line.startswith("STATUS="): self.phase=line.split("=",1)[1].strip().lower()
    def _run(self,cmd):
        try:p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        except OSError:return False
        if p.stdout:
            for line in p.stdout:self._line(line.strip())
        return p.wait()==0
    def finish(self,results):
        with self.lock:
            self.results=list(results); ok=all(x[1] for x in results); self.active=False; self.phase="completed" if ok else "failed"; self.progress=terminal_progress(self.kind,ok)
    def start_models(self,rows):
        if self.active or not rows:return False
        rows=list(rows); self.start("models",len(rows)); threading.Thread(target=self._models,args=(rows,),daemon=True).start(); return True
    def _models(self,rows):
        out=[]; MODELS_DIR.mkdir(exist_ok=True)
        for i,row in enumerate(rows,1):
            model=row.get("model_id","?")
            with self.lock:self.index=i;self.item=model;self.phase="downloading"
            out.append((model,self._run([sys.executable,str(INSTALLER),"--model-id",model,"--output-dir",str(MODELS_DIR)]))); self.results=list(out)
        self.finish(out)
    def start_software(self,components):
        if self.active or not components:return False
        components=list(components); self.start("software",len(components)); threading.Thread(target=self._software,args=(components,),daemon=True).start(); return True
    def _software(self,components):
        out=[]
        for i,c in enumerate(components,1):
            name=dict(SOFTWARE).get(c,c)
            with self.lock:self.index=i;self.item=name;self.phase="installing"
            out.append((name,self._run(["bash",str(INSTALL_SH),f"--{c}"]))); self.results=list(out)
        self.finish(out)
    def start_uninstall(self,components):
        if self.active or not components:return False
        components=list(components); self.start("uninstall",len(components)); threading.Thread(target=self._uninstall,args=(components,),daemon=True).start(); return True
    def _uninstall(self,components):
        out=[]
        for i,c in enumerate(components,1):
            name=dict(SOFTWARE).get(c,c)
            with self.lock:self.index=i;self.item=name;self.phase="removing"
            out.append((name,self._run(["bash",str(UNINSTALL_SH),"--yes",f"--{c}"]))); self.results=list(out)
        self.finish(out)

def run_operation(task,kind,items):
    """Single operation boundary used by the persistent progress panel."""
    if kind=="models": return task.start_models(items)
    if kind=="software": return task.start_software(items)
    if kind=="uninstall": return task.start_uninstall(items)
    return False

def run_recommendation(purposes):
    cmd=[sys.executable,str(RECOMMENDER),"--json"]
    for purpose in purposes: cmd.extend(("--purpose",purpose))
    try:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=120); data=json.loads(r.stdout); return data.get("status","error"),data
    except Exception as exc: return "error",{"message":str(exc)}

_CTX=None
def set_context(scr,lang,action):
    global _CTX; _CTX=(scr,lang,action)
def clear_context():
    global _CTX; _CTX=None
def confirm(scr,lang,question):
    if _CTX: _CTX[2].update(state=t(lang,"accept"),lines=[question],footer="[Y] sí   [N/ESC] no" if lang=="es" else "[Y] yes   [N/ESC] no")
    scr.timeout(-1)
    while True:
        key=scr.getch()
        if key in (ord('y'),ord('Y')): return True
        if key in (ord('n'),ord('N'),27): return False
def privilege_prompt(scr,lang):
    if os.geteuid()==0 or not shutil.which("sudo"): return True
    if subprocess.run(["sudo","-n","-v"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return True
    if _CTX: _CTX[2].update(state=t(lang,"authorize"),lines=["La operación requiere privilegios de administrador." if lang=="es" else "The operation requires administrator privileges.","[Y] Autorizar   [N/ESC] Cancelar"])
    scr.timeout(-1)
    while True:
        key=scr.getch()
        if key in (ord('n'),ord('N'),27): return False
        if key in (ord('y'),ord('Y')): break
    if _CTX:_CTX[2].update(state=t(lang,"authorize"),lines=[t(lang,"password"),t(lang,"hidden")])
    pwd=""; curses.echo(False)
    try:
        while True:
            key=scr.getch()
            if key in (10,13): break
            if key==27:return False
            if key in (8,127,curses.KEY_BACKSPACE):pwd=pwd[:-1]
            elif 32<=key<=126:pwd+=chr(key)
    finally:curses.echo(True)
    try:r=subprocess.run(["sudo","-S","-v"],input=pwd+"\n",text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    finally:pwd=""
    if r.returncode==0:return True
    if _CTX:_CTX[2].update(state=t(lang,"details"),lines=[t(lang,"failed_auth")])
    return False

def language_screen(scr):
    focus=0
    while True:
        scr.erase();h,w=scr.getmaxyx();bw=min(64,max(42,w-4));x=max(1,(w-bw)//2);box(scr,3,x,12,bw,"LEONES RC4");put(scr,5,x+4,"SELECCIONA IDIOMA / SELECT LANGUAGE",bw-8)
        for i,name in enumerate(("Español","English")):put(scr,8+i,x+8,f"{'>' if i==focus else ' '} [{i+1}] {name}",bw-16)
        put(scr,12,x+4,"↑/↓ · ENTER · Q",bw-8);scr.refresh();key=scr.getch()
        if key in (curses.KEY_UP,ord('k')):focus=(focus-1)%2
        elif key in (curses.KEY_DOWN,ord('j')):focus=(focus+1)%2
        elif key in (10,13):return ("es","en")[focus]
        elif key in (ord('1'),ord('2')):return ("es","en")[int(chr(key))-1]
        elif key in (ord('q'),ord('Q'),27):raise SystemExit

def draw_frame(scr,lang,nav,task):
    scr.erase();h,w=scr.getmaxyx()
    if h<28 or w<100:put(scr,1,2,"LEONES RC4 — terminal demasiado pequeña (mín. 100x28)",w-4);scr.refresh();return None
    box(scr,1,1,h-3,w-2,"LEONES RC4");navw=25;box(scr,3,3,h-7,navw,t(lang,"nav"))
    for i,(_,label) in enumerate(NAV):put(scr,5+i*2,6,f"{'>' if i==nav else ' '} [{i+1}] {label}",navw-6)
    x=30;rw=w-x-4;top=3;th=8;mid=12;mh=max(8,h-23);bot=mid+mh+1;bh=h-bot-4
    box(scr,top,x,th,rw,t(lang,"ops"));box(scr,mid,x,mh,rw,t(lang,"selection"));box(scr,bot,x,bh,rw,t(lang,"action"))
    s=task.snapshot();put(scr,5,x+2,f"● {t(lang,'active') if s['active'] else t(lang,'idle')}",rw-4);put(scr,6,x+2,f"{s['kind']} {s['item']}",rw-4);put(scr,7,x+2,f"{t(lang,'phase')}: {s['phase']}  {progress_bar(s['percent'])} {'' if s['percent'] is None else f'{s['percent']:.0f}%'}",rw-4)
    return x,rw,mid,mh,bot,bh

class ActionState:
    def __init__(self): self.state="";self.lines=[];self.footer=""

def run_app(scr):
    curses.curs_set(1);scr.nodelay(False);lang=language_screen(scr);nav=0;focus=0;task=TaskManager();action=ActionState();set_context(scr,lang,action);selected=[];intent=[]
    try:
        while True:
            frame=draw_frame(scr,lang,nav,task)
            if not frame: scr.getch();continue
            x,rw,mid,mh,bot,bh=frame
            if nav==2:
                put(scr,mid+2,x+2,t(lang,"intent"),rw-4);put(scr,mid+3,x+2,t(lang,"intent_help"),rw-4)
                for i,(key,label) in enumerate(PURPOSES):mark="[x]" if key in intent else "[ ]";put(scr,mid+5+i,x+4,f"{mark} {i+1}. {label}",rw-8)
                put(scr,mid+5+len(PURPOSES),x+2,"ENTER = recomendar",rw-4)
                if action.lines:
                    put(scr,bot+2,x+2,action.state or t(lang,"details"),rw-4)
                    for i,line in enumerate(action.lines[:max(1,bh-5)]):put(scr,bot+3+i,x+2,line,rw-4)
            elif nav==3:
                put(scr,mid+2,x+2,t(lang,"recommendation"),rw-4);put(scr,mid+3,x+2,t(lang,"estimated"),rw-4);put(scr,mid+4,x+2,t(lang,"measured"),rw-4)
                put(scr,mid+6,x+2,"Selecciona INTENCIÓN para obtener propuestas." if lang=="es" else "Select USE INTENT to obtain proposals.",rw-4)
            elif nav==4:
                models=local_models();put(scr,mid+2,x+2,"LLMs locales: "+str(len(models)),rw-4)
                for i,m in enumerate(models[:mh-5]):put(scr,mid+4+i,x+4,f"[{'x' if m in selected else ' '}] {m}",rw-8)
            elif nav==5:
                put(scr,mid+2,x+2,"SOFTWARE IA",rw-4)
                for i,(key,label) in enumerate(SOFTWARE):put(scr,mid+4+i,x+4,f"[{'x' if key in selected else ' '}] {label}",rw-8)
            elif nav==6:
                put(scr,mid+2,x+2,"DESINSTALACIÓN",rw-4);put(scr,mid+4,x+2,"Selecciona SOFTWARE IA y confirma abajo." if lang=="es" else "Select AI software and confirm below.",rw-4)
            elif nav==1:
                cpu,cores,gpu,ram,disk=machine_state();put(scr,mid+2,x+2,f"CPU: {cpu}",rw-4);put(scr,mid+3,x+2,f"Cores: {cores}  GPU: {gpu}",rw-4);put(scr,mid+4,x+2,f"RAM: {ram}",rw-4);put(scr,mid+5,x+2,f"DISCO: {disk}",rw-4);put(scr,mid+7,x+2,f"LLMs locales: {len(local_models())}",rw-4)
            else:
                put(scr,mid+2,x+2,t(lang,"home"),rw-4)
            if action.lines and nav!=2:
                put(scr,bot+2,x+2,action.state or t(lang,"details"),rw-4)
                for i,line in enumerate(action.lines[:max(1,bh-5)]):put(scr,bot+3+i,x+2,line,rw-4)
            put(scr,h-2 if (h:=scr.getmaxyx()[0]) else 0,2,f"{t(lang,'tab')} · {t(lang,'move')} · {t(lang,'open')} · {t(lang,'select')} · {t(lang,'back')} · {t(lang,'quit')}",scr.getmaxyx()[1]-4)
            scr.refresh();key=scr.getch()
            if key in (ord('q'),ord('Q')):break
            if key==9:focus=(focus+1)%2
            elif key in (curses.KEY_UP,ord('k')):nav=(nav-1)%len(NAV)
            elif key in (curses.KEY_DOWN,ord('j')):nav=(nav+1)%len(NAV)
            elif key in (ord('1'),ord('2'),ord('3'),ord('4'),ord('5'),ord('6'),ord('7')):nav=int(chr(key))-1
            elif key==ord(' '):
                if nav==2 and PURPOSES:
                    i=len(intent)%len(PURPOSES);k=PURPOSES[i][0];intent=[p for p in intent if p!=k] if k in intent else intent+[k]
                elif nav in (5,6):
                    i=len(selected)%len(SOFTWARE);k=SOFTWARE[i][0];selected=[p for p in selected if p!=k] if k in selected else selected+[k]
            elif key in (10,13):
                if nav==2:
                    if not intent: action.state=t(lang,"details");action.lines=["if not selected: Selecciona al menos un propósito." ];continue
                    status,data=run_recommendation(intent);action.state=status.upper();action.lines=[json.dumps(data,ensure_ascii=False)[:rw-4]]
                elif nav==4 and selected: run_operation(task,"models",[{"model_id":m} for m in selected])
                elif nav==5 and selected:
                    if confirm(scr,lang,t(lang,"confirm_install")) and privilege_prompt(scr,lang):run_operation(task,"software",selected)
                elif nav==6 and selected:
                    if confirm(scr,lang,t(lang,"confirm_uninstall")) and privilege_prompt(scr,lang):run_operation(task,"uninstall",selected)
    finally:clear_context()

def main():return curses.wrapper(run_app) or 0
if __name__=="__main__":raise SystemExit(main())
