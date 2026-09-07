#!/usr/bin/env python3
from __future__ import annotations
import curses,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'scripts/rc4_fitllm_recommend.py'; INV=ROOT/'scripts/rc4_component_inventory.py'; INS=ROOT/'install.sh'; UN=ROOT/'scripts/uninstall.sh'
PURPOSES=(('programming','PROGRAMMING'),('reasoning','REASONING'),('research','RESEARCH'),('chat','CHAT'),('multimodal','MULTIMODAL'),('embedding','EMBEDDING'),('general','GENERAL'))
def inv():
 try:return json.loads(subprocess.run([sys.executable,str(INV),'--json'],cwd=ROOT,capture_output=True,text=True,timeout=20).stdout)
 except Exception:return {'components':[],'uninstall_offers':[]}
def comp(i,k):return next((x for x in i.get('components',[]) if x.get('component_id')==k),{})
def pctmem():
 try:
  d={x.split(':',1)[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()};return round((d['MemTotal']-d['MemAvailable'])*100/d['MemTotal'])
 except Exception:return 0
def pctcpu():
 try:return min(100,round(os.getloadavg()[0]*100/(os.cpu_count() or 1)))
 except Exception:return 0
def pctdisk():
 try:d=shutil.disk_usage(ROOT);return round(d.used*100/d.total)
 except Exception:return 0
def run(cmd):
 try:
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=False);return (p.stdout+p.stderr)[-1600:]
 except Exception as e:return str(e)
def put(s,y,x,t,w):
 if w>0:s.addstr(y,x,t[:w])
def box(s,y,x,h,w,title):
 if h<3 or w<4:return
 s.addstr(y,x,'+'+'-'*(w-2)+'+')
 for r in range(y+1,y+h-1):s.addstr(r,x,'|');s.addstr(r,x+w-1,'|')
 s.addstr(y+h-1,x,'+'+'-'*(w-2)+'+');s.addstr(y,x+2,'[ '+title+' ]')
def pause(s,msg):
 h,w=s.getmaxyx();put(s,h-2,2,msg,w-4);s.refresh();s.getch()
def ask(s,prompt):
 h,w=s.getmaxyx();curses.echo();curses.curs_set(1);put(s,h-2,2,prompt,w-4);s.refresh()
 try:v=s.getstr(h-1,2,max(1,w-5)).decode('utf8','replace').strip()
 finally:curses.noecho();curses.curs_set(0)
 return v
def recommend(ps):
 try:
  c=[sys.executable,str(REC),'--json']
  for p in ps:c += ['--purpose',p]
  r=subprocess.run(c,cwd=ROOT,capture_output=True,text=True,check=False);d=json.loads(r.stdout);return d.get('status','error'),d
 except Exception as e:return 'error',{'message':str(e)}
def draw(s,i,sel,focus,phase,status='',result=None):
 s.erase();h,w=s.getmaxyx()
 if h<25 or w<92:put(s,1,2,'LEONES RC4 TUI -- terminal demasiado pequena (min 92x25)',w-4);s.refresh();return
 put(s,0,max(2,(w-46)//2),'LEONES // AI OPERATING SYSTEM v4',46);lw=27;rx=30;rw=w-rx-2
 box(s,1,1,h-3,lw,'NAVIGATION')
 nav=['Idioma','Estado de la máquina','Propósito(s)','Evidencia','Recomendación','Selección','Stack','Runtime / Benchmark']
 for n,x in enumerate(nav):put(s,3+n,4,('>' if x==phase else ' ')+' '+x,lw-6)
 box(s,1,rx,8,rw,'ESTADO DE LA MÁQUINA');put(s,3,rx+3,f'CPU {pctcpu():3}%   RAM {pctmem():3}%   DISCO {pctdisk():3}%',rw-6)
 names=(('fitllm','FitLLM'),('ods','ODS'),('magnitude','Magnitude'),('llms','LLMs'),('hermes','Hermes'),('omh','OMH'))
 put(s,5,rx+3,'IA: '+' '.join(f'{n}={"OK" if comp(i,k).get("installed") else "--"}' for k,n in names[:3]),rw-6)
 put(s,6,rx+3,'    '+' '.join(f'{n}={"OK" if comp(i,k).get("installed") else "--"}' for k,n in names[3:]),rw-6)
 wy=11;box(s,wy,rx,h-wy-3,rw,'RC4 WORKSPACE');x=rx+3;cw=rw-6;put(s,wy+2,x,'FASE: '+phase.upper(),cw)
 if phase=='Idioma':put(s,wy+4,x,'> Español',cw);put(s,wy+5,x,'  English',cw)
 elif phase=='Estado de la máquina':
  put(s,wy+4,x,'Hardware + recursos + software IA',cw);put(s,wy+6,x,'FitLLM ausente -> ENTER para instalar FitLLM',cw) if not comp(i,'fitllm').get('installed') else put(s,wy+6,x,'FitLLM disponible -> ENTER para continuar',cw)
 elif phase=='Propósito(s)':
  put(s,wy+4,x,'USER_INTENT[] · selección múltiple',cw)
  for n,(k,l) in enumerate(PURPOSES):put(s,wy+6+n,x,f'{">" if n==focus else " "} [{"X" if k in sel else " "}] {n+1}. {l}',cw)
 elif phase=='Evidencia':put(s,wy+4,x,'Hugging Face + Artificial Analysis',cw);put(s,wy+5,x,'Feed <=100 -> intersección -> LLMFit',cw);put(s,wy+7,x,'ENTER para ejecutar recomendación',cw)
 elif phase=='Recomendación':
  put(s,wy+4,x,'STATUS: '+(status or 'READY').upper(),cw);rows=(result or {}).get('recommendations') or []
  for n,r in enumerate(rows[:3],1):put(s,wy+6+n,x,f'[{n}] {r.get("model_id","?")} :: ESTIMATED',cw)
  if not rows and result:put(s,wy+6,x,result.get('message','Sin candidatos'),cw)
 elif phase=='Selección':put(s,wy+4,x,'El usuario elige el modelo. ESTIMATED no autoriza ejecución.',cw)
 elif phase=='Stack':put(s,wy+4,x,'> Magnitude',cw);put(s,wy+5,x,'  ODS',cw);put(s,wy+6,x,'  ninguno',cw);put(s,wy+8,x,'G = gestionar/instalar   D = desinstalar   ENTER = continuar',cw)
 else:put(s,wy+4,x,'Runtime -> A01 -> MEASURED',cw);put(s,wy+5,x,'Doble autorización: ejecución + medición',cw)
 put(s,h-1,2,'TAB/ARROWS mover  SPACE seleccionar  ENTER aceptar  B volver  Q salir',w-4);s.refresh()
def manage(s,i):
 opts=['LLMs seleccionados','Instalar LLM concreto (ruta completa)','ODS','Magnitude','otros'];f=0
 while 1:
  draw(s,i,set(),f,'Stack');h,w=s.getmaxyx();box(s,14,34,10,w-36,'GESTIONAR / INSTALAR')
  for n,o in enumerate(opts):put(s,16+n,37,('> ' if n==f else '  ')+o,w-40)
  k=s.getch()
  if k in (ord('b'),ord('B'),27):return
  if k in (curses.KEY_UP,ord('k')):f=(f-1)%len(opts)
  elif k in (curses.KEY_DOWN,ord('j')):f=(f+1)%len(opts)
  elif k in (10,13):
   if f==0:pause(s,'LLMs seleccionados: selección conservada; se solicita artefacto/ruta. ENTER')
   elif f==1:
    p=ask(s,'Ruta completa del fichero LLM: ')
    if p:pause(s,'Ruta recibida: '+p+' | validación antes de instalar. ENTER')
   elif f==2:pause(s,run([str(INS),'--ods'])+' ENTER')
   elif f==3:pause(s,run([str(INS),'--magnitude'])+' ENTER')
   else:pause(s,'Otros componentes: instalación explícita, sin bootstrap implícito. ENTER')
   return
def unmanage(s,i):
 offers=[x for x in i.get('uninstall_offers',[]) if x.get('component_id')!='leones'];opts=[(x['display_name'],x['uninstall_flag']) for x in offers]+[('Cancelar',None)];f=0
 while 1:
  draw(s,i,set(),f,'Stack');h,w=s.getmaxyx();box(s,14,34,min(13,5+len(opts)),w-36,'DESINSTALAR')
  for n,(o,_) in enumerate(opts):put(s,16+n,37,('> ' if n==f else '  ')+o,w-40)
  k=s.getch()
  if k in (ord('b'),ord('B'),27):return
  if k in (curses.KEY_UP,ord('k')):f=(f-1)%len(opts)
  elif k in (curses.KEY_DOWN,ord('j')):f=(f+1)%len(opts)
  elif k in (10,13):
   _,flag=opts[f]
   if not flag:return
   if flag=='--llms':
    models=comp(i,'llms').get('models',[]);name=ask(s,'Modelo a desinstalar (nombre exacto): ')
    if name in models:pause(s,run(['ollama','rm',name])+' ENTER')
   else:pause(s,run(['bash',str(UN),flag])+' ENTER')
   return
def main():
 sel=set();focus=0;phase='Idioma';status='ready';result=None;i=inv()
 def app(s):
  nonlocal focus,phase,status,result,i
  curses.curs_set(0);s.keypad(True)
  while 1:
   draw(s,i,sel,focus,phase,status,result);k=s.getch()
   if k in (ord('q'),ord('Q')):return
   if k in (ord('b'),ord('B')):
    phase={'Propósito(s)':'Estado de la máquina','Evidencia':'Propósito(s)','Recomendación':'Propósito(s)','Selección':'Recomendación','Stack':'Selección','Runtime / Benchmark':'Stack'}.get(phase,phase);continue
   if phase=='Idioma' and k in (10,13):phase='Estado de la máquina'
   elif phase=='Estado de la máquina' and k in (10,13):
    if not comp(i,'fitllm').get('installed'):pause(s,run([str(INS),'--fitllm'])+' ENTER');i=inv()
    phase='Propósito(s)'
   elif phase=='Propósito(s)':
    if k in (curses.KEY_UP,ord('k')):focus=(focus-1)%len(PURPOSES)
    elif k in (curses.KEY_DOWN,ord('j')):focus=(focus+1)%len(PURPOSES)
    elif k==ord(' '):
     key=PURPOSES[focus][0];sel.remove(key) if key in sel else sel.add(key)
    elif k in (10,13) and sel:phase='Evidencia'
   elif phase=='Evidencia' and k in (10,13):status,result=recommend([p for p,_ in PURPOSES if p in sel]);phase='Recomendación'
   elif phase=='Recomendación' and k in (10,13):phase='Selección'
   elif phase=='Selección' and k in (10,13):phase='Stack'
   elif phase=='Stack':
    if k in (ord('g'),ord('G'),ord('s'),ord('S')):manage(s,i);i=inv()
    elif k in (ord('d'),ord('D')):unmanage(s,i);i=inv()
    elif k in (10,13):phase='Runtime / Benchmark'
   elif phase=='Runtime / Benchmark' and k in (ord('r'),ord('R')):phase='Stack'
 curses.wrapper(app);return 0
if __name__=='__main__':raise SystemExit(main())
