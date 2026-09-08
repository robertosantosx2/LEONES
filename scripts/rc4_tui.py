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
"es":{"nav":"NAVEGACIÓN","ops":"OPERACIÓN / PROGRESO","selection":"SELECCIÓN / INFORMACIÓN PRINCIPAL","action":"ACCIÓN / ESCALADO / PRIVILEGIOS","active":"ACTIVA","idle":"SIN OPERACIONES","phase":"FASE","data":"DATOS","rate":"VELOCIDAD","tab":"TAB cambiar foco","move":"↑/↓ mover","open":"ENTER abrir","back":"ESC volver","quit":"Q salir","select":"SPACE select","details":"CARACTERÍSTICAS DE LA SELECCIÓN","accept":"ACEPTACIÓN","authorize":"AUTORIZACIÓN DEL SISTEMA","password":"Contraseña de sudo:","hidden":"Entrada oculta · ENTER confirma","cancelled":"Operación cancelada.","authorized":"Privilegios autorizados. Operación iniciada en segundo plano.","failed_auth":"No se pudo autorizar sudo. Operación cancelada.","requirements":"REQUISITOS","destination":"DESTINO","dependencies":"DEPENDENCIAS","consequences":"CONSECUENCIAS","state":"ESTADO","intent":"INTENCIÓN DE USO","intent_help":"Selecciona uno o varios propósitos","recommendation":"RECOMENDACIÓN RC4","estimated":"ESTIMATED · ejecución no autorizada · medición no autorizada","home":"Centro de control: puedes navegar mientras las operaciones continúan.","confirm_install":"¿Confirmar instalación de todos los seleccionados? [Y] sí / [N] no","confirm_uninstall":"¿Confirmar DESINSTALACIÓN de todos los seleccionados? [Y] sí / [N] no"},
"en":{"nav":"NAVIGATION","ops":"OPERATION / PROGRESS","selection":"SELECTION / MAIN INFORMATION","action":"ACTION / ESCALATION / PRIVILEGES","active":"ACTIVE","idle":"NO OPERATIONS","phase":"PHASE","data":"DATA","rate":"SPEED","tab":"TAB switch focus","move":"↑/↓ move","open":"ENTER open","back":"ESC back","quit":"Q quit","select":"SPACE select","details":"SELECTION CHARACTERISTICS","accept":"ACCEPTANCE","authorize":"SYSTEM AUTHORIZATION","password":"sudo password:","hidden":"Hidden input · ENTER confirms","cancelled":"Operation cancelled.","authorized":"Privileges authorized. Operation started in background.","failed_auth":"sudo authorization failed. Operation cancelled.","requirements":"REQUIREMENTS","destination":"DESTINATION","dependencies":"DEPENDENCIES","consequences":"CONSEQUENCES","state":"STATE","intent":"USE INTENT","intent_help":"Select one or more purposes","recommendation":"RC4 RECOMMENDATION","estimated":"ESTIMATED · execution not authorized · measurement not authorized","home":"Control center: you can navigate while operations continue.","confirm_install":"Confirm installation of all selected? [Y] yes / [N] no","confirm_uninstall":"Confirm UNINSTALL of all selected? [Y] yes / [N] no"}}

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
            self.active=True; self.kind=kind; self.item=""; self.index=0; self.total_items=n; self.percent=None; self.downloaded=0; self.total_bytes=0; self.rate=0.; self.phase="preparing"; self.results=[]; self.progress=OperationProgress(kind,OperationPhase.PREPARING,current=0,total=max(1,n))
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
    x=30;rw=w-x-4;top=3;th=8;mid=12;mh=max(8,h-23);bot=mid+mh+1;bh=max(5,h-bot-5)
    box(scr,top,x,th,rw,t(lang,"ops"));s=task.snapshot()
    if s["active"]:
        blink="●" if int(time.monotonic()*2)%2==0 else "○";put(scr,5,x+3,f"{blink} {t(lang,'active')} {s['kind'].upper()} {s['index']}/{s['total_items']} {s['item']}",rw-6);put(scr,6,x+3,f"{progress_bar(s['percent'])} {s['percent']:.1f}%" if s['percent'] is not None else f"{progress_bar(None)} -- %",rw-6);put(scr,7,x+3,f"{t(lang,'phase')}: {s['phase']}  {t(lang,'data')}: {human_bytes(s['downloaded'])}  {t(lang,'rate')}: {human_bytes(s['rate'])}/s",rw-6)
    else: put(scr,5,x+3,"○ "+(s["phase"] if s["phase"]!="idle" else t(lang,"idle")),rw-6)
    box(scr,mid,x,mh,rw,t(lang,"selection"));box(scr,bot,x,bh,rw,t(lang,"action"))
    return x,rw,mid,mh,bot,bh

def render_center(scr,lang,panel,state,geom):
    x,rw,mid,mh,_,_=geom;y=mid+2
    if panel=="home":put(scr,y,x+3,"LEONES RC4 — centro de control",rw-6);put(scr,y+2,x+3,t(lang,"home"),rw-6);return
    if panel=="state":
        cpu,cores,gpu,ram,disk=machine_state(); inv=inventory(); mods=local_models();
        lines=[f"HARDWARE: CPU {cpu} ({cores})",f"GPU {gpu}",f"RAM {ram}",f"DISCO {disk}",f"SOFTWARE IA INSTALADO: {', '.join(c.get('display_name',c.get('component_id','?')) for c in inv.get('components',[]) if c.get('installed')) or 'ninguno'}",f"LLMs LOCALES: {len(mods)} :: {', '.join(mods) or 'ninguno'}"]
        for i,line in enumerate(lines):put(scr,y+i,x+3,line,rw-6)
    elif panel=="intent":
        put(scr,y,x+3,"USER INTENT[] — "+t(lang,"intent_help"),rw-6)
        for i,(_,label) in enumerate(PURPOSES):put(scr,y+2+i,x+6,f"{'>' if i==state['focus'] else ' '} [{'X' if i in state['selected'] else ' '}] [{i+1}] {label}",rw-12)
    elif panel=="recommend":
        rows=(state.get("result") or {}).get("recommendations") or [];put(scr,y,x+3,f"{t(lang,'recommendation')}: {state.get('status','').upper()}",rw-6);put(scr,y+1,x+3,t(lang,"estimated"),rw-6)
        for i,row in enumerate(rows[:3]):put(scr,y+3+i,x+3,f"{'>' if i==state['focus'] else ' '} [{'X' if i in state['selected'] else ' '}] [{i+1}] {row.get('model_id','?')}",rw-6)
    elif panel=="models":
        put(scr,y,x+3,"LLMs LOCALES — usa R para recomendar",rw-6)
        for i,m in enumerate(local_models()[:10]):put(scr,y+2+i,x+3,"● "+m,rw-6)
    elif panel in ("software","uninstall"):
        if panel=="software":items=list(SOFTWARE);hint="Selecciona uno o varios componentes para instalar"
        else:items=[(c.get('component_id','?'),c.get('display_name',c.get('component_id','?'))) for c in inventory().get('components',[]) if c.get('installed') and c.get('uninstallable') and not c.get('offer_last')];hint="Selecciona uno o varios componentes instalados para desinstalar"
        put(scr,y,x+3,hint,rw-6)
        for i,(_,label) in enumerate(items[:10]):put(scr,y+2+i,x+6,f"{'>' if i==state['focus'] else ' '} [{'X' if i in state['selected'] else ' '}] [{i+1}] {label}",rw-12)

def selection_details(panel,state,lang):
    selected=state.get("selected",set())
    if panel=="intent":return [f"{t(lang,'state')}: {', '.join(PURPOSES[i][1] for i in sorted(selected)) or 'ninguno'}",f"{t(lang,'requirements')}: recomendador RC4 + evidencia externa"]
    if panel=="recommend":return [f"{t(lang,'state')}: {len(selected)} seleccionados",f"{t(lang,'requirements')}: artefacto descargable + evidencia",f"{t(lang,'destination')}: {MODELS_DIR}",f"{t(lang,'consequences')}: instalación del LLM; no autoriza medición"]
    if panel=="software":return [f"{t(lang,'state')}: {', '.join(SOFTWARE[i][1] for i in sorted(selected)) or 'ninguno'}",f"{t(lang,'requirements')}: privilegios del sistema si son necesarios",f"{t(lang,'consequences')}: instalación en segundo plano"]
    return [f"{t(lang,'state')}: {len(selected)} seleccionados",f"{t(lang,'consequences')}: eliminación del componente seleccionado"]

def render_action(scr,lang,action,geom):
    x,rw,_,_,bot,bh=geom;y=bot+2;put(scr,y,x+3,action.get("state") or t(lang,"details"),rw-6)
    for line in action.get("lines",[]):y+=1;put(scr,y,x+3,line,rw-6)
    if action.get("footer"):put(scr,bot+bh-2,x+3,action["footer"],rw-6)

def run_app(scr):
    scr.keypad(True);scr.timeout(200);lang=language_screen(scr)
    try:curses.curs_set(1)
    except curses.error:pass
    task=TaskManager();nav=0;focus="nav";panel="home";action={"state":"","lines":[],"footer":""};set_context(scr,lang,action)
    states={k:{"selected":set(),"focus":0} for k in ("intent","software","uninstall")};states["recommend"]={"selected":set(),"focus":0,"result":None,"status":"","purposes":[]}
    try:
        while True:
            geom=draw_frame(scr,lang,nav,task)
            if geom is None:scr.getch();continue
            state=states.get(panel,{})
            render_center(scr,lang,panel,state,geom)
            if not action.get("state"):action["state"]=t(lang,"details");action["lines"]=selection_details(panel,state,lang)
            render_action(scr,lang,action,geom)
            x,rw,mid,mh,bot,bh=geom;hint=f"TAB={t(lang,'tab')} | {t(lang,'move')} | ENTER={t(lang,'open')} | ESC={t(lang,'back')} | Q={t(lang,'quit')}";put(scr,2,32,hint,rw-4);put(scr,h-2 if (h:=scr.getmaxyx()[0]) else 0,4,hint,scr.getmaxyx()[1]-8)
            cy=5+nav*2 if focus=="nav" else mid+3+state.get("focus",0);cx=6 if focus=="nav" else x+4
            try:scr.move(min(scr.getmaxyx()[0]-2,cy),min(scr.getmaxyx()[1]-2,cx))
            except curses.error:pass
            scr.refresh();key=scr.getch()
            if key in (ord('q'),ord('Q')):return
            if key==9:focus="content" if focus=="nav" else "nav";continue
            if key==27:focus="nav";action={"state":"","lines":[],"footer":""};set_context(scr,lang,action);continue
            if focus=="nav":
                if key in (curses.KEY_UP,ord('k')):nav=(nav-1)%len(NAV)
                elif key in (curses.KEY_DOWN,ord('j')):nav=(nav+1)%len(NAV)
                elif ord('1')<=key<=ord('7'):nav=int(chr(key))-1
                elif key in (10,13):focus="content"
                panel=NAV[nav][0];continue
            state=states.get(panel,{})
            if panel=="intent":
                n=len(PURPOSES)
                if key in (curses.KEY_UP,ord('k')):state['focus']=(state['focus']-1)%n
                elif key in (curses.KEY_DOWN,ord('j')):state['focus']=(state['focus']+1)%n
                elif key==32:state['selected'].symmetric_difference_update({state['focus']})
                elif ord('1')<=key<=ord('7'):state['selected'].symmetric_difference_update({int(chr(key))-1});state['focus']=int(chr(key))-1
                elif key in (10,13):
                    selected=state['selected']
                    if not selected: action.update(state=t(lang,"details"),lines=["Debes seleccionar al menos un propósito."]);continue
                    purposes=[PURPOSES[i][0] for i in sorted(selected)];states['recommend']['purposes']=purposes;states['recommend']['status'],states['recommend']['result']=run_recommendation(purposes);states['recommend']['selected']=set();states['recommend']['focus']=0;panel="recommend";nav=3;action={"state":t(lang,"details"),"lines":[],"footer":""};set_context(scr,lang,action)
            elif panel=="recommend":
                rows=(state.get('result') or {}).get('recommendations') or [];n=min(3,len(rows))
                if key in (curses.KEY_UP,ord('k')) and n:state['focus']=(state['focus']-1)%n
                elif key in (curses.KEY_DOWN,ord('j')) and n:state['focus']=(state['focus']+1)%n
                elif key==32 and n:state['selected'].symmetric_difference_update({state['focus']})
                elif ord('1')<=key<=ord('3') and n:state['selected'].symmetric_difference_update({int(chr(key))-1});state['focus']=int(chr(key))-1
                elif key in (10,13):
                    selected=state['selected']
                    if not selected:action.update(state=t(lang,"details"),lines=["Selecciona al menos un modelo."]);continue
                    if task.active:continue
                    if confirm(scr,lang,t(lang,"confirm_install")):
                        run_operation(task,"models",[rows[i] for i in sorted(selected)]);state['selected']=set();action={"state":t(lang,"details"),"lines":["Operación enviada al panel superior."],"footer":""};set_context(scr,lang,action)
            elif panel=="software":
                n=len(SOFTWARE)
                if key in (curses.KEY_UP,ord('k')):state['focus']=(state['focus']-1)%n
                elif key in (curses.KEY_DOWN,ord('j')):state['focus']=(state['focus']+1)%n
                elif key==32:state['selected'].symmetric_difference_update({state['focus']})
                elif ord('1')<=key<=ord('5'):i=int(chr(key))-1;state['selected'].symmetric_difference_update({i});state['focus']=i
                elif key in (10,13):
                    selected=state['selected']
                    if not selected:action.update(state=t(lang,"details"),lines=["Selecciona al menos un componente."]);continue
                    if not task.active and confirm(scr,lang,t(lang,"confirm_install")) and privilege_prompt(scr,lang):run_operation(task,"software",[SOFTWARE[i][0] for i in sorted(selected)]);state['selected']=set()
                elif key in (ord('d'),ord('D')):panel="uninstall";nav=6;states['uninstall']={"selected":set(),"focus":0}
            elif panel=="uninstall":
                comps=[c for c in inventory().get('components',[]) if c.get('installed') and c.get('uninstallable') and not c.get('offer_last')];n=min(10,len(comps))
                if n:
                    if key in (curses.KEY_UP,ord('k')):state['focus']=(state['focus']-1)%n
                    elif key in (curses.KEY_DOWN,ord('j')):state['focus']=(state['focus']+1)%n
                    elif key==32:state['selected'].symmetric_difference_update({state['focus']})
                    elif ord('1')<=key<=ord(str(min(9,n))):i=int(chr(key))-1;state['selected'].symmetric_difference_update({i});state['focus']=i
                    elif key in (10,13):
                        selected=state['selected']
                        if not selected:action.update(state=t(lang,"details"),lines=["Selecciona al menos un componente."]);continue
                        if not task.active and confirm(scr,lang,t(lang,"confirm_uninstall")) and privilege_prompt(scr,lang):run_operation(task,"uninstall",[comps[i]['component_id'] for i in sorted(selected)]);state['selected']=set()
            elif panel=="models" and key in (ord('r'),ord('R')):panel="intent";nav=2
            action["lines"]=selection_details(panel,states.get(panel,{}),lang)
    finally:clear_context()

def main():return curses.wrapper(run_app) or 0
if __name__=="__main__":raise SystemExit(main())
