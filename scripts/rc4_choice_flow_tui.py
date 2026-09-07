#!/usr/bin/env python3
"""RC4 human-choice flow: language -> machine state -> purposes -> models -> solution -> costs -> consent."""
from __future__ import annotations
import curses,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RECOMMENDER=ROOT/"scripts/rc4_fitllm_recommend.py"; CATALOG=ROOT/"catalogs/rc4_solutions.json"
PURPOSES=(("programming","PROGRAMMING"),("reasoning","REASONING"),("research","RESEARCH"),("chat","CHAT"),("multimodal","MULTIMODAL"),("embedding","EMBEDDING"),("general","GENERAL"))
SOLUTIONS=(("personal_assistant","PERSONAL AI ASSISTANT"),("soho","FULL SOHO"),("both","BOTH"))
T={"es":{"select":"SELECCIONA IDIOMA","keys":"↑/↓ · ENTER","nav":"NAVEGACIÓN","dash":"Panel","machine":"Estado de máquina","intent":"Intención","rec":"Recomendador","evidence":"Evidencia","legacy":"RC2 legado","settings":"Configuración","exit":"Salir","small":"LEONES RC4 TUI -- terminal demasiado pequeña (mín. 92x25)","resize":"Redimensiona la ventana. Q: salir"},"en":{"select":"SELECT LANGUAGE","keys":"↑/↓ · ENTER","nav":"NAVIGATION","dash":"Dashboard","machine":"Machine State","intent":"Intent","rec":"Recommender","evidence":"Evidence","legacy":"RC2 legacy","settings":"Settings","exit":"Exit","small":"LEONES RC4 TUI -- terminal too small (min 92x25)","resize":"Resize the window. Q: quit"},"zh":{"select":"选择语言","keys":"↑/↓ · ENTER","nav":"导航","dash":"仪表板","machine":"机器状态","intent":"意图","rec":"推荐器","evidence":"证据","legacy":"RC2 旧版","settings":"设置","exit":"退出","small":"LEONES RC4 TUI -- 终端太小（最小 92x25）","resize":"请调整窗口大小。Q：退出"}}
def tr(lang,key):return T.get(lang,T["es"]).get(key,key)
def human_bytes(v):
    if not isinstance(v,int) or v<0:return "UNKNOWN"
    n=float(v)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB":return f"{n:.1f} {u}"
        n/=1024
    return "UNKNOWN"
def disk_free():
    try:return shutil.disk_usage(ROOT).free
    except OSError:return None
def catalog():
    try:return json.loads(CATALOG.read_text()).get("solutions",{})
    except (OSError,json.JSONDecodeError):return {}
def run_recommendation(purposes):
    cmd=[sys.executable,str(RECOMMENDER),"--json"]
    for p in purposes:cmd += ["--purpose",p]
    try:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=False,timeout=90);return json.loads(r.stdout)
    except (OSError,subprocess.TimeoutExpired,json.JSONDecodeError):return {"status":"unavailable","recommendations":[]}
def model_cost(row):
    raw=row.get("raw") if isinstance(row.get("raw"),dict) else {}
    for k in ("size_bytes","disk_bytes","size","disk_size_bytes"):
        v=raw.get(k)
        if isinstance(v,int) and v>=0:return v
    return None
def solution_keys(solution):return ["personal_assistant","soho"] if solution=="both" else [solution]
def aggregate(models,solution):
    total=0;known=True
    for m in models:
        v=model_cost(m)
        if v is None:known=False
        else:total+=v
    for k in solution_keys(solution):
        v=catalog().get(k,{}).get("disk_bytes")
        if not isinstance(v,int):known=False
        else:total+=v
    return total if known else None
def add_box(s,y,x,h,w,title):
    if h<3 or w<4:return
    s.addstr(y,x,"+"+"-"*(w-2)+"+")
    for r in range(y+1,y+h-1):s.addstr(r,x,"|");s.addstr(r,x+w-1,"|")
    s.addstr(y+h-1,x,"+"+"-"*(w-2)+"+")
    if len(title)+4<w:s.addstr(y,x+2,"[ "+title+" ]")
def put(s,y,x,text,width):
    if 0<=y<s.getmaxyx()[0]:
        try:s.addstr(y,x,text[:max(0,width)])
        except curses.error:pass
def language_screen(s):
    focus=0;langs=(("es","Español"),("en","English"),("zh","中文"))
    while True:
        s.erase();h,w=s.getmaxyx();bw=min(70,max(40,w-4));x=max(1,(w-bw)//2);add_box(s,3,x,12,bw,"LEONES RC4")
        put(s,5,x+4,tr(langs[focus][0],"select"),bw-8)
        for i,(_,label) in enumerate(langs):put(s,8+i,x+8,(">" if i==focus else " ")+f" [{i+1}] {label}",bw-16)
        put(s,12,x+4,tr(langs[focus][0],"keys"),bw-8);k=s.getch()
        if k in (curses.KEY_UP,ord('k')):focus=(focus-1)%3
        elif k in (curses.KEY_DOWN,ord('j')):focus=(focus+1)%3
        elif k in (10,13,ord('1'),ord('2'),ord('3')):
            if k in (ord('1'),ord('2'),ord('3')):focus=int(chr(k))-1
            return langs[focus][0]
        elif k in (ord('q'),ord('Q')):raise SystemExit(0)
def machine_state_screen(s,language):
    while True:
        s.erase();h,w=s.getmaxyx()
        if h<25 or w<92:
            put(s,1,2,tr(language,'small'),w-4);put(s,3,2,tr(language,'resize'),w-4);s.refresh();
            if s.getch() in (ord('q'),ord('Q')):raise SystemExit(0)
            continue
        title={"es":"LEONES // ESTADO DE LA MÁQUINA","en":"LEONES // MACHINE STATE","zh":"LEONES // 机器状态"}[language];add_box(s,1,1,h-4,w-2,title);x=4
        try:
            m={}
            for line in Path('/proc/meminfo').read_text().splitlines():a,b=line.split(':',1);m[a]=int(b.split()[0])*1024
            total=m['MemTotal'];free=m['MemAvailable'];used=total-free
            put(s,3,x,"MEMORIA",w-8);put(s,4,x,f"TOTAL     {human_bytes(total)}",w-8);put(s,5,x,f"LIBRE     {human_bytes(free)}",w-8);put(s,6,x,f"EN USO    {human_bytes(used)} ({used*100//total}%)",w-8)
        except (OSError,KeyError,ValueError,ZeroDivisionError):put(s,3,x,"MEMORIA   UNKNOWN",w-8)
        try:
            load=os.getloadavg()[0];cores=os.cpu_count() or 1;put(s,8,x,f"CPU       carga 1m={load:.2f} · {load*100/cores:.1f}% lógico ({cores} CPUs)",w-8)
        except OSError:put(s,8,x,"CPU       UNKNOWN",w-8)
        try:
            u=shutil.disk_usage(ROOT);put(s,10,x,f"DISCO     libre {human_bytes(u.free)} / total {human_bytes(u.total)}",w-8)
        except OSError:put(s,10,x,"DISCO     UNKNOWN",w-8)
        put(s,12,x,"TOP 5 PROCESOS · MEMORIA",w-8)
        try:
            out=subprocess.run(['ps','-eo','pid,%mem,rss,comm','--sort=-%mem'],capture_output=True,text=True,check=False,timeout=5).stdout.splitlines()[1:6]
            for i,line in enumerate(out):put(s,13+i,x,line,w-8)
        except (OSError,subprocess.TimeoutExpired):put(s,13,x,"UNKNOWN",w-8)
        put(s,18,x,"TOP 5 PROCESOS · CPU",w-8)
        try:
            out=subprocess.run(['ps','-eo','pid,%cpu,%mem,comm','--sort=-%cpu'],capture_output=True,text=True,check=False,timeout=5).stdout.splitlines()[1:6]
            for i,line in enumerate(out):put(s,19+i,x,line,w-8)
        except (OSError,subprocess.TimeoutExpired):put(s,19,x,"UNKNOWN",w-8)
        put(s,h-2,x,"[ENTER] continuar   [Q] salir",w-8);s.refresh();k=s.getch()
        if k in (ord('q'),ord('Q')):raise SystemExit(0)
        if k in (10,13):return
def draw(s,phase,purposes,models,selected,solution,cursor,nav_focus,nav_index,language):
    s.erase();h,w=s.getmaxyx()
    if h<25 or w<92:put(s,1,2,tr(language,'small'),w-4);put(s,3,2,tr(language,'resize'),w-4);s.refresh();return
    title="LEONES // AI OPERATING SYSTEM v4";put(s,0,max(2,(w-len(title))//2),title,len(title));left=28;rx=left+3;rw=w-rx-2;top=7;by=top+2;mh=h-by-2
    add_box(s,1,1,h-3,left,tr(language,'nav')+(" <FOCUS>" if nav_focus else ""));nav=[tr(language,k) for k in ('dash','machine','intent','rec','evidence','legacy','settings','exit')]
    put(s,3,4,("> " if nav_focus and nav_index==0 else "[X] ")+"LEONES RC4",left-6)
    for i,n in enumerate(nav[:5]):put(s,4+i,6,("> " if nav_focus and nav_index==i+1 else "-> ")+n,left-8)
    for i,n in ((6,nav[5]),(7,nav[6]),(8,nav[7])):put(s,10+(i-6)*2,4,("> " if nav_focus and nav_index==i else "[ ] ")+n,left-6)
    add_box(s,1,rx,top,rw,"ESTADO DEL SISTEMA");add_box(s,by,rx,mh,rw,"ESPACIO DE TRABAJO RC4");x=rx+3;cw=rw-6
    labels=("1 PROPÓSITOS","2 MODELOS","3 SOLUCIÓN","4 COSTES","5 CONFIRMACIÓN");put(s,by+2,x,"  ".join((">" if i==phase else " ")+v for i,v in enumerate(labels)),cw);row=by+4
    if phase==0:
        put(s,row,x,"Selecciona uno o varios propósitos:",cw);row+=2
        for i,(k,n) in enumerate(PURPOSES):put(s,row+i,x,(">" if i==cursor and not nav_focus else " ")+f" [{'X' if k in purposes else ' '}] {n}",cw)
        put(s,row+len(PURPOSES)+1,x,"↑/↓ mover · ESPACIO seleccionar · ENTER continuar",cw)
    elif phase==1:
        put(s,row,x,"MODELOS COMPATIBLES / RECOMENDADOS · SELECCIÓN MÚLTIPLE · SIN LÍMITE ARTIFICIAL",cw);row+=2
        for i,m in enumerate(models):put(s,row+i,x,(">" if i==cursor and not nav_focus else " ")+f" [{'X' if i in selected else ' '}] {i+1:>2} {str(m.get('model_id','?'))[:44]} DISCO={human_bytes(model_cost(m))} ESTIMATED",cw)
        put(s,row+max(8,len(models))+1,x,"↑/↓ mover · ESPACIO seleccionar · ENTER continuar · R recalcular · B volver",cw)
    elif phase==2:
        cat=catalog();key=solution;info=cat.get(key,{})
        put(s,row,x,"SOLUCIÓN · ↑/↓ CAMBIA LA OPCIÓN Y ACTUALIZA SU FICHA",cw);row+=2
        for i,(k,n) in enumerate(SOLUTIONS):put(s,row+i,x,("> " if k==solution else "  ")+n,cw)
        row+=4
        put(s,row,x,"FUNCIONALIDADES:",cw);row+=1
        for f in info.get('functions',[]):put(s,row,x,"· "+f,cw);row+=1
        put(s,row,x,"USO HABITUAL: "+str(info.get('usage_profile','UNKNOWN')),cw);row+=2
        put(s,row,x,f"INSTALACIÓN: DISCO={human_bytes(info.get('disk_bytes'))} · RAM={human_bytes(info.get('ram_bytes'))} · CPU={info.get('cpu_load','UNKNOWN')} · VRAM={human_bytes(info.get('vram_bytes'))}",cw)
        put(s,h-3,x,"↑/↓ elegir · ENTER continuar · B volver",cw)
    elif phase==3:
        required=aggregate([models[i] for i in sorted(selected)],solution);free=disk_free();status='UNKNOWN' if required is None or free is None else ('SUFICIENTE' if free>=required else 'INSUFICIENTE');put(s,row,x,"COSTE DE LA SELECCIÓN",cw);row+=2
        for i in sorted(selected):put(s,row,x,f"{models[i].get('model_id','?')}: {human_bytes(model_cost(models[i]))} [ESTIMATED/UNKNOWN]",cw);row+=1
        for k in solution_keys(solution):
            info=catalog().get(k,{});put(s,row,x,f"{info.get('name',k)}: DISCO={human_bytes(info.get('disk_bytes'))} RAM={human_bytes(info.get('ram_bytes'))} CPU={info.get('cpu_load','UNKNOWN')} VRAM={human_bytes(info.get('vram_bytes'))}",cw);row+=1
        put(s,row+1,x,f"TOTAL INSTALACIÓN={human_bytes(required)} · DISCO LIBRE={human_bytes(free)}",cw);put(s,row+2,x,f"GATE DISCO={status} · INSTALACIÓN AUTORIZADA=NO",cw);put(s,row+4,x,"UNKNOWN no pasa el gate · no instalación parcial por defecto · B volver · ENTER continuar",cw)
    else:
        required=aggregate([models[i] for i in sorted(selected)],solution);free=disk_free();status='SUFICIENTE' if required is not None and free is not None and free>=required else ('UNKNOWN' if required is None or free is None else 'INSUFICIENTE');put(s,row,x,"CONFIRMACIÓN EXPLÍCITA",cw);row+=2
        for line in (f"Propósitos: {', '.join(purposes)}",f"Modelos: {len(selected)} seleccionado(s), sin límite artificial",f"Solución: {solution.upper()}",f"Disco: {status} · requerido={human_bytes(required)} · libre={human_bytes(free)}"):
            put(s,row,x,line,cw);row+=1
        put(s,row+2,x,"ENTER = registrar consentimiento · NO ejecuta instalación en esta capa",cw);put(s,row+4,x,"B volver · Q salir",cw)
    put(s,h-2,3,"TAB navegación · ↑/↓ mover · ENTER abrir/continuar · B volver · Q salir",w-6);s.refresh()
def main():
    def app(s):
        curses.curs_set(0);s.keypad(True);language=language_screen(s);machine_state_screen(s,language);phase=0;purposes=[];models=[];selected=set();solution='personal_assistant';cursor=0;nav_focus=False;nav_index=0
        while True:
            draw(s,phase,purposes,models,selected,solution,cursor,nav_focus,nav_index,language);k=s.getch()
            if k in (ord('q'),ord('Q')):return
            if k==9:nav_focus=not nav_focus;continue
            if nav_focus:
                if k in (curses.KEY_UP,ord('k')):nav_index=(nav_index-1)%9
                elif k in (curses.KEY_DOWN,ord('j')):nav_index=(nav_index+1)%9
                elif k in (10,13):
                    if nav_index==8:return
                    if nav_index==1:machine_state_screen(s,language)
                    nav_focus=False
                continue
            if phase==0:
                if k in (curses.KEY_UP,ord('k')):cursor=(cursor-1)%len(PURPOSES)
                elif k in (curses.KEY_DOWN,ord('j')):cursor=(cursor+1)%len(PURPOSES)
                elif k==ord(' '):p=PURPOSES[cursor][0];purposes.remove(p) if p in purposes else purposes.append(p)
                elif k in (10,13) and purposes:models=run_recommendation(purposes).get('recommendations') or [];selected=set();cursor=0;phase=1
            elif phase==1:
                if models and k in (curses.KEY_UP,ord('k')):cursor=(cursor-1)%len(models)
                elif models and k in (curses.KEY_DOWN,ord('j')):cursor=(cursor+1)%len(models)
                elif models and k==ord(' '):selected.remove(cursor) if cursor in selected else selected.add(cursor)
                elif k in (ord('r'),ord('R')):models=run_recommendation(purposes).get('recommendations') or [];selected=set();cursor=0
                elif k in (10,13) and selected:phase=2;cursor=0
                elif k in (ord('b'),ord('B')):phase=0;cursor=0
            elif phase==2:
                if k in (curses.KEY_UP,ord('k'),curses.KEY_DOWN,ord('j')):
                    i=[a for a,_ in SOLUTIONS].index(solution);solution=SOLUTIONS[(i+(1 if k in (curses.KEY_DOWN,ord('j')) else -1))%3][0]
                elif k in (10,13):phase=3
                elif k in (ord('b'),ord('B')):phase=1
            elif phase==3:
                if k in (ord('b'),ord('B')):phase=2
                elif k in (10,13):phase=4
            elif k in (ord('b'),ord('B')):phase=3
    curses.wrapper(app)
if __name__=='__main__':raise SystemExit(main())
