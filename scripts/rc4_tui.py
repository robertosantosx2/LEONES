#!/usr/bin/env python3
"""LEONES RC4 persistent control-center TUI.

Normative contract: docs/TUI_RULES_RC4.md
Only the language screen appears without the persistent navigation frame.
"""
from __future__ import annotations
import curses, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECOMMENDER=ROOT/"scripts/rc4_fitllm_recommend.py"; INSTALLER=ROOT/"scripts/rc4_model_install.py"
INVENTORY=ROOT/"scripts/rc4_component_inventory.py"; INSTALL_SH=ROOT/"install.sh"; UNINSTALL_SH=ROOT/"scripts/uninstall.sh"; MODELS_DIR=ROOT/"models"
PURPOSES=(("programming","PROGRAMMING"),("reasoning","REASONING"),("research","RESEARCH"),("chat","CHAT"),("multimodal","MULTIMODAL"),("embedding","EMBEDDING"),("general","GENERAL"))
SOFTWARE=(("fitllm","FitLLM"),("ods","ODS"),("magnitude","Magnitude"),("hermes","Hermes"),("omh","OMH"))
NAV=(("home","INICIO"),("state","ESTADO"),("intent","INTENCIÓN"),("recommend","RECOMENDADOR"),("models","LLMs / INSTALACIÓN"),("software","SOFTWARE IA"),("uninstall","DESINSTALACIÓN"))
TEXT={"es":{"nav":"NAVEGACIÓN","ops":"OPERACIÓN / PROGRESO","selection":"SELECCIÓN / INFORMACIÓN PRINCIPAL","action":"ACCIÓN / ESCALADO / PRIVILEGIOS","active":"ACTIVA","idle":"SIN OPERACIONES","phase":"FASE","data":"DATOS","rate":"VELOCIDAD","tab":"TAB cambiar foco","move":"↑/↓ mover","open":"ENTER abrir","back":"ESC volver","quit":"Q salir","select":"SPACE seleccionar","install":"INSTALAR","uninstall":"DESINSTALAR","confirm":"CONFIRMAR","none":"ninguno","machine":"ESTADO DE LA MÁQUINA","hardware":"HARDWARE","resources":"RECURSOS EN USO","software_installed":"SOFTWARE IA INSTALADO","models_local":"LLMs LOCALES","agents":"AGENTES","recommendation":"RECOMENDACIÓN RC4","intent":"INTENCIÓN DE USO","intent_help":"Selecciona uno o varios propósitos","recommend_now":"Selecciona la intención y pulsa ENTER para recomendar","model_select":"Selecciona uno o varios modelos recomendados","software_select":"Selecciona uno o varios componentes para instalar","uninstall_select":"Selecciona uno o varios componentes instalados para desinstalar","no_installed":"No hay componentes instalados para desinstalar.","confirm_install":"¿Confirmar instalación de todos los seleccionados? [Y] sí / [N] no","confirm_uninstall":"¿Confirmar DESINSTALACIÓN de todos los seleccionados? [Y] sí / [N] no","home":"Centro de control: puedes navegar mientras las operaciones continúan.","estimated":"ESTIMATED · ejecución no autorizada · medición no autorizada","details":"CARACTERÍSTICAS DE LA SELECCIÓN","accept":"ACEPTACIÓN","authorize":"AUTORIZACIÓN DEL SISTEMA","password":"Contraseña de sudo:","hidden":"Entrada oculta · ENTER confirma","authorized":"Privilegios autorizados. Operación iniciada en segundo plano.","cancelled":"Operación cancelada.","failed_auth":"No se pudo autorizar sudo. Operación cancelada.","requirements":"REQUISITOS","destination":"DESTINO","dependencies":"DEPENDENCIAS","consequences":"CONSECUENCIAS","state":"ESTADO"},"en":{"nav":"NAVIGATION","ops":"OPERATION / PROGRESS","selection":"SELECTION / MAIN INFORMATION","action":"ACTION / ESCALATION / PRIVILEGES","active":"ACTIVE","idle":"NO OPERATIONS","phase":"PHASE","data":"DATA","rate":"SPEED","tab":"TAB switch focus","move":"↑/↓ move","open":"ENTER open","back":"ESC back","quit":"Q quit","select":"SPACE select","install":"INSTALL","uninstall":"UNINSTALL","confirm":"CONFIRM","none":"none","machine":"MACHINE STATE","hardware":"HARDWARE","resources":"RESOURCES IN USE","software_installed":"INSTALLED AI SOFTWARE","models_local":"LOCAL LLMs","agents":"AGENTS","recommendation":"RC4 RECOMMENDATION","intent":"USE INTENT","intent_help":"Select one or more purposes","recommend_now":"Select the intent and press ENTER to recommend","model_select":"Select one or more recommended models","software_select":"Select one or more components to install","uninstall_select":"Select one or more installed components to uninstall","no_installed":"No installed components available for uninstall.","confirm_install":"Confirm installation of all selected? [Y] yes / [N] no","confirm_uninstall":"Confirm UNINSTALL of all selected? [Y] yes / [N] no","home":"Control center: you can navigate while operations continue.","estimated":"ESTIMATED · execution not authorized · measurement not authorized","details":"SELECTION CHARACTERISTICS","accept":"ACCEPTANCE","authorize":"SYSTEM AUTHORIZATION","password":"sudo password:","hidden":"Hidden input · ENTER confirms","authorized":"Privileges authorized. Operation started in background.","cancelled":"Operation cancelled.","failed_auth":"sudo authorization failed. Operation cancelled.","requirements":"REQUIREMENTS","destination":"DESTINATION","dependencies":"DEPENDENCIES","consequences":"CONSEQUENCES","state":"STATE"}}
def t(lang,k): return TEXT.get(lang,TEXT["es"]).get(k,k)
def put(s,y,x,text,width):
    if width<=0 or y<0 or y>=s.getmaxyx()[0]: return
    try:s.addnstr(y,max(0,x),str(text),width)
    except curses.error:pass
def box(s,y,x,h,w,title=""):
    if h<3 or w<4:return
    try:
        s.addstr(y,x,"+"+"-"*(w-2)+"+")
        for r in range(y+1,y+h-1):s.addstr(r,x,"|");s.addstr(r,x+w-1,"|")
        s.addstr(y+h-1,x,"+"+"-"*(w-2)+"+")
        if title:s.addstr(y,x+2,f"[ {title} ]")
    except curses.error:pass
def human_bytes(v):
    n=float(v or 0)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB":return f"{n:.1f} {u}"
        n/=1024
def bar(p,w=28):
    if p is None:return "["+"."*w+"]"
    n=max(0,min(w,round(w*p/100)));return "["+"#"*n+"."*(w-n)+"]"
def inventory():
    try:
        r=subprocess.run([sys.executable,str(INVENTORY),"--json"],cwd=ROOT,capture_output=True,text=True,timeout=20);return json.loads(r.stdout)
    except Exception:return {"components":[]}
def local_models():return sorted(p.name for p in MODELS_DIR.iterdir() if p.is_dir() and (p/".leones-installed.json").is_file()) if MODELS_DIR.is_dir() else []
def agents():
    out=[]
    for d in (ROOT/"agents",ROOT/".leones"/"agents"):
        if d.is_dir():out += [p.stem if p.is_file() else p.name for p in sorted(d.iterdir()) if not p.name.startswith(".")]
    return list(dict.fromkeys(out))
def memory_stats():
    try:
        v={};
        for l in Path("/proc/meminfo").read_text().splitlines():k,x=l.split(":",1);v[k]=int(x.split()[0])*1024
        return v["MemTotal"]-v["MemAvailable"],v["MemTotal"]
    except Exception:return 0,0
def hardware():
    cpu="estado no disponible"
    try:
        for l in Path("/proc/cpuinfo").read_text().splitlines():
            if l.lower().startswith("model name"):cpu=l.split(":",1)[1].strip();break
    except OSError:pass
    gpu="estado no disponible"
    if shutil.which("nvidia-smi"):
        try:
            r=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],capture_output=True,text=True,timeout=5)
            if r.returncode==0 and r.stdout.strip():gpu=r.stdout.strip().replace("\n","; ")
        except Exception:pass
    return cpu,os.cpu_count() or 1,gpu

class TaskManager:
    def __init__(self):self.lock=threading.Lock();self.active=False;self.kind="";self.item="";self.index=0;self.total_items=0;self.percent=None;self.downloaded=0;self.total_bytes=0;self.rate=0.;self.phase="idle";self.results=[]
    def snapshot(self):
        with self.lock:return self.__dict__.copy()
    def _start(self,k,n):
        with self.lock:self.active=True;self.kind=k;self.item="";self.index=0;self.total_items=n;self.percent=None;self.downloaded=0;self.total_bytes=0;self.rate=0.;self.phase="preparing";self.results=[]
    def _line(self,l):
        with self.lock:
            if l.startswith("PROGRESS="):
                f={x.split("=",1)[0]:x.split("=",1)[1] for x in l.split() if "=" in x}
                try:self.percent=float(f.get("PROGRESS","").rstrip("%"))
                except ValueError:pass
                for a in ("DOWNLOADED","TOTAL"):
                    try:setattr(self,a.lower() if a=="DOWNLOADED" else "total_bytes",int(f.get(a,getattr(self,a.lower() if a=="DOWNLOADED" else "total_bytes"))))
                    except ValueError:pass
                try:self.rate=float(f.get("RATE",self.rate))
                except ValueError:pass
            elif l.startswith("PHASE=") or l.startswith("STATUS="):self.phase=l.split("=",1)[1].strip().lower()
    def _run(self,c):
        try:p=subprocess.Popen(c,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        except OSError:return False
        if p.stdout:
            for l in p.stdout:self._line(l.strip())
        return p.wait()==0
    def _finish(self,r):
        with self.lock:self.active=False;self.phase="completed" if all(x[1] for x in r) else "completed_with_errors";self.results=list(r)
    def start_models(self,rows):
        if self.active or not rows:return False
        rows=list(rows);self._start("models",len(rows));threading.Thread(target=self._models,args=(rows,),daemon=True).start();return True
    def _models(self,rows):
        r=[];MODELS_DIR.mkdir(exist_ok=True)
        for i,row in enumerate(rows,1):
            m=row.get("model_id","?");
            with self.lock:self.index=i;self.item=m;self.phase="downloading"
            r.append((m,self._run([sys.executable,str(INSTALLER),"--model-id",m,"--output-dir",str(MODELS_DIR)])));self.results=list(r)
        self._finish(r)
    def start_software(self,cs):
        if self.active or not cs:return False
        cs=list(cs);self._start("software",len(cs));threading.Thread(target=self._software,args=(cs,),daemon=True).start();return True
    def _software(self,cs):
        r=[]
        for i,c in enumerate(cs,1):
            name=next((n for k,n in SOFTWARE if k==c),c)
            with self.lock:self.index=i;self.item=name;self.phase="installing"
            r.append((name,self._run(["bash",str(INSTALL_SH),f"--{c}"])));self.results=list(r)
        self._finish(r)
    def start_uninstall(self,cs):
        if self.active or not cs:return False
        cs=list(cs);self._start("uninstall",len(cs));threading.Thread(target=self._uninstall,args=(cs,),daemon=True).start();return True
    def _uninstall(self,cs):
        r=[]
        for i,c in enumerate(cs,1):
            name=next((n for k,n in SOFTWARE if k==c),c)
            with self.lock:self.index=i;self.item=name;self.phase="uninstalling"
            r.append((name,self._run(["bash",str(UNINSTALL_SH),"--yes",f"--{c}"])));self.results=list(r)
        self._finish(r)

_CTX=None
def set_context(scr,lang,action):
    global _CTX;_CTX=(scr,lang,action)
def clear_context():
    global _CTX;_CTX=None
def _action_box(title,lines,footer=""):
    if not _CTX:return
    scr,lang,a=_CTX; a["state"]=title;a["lines"]=list(lines);a["footer"]=footer

def confirm(scr,lang,title,question):
    _action_box(t(lang,"accept"),[question],"[Y] sí    [N/ESC] no" if lang=="es" else "[Y] yes    [N/ESC] no")
    scr.timeout(-1)
    while True:
        k=scr.getch()
        if k in (ord("y"),ord("Y")):return True
        if k in (ord("n"),ord("N"),27):_action_box(t(lang,"details"),[t(lang,"cancelled")]);return False

def privilege_prompt(scr,lang,operation):
    if os.geteuid()==0:return True
    if not shutil.which("sudo"):return True
    r=subprocess.run(["sudo","-n","-v"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if r.returncode==0:return True
    _action_box(t(lang,"authorize"),["La operación requiere privilegios de administrador." if lang=="es" else "The operation requires administrator privileges.","[Y] Autorizar    [N/ESC] Cancelar" if lang=="es" else "[Y] Authorize    [N/ESC] Cancel"])
    scr.timeout(-1)
    while True:
        k=scr.getch()
        if k in (ord("n"),ord("N"),27):_action_box(t(lang,"details"),[t(lang,"cancelled")]);return False
        if k in (ord("y"),ord("Y")):break
    _action_box(t(lang,"authorize"),[t(lang,"password"),t(lang,"hidden")])
    pwd="";curses.echo(False)
    try:
        while True:
            k=scr.getch()
            if k in (10,13):break
            if k==27:return False
            if k in (curses.KEY_BACKSPACE,127,8):pwd=pwd[:-1]
            elif 32<=k<=126:pwd+=chr(k)
    finally:curses.echo(True)
    try:r=subprocess.run(["sudo","-S","-v"],input=pwd+"\n",text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    finally:pwd=""
    if r.returncode==0:_action_box(t(lang,"details"),[t(lang,"authorized")]);return True
    _action_box(t(lang,"details"),[t(lang,"failed_auth")]);return False

def language_screen(scr):
    f=0
    while True:
        scr.erase();h,w=scr.getmaxyx();bw=min(64,max(42,w-4));x=max(1,(w-bw)//2);box(scr,3,x,12,bw,"LEONES RC4");put(scr,5,x+4,"SELECCIONA IDIOMA / SELECT LANGUAGE",bw-8)
        for i,n in enumerate(("Español","English")):put(scr,8+i,x+8,f"{'>' if i==f else ' '} [{i+1}] {n}",bw-16)
        put(scr,12,x+4,"↑/↓ · ENTER · Q",bw-8);scr.refresh();k=scr.getch()
        if k in (curses.KEY_UP,ord("k")):f=(f-1)%2
        elif k in (curses.KEY_DOWN,ord("j")):f=(f+1)%2
        elif k in (10,13,ord("1"),ord("2")):return ("es","en")[int(chr(k))-1] if k in (ord("1"),ord("2")) else ("es","en")[f]
        elif k in (ord("q"),ord("Q"),27):raise SystemExit

def draw_frame(scr,lang,focus,task,ni):
    scr.erase();h,w=scr.getmaxyx()
    if h<28 or w<100:put(scr,1,2,"LEONES RC4 — terminal demasiado pequeña (mín. 100x28)",w-4);scr.refresh();return False
    put(scr,0,max(2,(w-28)//2),"LEONES // CENTRO DE CONTROL RC4",28);box(scr,1,1,h-3,w-2,"LEONES RC4")
    navw=25;box(scr,3,3,h-7,navw,t(lang,"nav"))
    for i,(_,lab) in enumerate(NAV):put(scr,5+i*2,6,f"{'>' if i==ni else ' '} [{i+1}] {lab}",navw-6)
    x=30;rw=w-x-4; top=3; th=8; mid=11; mh=max(9,h-22); bot=mid+mh+1; bh=h-bot-5
    box(scr,top,x,th,rw,t(lang,"ops"));s=task.snapshot()
    if s["active"]:
        a="●" if int(time.monotonic()*2)%2==0 else "○";put(scr,5,x+3,f"{a} {t(lang,'active')} {s['kind'].upper()} {s['index']}/{s['total_items']} {s['item']}",rw-6);put(scr,6,x+3,f"{bar(s['percent'])} {s['percent']:.1f}%" if s['percent'] is not None else f"{bar(None)} -- %",rw-6);put(scr,7,x+3,f"{t(lang,'phase')}: {s['phase']}  {t(lang,'data')}: {human_bytes(s['downloaded'])}  {t(lang,'rate')}: {human_bytes(s['rate'])}/s",rw-6);put(scr,8,x+3,"● background / segundo plano",rw-6)
    else:
        put(scr,5,x+3,("○ "+s["phase"]) if s["phase"]!="idle" else "○ "+t(lang,"idle"),rw-6)
        if s["results"]:put(scr,6,x+3,f"RESULTADO: {sum(1 for _,ok in s['results'] if ok)}/{len(s['results'])}",rw-6)
    return (x,rw,mid,mh,bot,bh)

def details(scr,lang,a,lines=()):
    h,w=scr.getmaxyx();x=30;rw=w-x-4;box(scr,a[4],x,max(5,a[5]),rw,t(lang,"action"));y=a[4]+2;put(scr,y,x+3,a.get("state",t(lang,"details")),rw-6)
    for line in lines or a.get("lines",[]):y+=1;put(scr,y,x+3,line,rw-6)
    if a.get("footer"):put(scr,a[4]+a[5]-2,x+3,a["footer"],rw-6)

def center(scr,lang,panel,state,a):
    h,w=scr.getmaxyx();x=30;rw=w-x-4;box(scr,a[2],x,a[3],rw,t(lang,"selection"));y=a[2]+2
    if panel=="home":put(scr,y,x+3,t(lang,"home"),rw-6);return
    if panel=="state":
        u,tot=memory_stats();cpu,cores,gpu=hardware();du,dt=shutil.disk_usage(ROOT).used,shutil.disk_usage(ROOT).total;inv=inventory();mods=local_models();ags=agents();
        for line in (f"{t(lang,'hardware')}: CPU {cpu} ({cores})",f"GPU {gpu}",f"RAM {human_bytes(u)} / {human_bytes(tot)}",f"DISCO {human_bytes(du)} / {human_bytes(dt)}",f"{t(lang,'software_installed')}: "+", ".join(c.get('display_name',c.get('component_id','?')) for c in inv.get('components',[]) if c.get('installed')),f"{t(lang,'models_local')}: {len(mods)} :: {', '.join(mods) or t(lang,'none')}",f"{t(lang,'agents')}: {len(ags)} :: {', '.join(ags) or t(lang,'none')}"):put(scr,y,x+3,line,rw-6);y+=1
    elif panel=="intent":
        put(scr,y,x+3,t(lang,"intent_help"),rw-6)
        for i,(_,lab) in enumerate(PURPOSES):put(scr,y+2+i,x+6,f"{'>' if i==state['focus'] else ' '} [{'X' if i in state['selected'] else ' '}] [{i+1}] {lab}",rw-12)
    elif panel=="recommend":
        r=state.get("result") or {};rows=r.get("recommendations") or [];put(scr,y,x+3,f"STATUS: {state.get('status','').upper()}",rw-6);put(scr,y+1,x+3,t(lang,"estimated"),rw-6)
        for i,row in enumerate(rows[:3]):put(scr,y+3+i,x+3,f"{'>' if i==state['focus'] else ' '} [{'X' if i in state['selected'] else ' '}] [{i+1}] {row.get('model_id','?')}",rw-6)
    elif panel=="models":
        mods=local_models();put(scr,y,x+3,f"{t(lang,'models_local')}: {len(mods)}",rw-6)
        for i,m in enumerate(mods[:10]):put(scr,y+2+i,x+3,"● "+m,rw-6)
    elif panel in ("software","uninstall"):
        if panel=="software":items=list(SOFTWARE);hint=t(lang,"software_select")
        else:items=[(c.get('component_id','?'),c.get('display_name',c.get('component_id','?'))) for c in inventory().get('components',[]) if c.get('installed') and c.get('uninstallable') and not c.get('offer_last')];hint=t(lang,"uninstall_select")
        put(scr,y,x+3,hint,rw-6)
        for i,(_,lab) in enumerate(items[:10]):put(scr,y+2+i,x+6,f"{'>' if i==state['focus'] else ' '} [{'X' if i in state['selected'] else ' '}] [{i+1}] {lab}",rw-12)

def selection_details(panel,state,lang):
    if panel=="intent":
        names=[n for i,(_,n) in enumerate(PURPOSES) if i in state["selected"]];return [f"{t(lang,'state')}: {', '.join(names) or t(lang,'none')}",f"{t(lang,'requirements')}: recomendador RC4 + evidencia externa"]
    if panel=="recommend":
        rows=(state.get("result") or {}).get("recommendations") or [];sel=sorted(state["selected"]);return [f"{t(lang,'state')}: {len(sel)} seleccionados",f"{t(lang,'requirements')}: artefacto descargable + evidencia",f"{t(lang,'destination')}: {MODELS_DIR}",f"{t(lang,'consequences')}: instalación del LLM; no autoriza medición"]
    if panel=="software":
        sel=sorted(state["selected"]);names=[SOFTWARE[i][1] for i in sel];return [f"{t(lang,'state')}: {', '.join(names) or t(lang,'none')}",f"{t(lang,'requirements')}: privilegios del sistema si son necesarios",f"{t(lang,'consequences')}: instalación en segundo plano"]
    if panel=="uninstall":
        comps=[c for c in inventory().get('components',[]) if c.get('installed') and c.get('uninstallable') and not c.get('offer_last')];sel=sorted(state["selected"]);names=[comps[i].get('display_name',comps[i].get('component_id','?')) for i in sel if i<len(comps)];return [f"{t(lang,'state')}: {', '.join(names) or t(lang,'none')}",f"{t(lang,'consequences')}: eliminación del componente seleccionado"]
    return []

def recommend(ps):
    c=[sys.executable,str(RECOMMENDER),"--json"];[c.extend(("--purpose",p)) for p in ps]
    try:r=subprocess.run(c,cwd=ROOT,capture_output=True,text=True,timeout=120);d=json.loads(r.stdout);return d.get("status","error"),d
    except Exception as e:return "error",{"message":str(e)}

def run_app(scr):
    scr.keypad(True);scr.timeout(200);lang=language_screen(scr)
    try:curses.curs_set(1)
    except curses.error:pass
    task=TaskManager();ni=0;focus="nav";panel="home";cf=0
    states={k:{"selected":set(),"focus":0} for k in ("intent","software","uninstall")};states["recommend"]={"selected":set(),"focus":0,"result":None,"status":"","purposes":[]}
    action={"state":"","lines":[],"footer":""};set_context(scr,lang,action)
    try:
        while True:
            a=draw_frame(scr,lang,focus,task,ni)
            if not a:scr.getch();continue
            x,rw,mid,mh,bot,bh=a;center(scr,lang,panel,states.get(panel,{}),a);action["_geom"]=(bot,bh)
            if not action.get("state"):action["lines"]=selection_details(panel,states.get(panel,{}),lang);action["state"]=t(lang,"details")
            details(scr,lang,action)
            hint=f"TAB={t(lang,'tab')} | {t(lang,'move')} | ENTER={t(lang,'open')} | {t(lang,'back')} | {t(lang,'quit')}";put(scr,2,32,hint,rw-4);put(scr,scr.getmaxyx()[0]-2,4,(t(lang,"nav") if focus=="nav" else t(lang,"selection"))+" | "+hint,scr.getmaxyx()[1]-8)
            cy=5+ni*2 if focus=="nav" else max(mid+2,mid+3+cf);cx=6 if focus=="nav" else x+4
            try:scr.move(min(scr.getmaxyx()[0]-2,cy),min(scr.getmaxyx()[1]-2,cx))
            except curses.error:pass
            scr.refresh();k=scr.getch()
            if k in (ord('q'),ord('Q')):return
            if k==9:focus="content" if focus=="nav" else "nav";continue
            if k==27:
                action={"state":"","lines":[],"footer":""};set_context(scr,lang,action);focus="nav";continue
            if focus=="nav":
                if k in (curses.KEY_UP,ord('k')):ni=(ni-1)%len(NAV)
                elif k in (curses.KEY_DOWN,ord('j')):ni=(ni+1)%len(NAV)
                elif ord('1')<=k<=ord(str(len(NAV))):ni=int(chr(k))-1
                elif k in (10,13):focus="content"
                panel=NAV[ni][0];cf=0;continue
            st=states.get(panel)
            if panel in st if isinstance(st,dict) else False:
                pass
            if panel=="intent":
                n=len(PURPOSES)
                if k in (curses.KEY_UP,ord('k')):st['focus']=(st['focus']-1)%n;cf=st['focus']
                elif k in (curses.KEY_DOWN,ord('j')):st['focus']=(st['focus']+1)%n;cf=st['focus']
                elif k==32:st['selected'].symmetric_difference_update({st['focus']});action["state"]=t(lang,"details");action["lines"]=selection_details(panel,st,lang)
                elif ord('1')<=k<=ord('7'):i=int(chr(k))-1;st['selected'].symmetric_difference_update({i});st['focus']=i;cf=i
                elif k in (10,13) and st['selected']:
                    ps=[p for i,(p,_) in enumerate(PURPOSES) if i in st['selected']];states['recommend']['purposes']=ps;states['recommend']['status'],states['recommend']['result']=recommend(ps);states['recommend']['selected']=set();states['recommend']['focus']=0;panel='recommend';ni=3;cf=0;action={"state":t(lang,"details"),"lines":[],"footer":""};set_context(scr,lang,action)
            elif panel=="recommend":
                rows=(st.get('result') or {}).get('recommendations') or [];n=min(3,len(rows))
                if k in (curses.KEY_UP,ord('k')) and n:st['focus']=(st['focus']-1)%n;cf=st['focus']
                elif k in (curses.KEY_DOWN,ord('j')) and n:st['focus']=(st['focus']+1)%n;cf=st['focus']
                elif k==32 and n:st['selected'].symmetric_difference_update({st['focus']})
                elif ord('1')<=k<=ord('3') and n:i=int(chr(k))-1;st['selected'].symmetric_difference_update({i});st['focus']=i;cf=i
                elif k in (10,13) and st['selected'] and not task.active:
                    if confirm(scr,lang,t(lang,'confirm'),t(lang,'confirm_install')):
                        task.start_models([rows[i] for i in sorted(st['selected'])]);st['selected']=set();action={"state":t(lang,'details'),"lines":["Operación enviada al panel superior."],"footer":""};set_context(scr,lang,action)
            elif panel=="software":
                n=len(SOFTWARE)
                if k in (curses.KEY_UP,ord('k')):st['focus']=(st['focus']-1)%n;cf=st['focus']
                elif k in (curses.KEY_DOWN,ord('j')):st['focus']=(st['focus']+1)%n;cf=st['focus']
                elif k==32:st['selected'].symmetric_difference_update({st['focus']})
                elif ord('1')<=k<=ord('5'):i=int(chr(k))-1;st['selected'].symmetric_difference_update({i});st['focus']=i
                elif k in (10,13) and st['selected'] and not task.active:
                    if confirm(scr,lang,t(lang,'confirm'),t(lang,'confirm_install')):
                        if privilege_prompt(scr,lang,'install'):task.start_software([SOFTWARE[i][0] for i in sorted(st['selected'])]);st['selected']=set()
                elif k in (ord('d'),ord('D')):panel='uninstall';ni=6;states['uninstall']={"selected":set(),"focus":0}
            elif panel=="uninstall":
                comps=[c for c in inventory().get('components',[]) if c.get('installed') and c.get('uninstallable') and not c.get('offer_last')];n=min(10,len(comps))
                if n:
                    if k in (curses.KEY_UP,ord('k')):st['focus']=(st['focus']-1)%n
                    elif k in (curses.KEY_DOWN,ord('j')):st['focus']=(st['focus']+1)%n
                    elif k==32:st['selected'].symmetric_difference_update({st['focus']})
                    elif ord('1')<=k<=ord(str(min(9,n))):i=int(chr(k))-1;st['selected'].symmetric_difference_update({i});st['focus']=i
                    elif k in (10,13) and st['selected'] and not task.active:
                        if confirm(scr,lang,t(lang,'confirm'),t(lang,'confirm_uninstall')):
                            if privilege_prompt(scr,lang,'uninstall'):task.start_uninstall([comps[i]['component_id'] for i in sorted(st['selected'])]);st['selected']=set()
            elif panel=="models" and k in (ord('r'),ord('R')):panel='intent';ni=2
            cf=states.get(panel,{}).get('focus',0) if isinstance(states.get(panel,{}),dict) else 0
            if not action.get('state'):action["state"]=t(lang,"details")
    finally:clear_context()
def main():return curses.wrapper(run_app) or 0
if __name__=="__main__":raise SystemExit(main())
