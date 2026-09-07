#!/usr/bin/env python3
"""RC4 human-choice TUI: language -> machine -> purposes -> models -> solution -> cost -> consent."""
from __future__ import annotations
import curses, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RECOMMENDER=ROOT/'scripts/rc4_fitllm_recommend.py'; CATALOG=ROOT/'catalogs/rc4_solutions.json'
PURPOSES=('programming','reasoning','research','chat','multimodal','embedding','general'); SOLUTIONS=('personal_assistant','soho','both')
T={
'es':{'language':'IDIOMA','es':'Español','en':'Inglés','zh':'Chino','nav':'NAVEGACIÓN','dashboard':'Panel','machine':'Estado de máquina','intent':'Intención','recommender':'Recomendador','evidence':'Evidencia','settings':'Configuración','exit':'Salir','system':'ESTADO DEL SISTEMA','workspace':'ESPACIO DE TRABAJO RC4','focus':'FOCO','unknown':'UNKNOWN','measured':'MEDIDO','declared':'DECLARADO','estimated':'ESTIMADO','purposes':'PROPÓSITOS','purpose_prompt':'Selecciona uno o varios propósitos:','models':'MODELOS','models_prompt':'MODELOS COMPATIBLES / RECOMENDADOS · SELECCIÓN MÚLTIPLE · SIN LÍMITE ARTIFICIAL','solution':'SOLUCIÓN','solution_prompt':'Selecciona la solución de despliegue:','cost':'COSTE DE LA SELECCIÓN','confirm':'CONFIRMACIÓN EXPLÍCITA','programming':'PROGRAMACIÓN','reasoning':'RAZONAMIENTO','research':'INVESTIGACIÓN','chat':'CHAT / ASISTENTE','multimodal':'MULTIMODAL','embedding':'EMBEDDINGS / BÚSQUEDA','general':'USO GENERAL','personal_assistant':'ASISTENTE IA PERSONAL','soho':'SOHO COMPLETO','both':'PERSONAL + SOHO','personal_desc':'Asistente personal local para un usuario principal.','soho_desc':'Servicios de IA locales para varios usuarios y servicios compartidos.','personal_functions':'chat local; asistencia personal; acceso a modelos seleccionados; documentos y contexto locales; interacción local de un solo usuario','soho_functions':'servicio multiusuario; servicios de IA locales; acceso a modelos seleccionados; endpoints locales compartidos; operación orientada a servicios','personal_usage':'Uso interactivo y por ráfagas; el consumo depende del modelo, contexto y concurrencia.','soho_usage':'Puede haber uso concurrente y sostenido; el consumo depende del modelo, concurrencia, contexto y servicios.','memory':'MEMORIA','total':'TOTAL','free':'LIBRE','used':'EN USO','cpu':'CPU','load':'CARGA 1 MIN','logical':'LÓGICOS','disk':'DISCO','top_mem':'TOP 5 PROCESOS · MEMORIA','top_cpu':'TOP 5 PROCESOS · CPU','functions':'FUNCIONALIDADES','usage':'USO HABITUAL','install':'INSTALACIÓN','ram':'RAM','vram':'VRAM','required':'REQUERIDO','sufficient':'SUFICIENTE','insufficient':'INSUFICIENTE','gate':'GATE DISCO','move':'↑/↓ mover','space':'ESPACIO seleccionar','enter':'ENTER abrir/continuar','tab':'TAB navegación','back':'B volver','quit':'Q salir','consent':'ENTER = registrar consentimiento','no_install':'NO ejecuta instalación en esta capa','models_count':'Modelos: {n} seleccionado(s), sin límite artificial','unknown_gate':'UNKNOWN no pasa el gate · no instalación parcial por defecto'},
'en':{'language':'LANGUAGE','es':'Spanish','en':'English','zh':'Chinese','nav':'NAVIGATION','dashboard':'Dashboard','machine':'Machine State','intent':'Intent','recommender':'Recommender','evidence':'Evidence','settings':'Settings','exit':'Exit','system':'SYSTEM STATE','workspace':'RC4 WORKSPACE','focus':'FOCUS','unknown':'UNKNOWN','measured':'MEASURED','declared':'DECLARED','estimated':'ESTIMATED','purposes':'PURPOSES','purpose_prompt':'Select one or more purposes:','models':'MODELS','models_prompt':'COMPATIBLE / RECOMMENDED MODELS · MULTI-SELECTION · NO ARTIFICIAL LIMIT','solution':'SOLUTION','solution_prompt':'Select deployment solution:','cost':'SELECTION COST','confirm':'EXPLICIT CONFIRMATION','programming':'PROGRAMMING','reasoning':'REASONING','research':'RESEARCH','chat':'CHAT / ASSISTANT','multimodal':'MULTIMODAL','embedding':'EMBEDDINGS / SEARCH','general':'GENERAL USE','personal_assistant':'PERSONAL AI ASSISTANT','soho':'FULL SOHO','both':'PERSONAL + SOHO','personal_desc':'Local personal assistant for one primary user.','soho_desc':'Local AI services for multiple users and shared services.','personal_functions':'local chat; personal assistance; selected model access; local documents and context; single-user local interaction','soho_functions':'multi-user service; local AI services; selected model access; shared local endpoints; service-oriented operation','personal_usage':'Interactive and bursty use; consumption depends on model, context and concurrency.','soho_usage':'Concurrent and sustained use is possible; consumption depends on model, concurrency, context and services.','memory':'MEMORY','total':'TOTAL','free':'FREE','used':'IN USE','cpu':'CPU','load':'1 MIN LOAD','logical':'LOGICAL','disk':'DISK','top_mem':'TOP 5 PROCESSES · MEMORY','top_cpu':'TOP 5 PROCESSES · CPU','functions':'FUNCTIONS','usage':'NORMAL USE','install':'INSTALLATION','ram':'RAM','vram':'VRAM','required':'REQUIRED','sufficient':'SUFFICIENT','insufficient':'INSUFFICIENT','gate':'DISK GATE','move':'↑/↓ move','space':'SPACE select','enter':'ENTER open/continue','tab':'TAB navigation','back':'B back','quit':'Q quit','consent':'ENTER = record consent','no_install':'DOES NOT execute installation in this layer','models_count':'Models: {n} selected, no artificial limit','unknown_gate':'UNKNOWN does not pass the gate · no partial installation by default'},
'zh':{'language':'语言','es':'西班牙语','en':'英语','zh':'中文','nav':'导航','dashboard':'仪表板','machine':'机器状态','intent':'意图','recommender':'推荐器','evidence':'证据','settings':'设置','exit':'退出','system':'系统状态','workspace':'RC4 工作区','focus':'焦点','unknown':'未知','measured':'已测量','declared':'已声明','estimated':'估算','purposes':'用途','purpose_prompt':'选择一个或多个用途：','models':'模型','models_prompt':'兼容 / 推荐模型 · 多选 · 无人为数量限制','solution':'方案','solution_prompt':'选择部署方案：','cost':'选择成本','confirm':'明确确认','programming':'编程','reasoning':'推理','research':'研究','chat':'聊天 / 助手','multimodal':'多模态','embedding':'嵌入 / 搜索','general':'通用用途','personal_assistant':'个人 AI 助手','soho':'完整 SOHO','both':'个人助手 + SOHO','personal_desc':'面向主要用户的本地个人助手。','soho_desc':'面向多用户和共享服务的本地 AI 服务。','personal_functions':'本地聊天；个人助理；访问所选模型；本地文档和上下文；单用户本地交互','soho_functions':'多用户服务；本地 AI 服务；访问所选模型；共享本地端点；面向服务的运行','personal_usage':'交互式、突发式使用；资源消耗取决于模型、上下文和并发。','soho_usage':'可进行并发和持续使用；资源消耗取决于模型、并发、上下文和服务。','memory':'内存','total':'总计','free':'可用','used':'使用中','cpu':'CPU','load':'1分钟负载','logical':'逻辑','disk':'磁盘','top_mem':'内存占用前5个进程','top_cpu':'CPU占用前5个进程','functions':'功能','usage':'正常使用','install':'安装','ram':'内存','vram':'显存','required':'需要','sufficient':'足够','insufficient':'不足','gate':'磁盘门禁','move':'↑/↓ 移动','space':'空格 选择','enter':'ENTER 打开/继续','tab':'TAB 导航','back':'B 返回','quit':'Q 退出','consent':'ENTER = 记录同意','no_install':'本层不会执行安装','models_count':'模型：已选择 {n} 个，无人为数量限制','unknown_gate':'未知值不能通过门禁 · 默认不进行部分安装'}}
def tr(lang,key,**kw): return T.get(lang,T['es']).get(key,key).format(**kw)
def hb(v,lang):
 if not isinstance(v,int) or v<0:return tr(lang,'unknown')
 n=float(v)
 for u in ('B','KB','MB','GB','TB'):
  if n<1024 or u=='TB':return f'{n:.1f} {u}'
  n/=1024
 return tr(lang,'unknown')
def put(s,y,x,text,width):
 if 0<=y<s.getmaxyx()[0] and width>0:
  try:s.addstr(y,x,str(text)[:width])
  except curses.error:pass
def box(s,y,x,h,w,title):
 if h<3 or w<4:return
 try:
  s.addstr(y,x,'+'+'-'*(w-2)+'+')
  for r in range(y+1,y+h-1):s.addstr(r,x,'|');s.addstr(r,x+w-1,'|')
  s.addstr(y+h-1,x,'+'+'-'*(w-2)+'+')
  if len(title)+4<w:s.addstr(y,x+2,'[ '+title+' ]')
 except curses.error:pass
def machine_data():
 d={'mem':None,'cpu':None,'disk':None,'memtop':[],'cputop':[]}
 try:
  m={}
  for line in Path('/proc/meminfo').read_text().splitlines():k,r=line.split(':',1);m[k]=int(r.split()[0])*1024
  d['mem']=(m['MemTotal'],m['MemAvailable'],m['MemTotal']-m['MemAvailable'])
 except Exception:pass
 try:d['cpu']=(os.getloadavg()[0],os.cpu_count() or 1)
 except OSError:pass
 try:d['disk']=shutil.disk_usage(ROOT)
 except OSError:pass
 for key,cmd in (('memtop',['ps','-eo','pid,%mem,rss,comm','--sort=-%mem']),('cputop',['ps','-eo','pid,%cpu,%mem,comm','--sort=-%cpu'])):
  try:d[key]=subprocess.run(cmd,capture_output=True,text=True,timeout=5).stdout.splitlines()[1:6]
  except Exception:pass
 return d
def machine_screen(s,lang):
 while True:
  s.erase();h,w=s.getmaxyx();d=machine_data();box(s,1,1,h-3,w-2,'LEONES // '+tr(lang,'machine'));x=4
  if d['mem']:
   total,free,used=d['mem'];put(s,3,x,f"{tr(lang,'memory')} [{tr(lang,'measured')}]: {hb(total,lang)} {tr(lang,'total').lower()} · {hb(free,lang)} {tr(lang,'free').lower()} · {hb(used,lang)} {tr(lang,'used').lower()}",w-8)
  if d['cpu']:
   load,cores=d['cpu'];put(s,5,x,f"{tr(lang,'cpu')} [{tr(lang,'measured')}]: {load:.2f} {tr(lang,'load')} · {load*100/cores:.1f}% · {cores} {tr(lang,'logical')}",w-8)
  if d['disk']:put(s,7,x,f"{tr(lang,'disk')} [{tr(lang,'measured')}]: {hb(d['disk'].free,lang)} {tr(lang,'free').lower()} / {hb(d['disk'].total,lang)} {tr(lang,'total').lower()}",w-8)
  put(s,9,x,f"{tr(lang,'top_mem')} [{tr(lang,'measured')}]");
  for i,line in enumerate(d['memtop']):put(s,10+i,x,line,w-8)
  put(s,16,x,f"{tr(lang,'top_cpu')} [{tr(lang,'measured')}]");
  for i,line in enumerate(d['cputop']):put(s,17+i,x,line,w-8)
  put(s,h-2,x,f"{tr(lang,'enter')} · {tr(lang,'quit')}",w-8);s.refresh();k=s.getch()
  if k in (10,13,ord('b'),ord('B')):return
  if k in (ord('q'),ord('Q')):raise SystemExit(0)
def language_screen(s):
 langs=('es','en','zh');i=0
 while True:
  s.erase();h,w=s.getmaxyx();bw=min(70,w-4);x=max(1,(w-bw)//2);box(s,3,x,12,bw,'LEONES RC4');lang=langs[i];put(s,5,x+4,tr(lang,'language'),bw-8)
  for j,k in enumerate(langs):put(s,8+j,x+8,('>' if i==j else ' ')+f' {j+1}. {tr(lang,k)}',bw-16)
  put(s,12,x+4,tr(lang,'move')+' · ENTER',bw-8);s.refresh();k=s.getch()
  if k in (curses.KEY_UP,ord('k')):i=(i-1)%3
  elif k in (curses.KEY_DOWN,ord('j')):i=(i+1)%3
  elif k in (10,13,49,50,51):
   if k in (49,50,51):i=k-49
   return langs[i]
  elif k in (ord('q'),ord('Q')):raise SystemExit(0)
def catalog():
 try:return json.loads(CATALOG.read_text()).get('solutions',{})
 except Exception:return {}
def model_cost(m):
 r=m.get('raw') if isinstance(m.get('raw'),dict) else {}
 for k in ('size_bytes','disk_bytes','size','disk_size_bytes'):
  if isinstance(r.get(k),int) and r[k]>=0:return r[k]
 return None
def recommend(purposes):
 cmd=[sys.executable,str(RECOMMENDER),'--json']
 for p in purposes:cmd += ['--purpose',p]
 try:return json.loads(subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=90).stdout).get('recommendations') or []
 except Exception:return []
def solution_keys(sol):return ('personal_assistant','soho') if sol=='both' else (sol,)
def solution_info(sol,lang):
 c=catalog();ks=solution_keys(sol);desc=' '.join(tr(lang,k+'_desc') for k in ks);func=[]
 for k in ks:func += tr(lang,k+'_functions').split(';')
 return c,desc,func,' '.join(tr(lang,k+'_usage') for k in ks)
def agg(models,sel,sol):
 total=0
 for i in sel:
  v=model_cost(models[i])
  if v is None:return None
  total+=v
 for k in solution_keys(sol):
  v=catalog().get(k,{}).get('disk_bytes')
  if not isinstance(v,int):return None
  total+=v
 return total
def prov(v,lang):return tr(lang,'declared') if isinstance(v,int) else tr(lang,'unknown')
def resource(info,lang):
 cpu=info.get('cpu_load');cv=cpu if isinstance(cpu,(int,float)) else tr(lang,'unknown');cp=tr(lang,'estimated') if isinstance(cpu,(int,float)) else tr(lang,'unknown')
 return f"{tr(lang,'install')}: {tr(lang,'disk')}={hb(info.get('disk_bytes'),lang)} [{prov(info.get('disk_bytes'),lang)}] · {tr(lang,'ram')}={hb(info.get('ram_bytes'),lang)} [{prov(info.get('ram_bytes'),lang)}] · {tr(lang,'cpu')}={cv} [{cp}] · {tr(lang,'vram')}={hb(info.get('vram_bytes'),lang)} [{prov(info.get('vram_bytes'),lang)}]"
def draw(s,phase,purposes,models,sel,sol,cursor,navfocus,navidx,lang):
 s.erase();h,w=s.getmaxyx()
 if h<25 or w<92:put(s,1,2,'LEONES RC4 TUI · '+tr(lang,'unknown'),w-4);s.refresh();return
 title='LEONES // AI OPERATING SYSTEM v4';put(s,0,max(2,(w-len(title))//2),title,len(title));left=28;rx=left+3;rw=w-rx-2
 box(s,1,1,h-3,left,tr(lang,'nav'));nav=('LEONES RC4',tr(lang,'dashboard'),tr(lang,'machine'),tr(lang,'intent'),tr(lang,'recommender'),tr(lang,'evidence'),tr(lang,'settings'),tr(lang,'exit'))
 for i,n in enumerate(nav):put(s,3+i,4,('> ' if navfocus and navidx==i else '  ')+n,left-6)
 box(s,1,rx,5,rw,tr(lang,'system'));d=machine_data();x=rx+3;cw=rw-6
 if d['mem']:
  total,free,used=d['mem'];put(s,3,x,f"{tr(lang,'memory')}: {hb(total,lang)} {tr(lang,'total').lower()} · {hb(free,lang)} {tr(lang,'free').lower()} · {hb(used,lang)} {tr(lang,'used').lower()} [{tr(lang,'measured')}]")
 if d['cpu']:
  load,cores=d['cpu'];put(s,4,x,f"{tr(lang,'cpu')}: {load:.2f} {tr(lang,'load')} · {load*100/cores:.1f}% · {cores} {tr(lang,'logical')} [{tr(lang,'measured')}]")
 by=7;box(s,by,rx,h-by-3,rw,tr(lang,'workspace'));row=by+2;labels=(tr(lang,'purposes'),tr(lang,'models'),tr(lang,'solution'),tr(lang,'cost'),tr(lang,'confirm'));put(s,row,x,'  '.join(('>' if phase==i else ' ')+f'{i+1} {v}' for i,v in enumerate(labels)),cw);row+=2
 if phase==0:
  put(s,row,x,tr(lang,'purpose_prompt'),cw);row+=1
  for i,p in enumerate(PURPOSES):put(s,row+i,x,('>' if i==cursor and not navfocus else ' ')+f" [{'X' if p in purposes else ' '}] {tr(lang,p)}",cw)
 elif phase==1:
  put(s,row,x,tr(lang,'models_prompt'),cw);row+=1
  for i,m in enumerate(models):put(s,row+i,x,('>' if i==cursor and not navfocus else ' ')+f" [{'X' if i in sel else ' '}] {i+1:>2} {str(m.get('model_id','?'))[:42]} · {tr(lang,'disk')}={hb(model_cost(m),lang)} [{prov(model_cost(m),lang)}]",cw)
 elif phase==2:
  c,desc,func,usage=solution_info(sol,lang);put(s,row,x,tr(lang,'solution_prompt'),cw);row+=1
  for k in SOLUTIONS:put(s,row,x,('> ' if k==sol else '  ')+tr(lang,k),cw);row+=1
  put(s,row,x,desc,cw);row+=2;put(s,row,x,tr(lang,'functions')+':',cw);row+=1
  for f in func:put(s,row,x,'· '+f,cw);row+=1
  put(s,row,x,tr(lang,'usage')+': '+usage,cw);row+=2
  for k in solution_keys(sol):put(s,row,x,resource(c.get(k,{}),lang),cw);row+=1
 elif phase==3:
  req=agg(models,sel,sol);free=shutil.disk_usage(ROOT).free;status=tr(lang,'unknown') if req is None else (tr(lang,'sufficient') if free>=req else tr(lang,'insufficient'));put(s,row,x,tr(lang,'cost'),cw);row+=2
  for i in sorted(sel):v=model_cost(models[i]);put(s,row,x,f"{models[i].get('model_id','?')}: {hb(v,lang)} [{prov(v,lang)}]",cw);row+=1
  put(s,row,x,f"{tr(lang,'required')}: {hb(req,lang)} · {tr(lang,'free')}: {hb(free,lang)} [{tr(lang,'measured')}] · {status} [{tr(lang,'gate')}]")
 elif phase==4:
  put(s,row,x,tr(lang,'confirm'),cw);row+=2;put(s,row,x,tr(lang,'models_count',n=len(sel)),cw);row+=1;put(s,row,x,f"{tr(lang,'solution')}: {tr(lang,sol)}",cw);row+=2;put(s,row,x,tr(lang,'consent')+' · '+tr(lang,'no_install'),cw)
 put(s,h-2,3,f"{tr(lang,'tab')} · {tr(lang,'move')} · {tr(lang,'enter')} · {tr(lang,'back')} · {tr(lang,'quit')}",w-6);s.refresh()
def main():
 def app(s):
  curses.curs_set(0);s.keypad(True);lang=language_screen(s);machine_screen(s,lang);phase=0;purposes=[];models=[];sel=set();sol='personal_assistant';cursor=0;navfocus=False;navidx=0
  while True:
   draw(s,phase,purposes,models,sel,sol,cursor,navfocus,navidx,lang);k=s.getch()
   if k in (ord('q'),ord('Q')):return
   if k==9:navfocus=not navfocus;continue
   if navfocus:
    if k in (curses.KEY_UP,ord('k')):navidx=(navidx-1)%8
    elif k in (curses.KEY_DOWN,ord('j')):navidx=(navidx+1)%8
    elif k in (10,13):
     if navidx==7:return
     if navidx==2:machine_screen(s,lang)
     navfocus=False
    continue
   if phase==0:
    if k in (curses.KEY_UP,ord('k')):cursor=(cursor-1)%len(PURPOSES)
    elif k in (curses.KEY_DOWN,ord('j')):cursor=(cursor+1)%len(PURPOSES)
    elif k==ord(' '):p=PURPOSES[cursor];purposes.remove(p) if p in purposes else purposes.append(p)
    elif k in (10,13) and purposes:models=recommend(purposes);sel=set();cursor=0;phase=1
   elif phase==1:
    if models and k in (curses.KEY_UP,ord('k')):cursor=(cursor-1)%len(models)
    elif models and k in (curses.KEY_DOWN,ord('j')):cursor=(cursor+1)%len(models)
    elif models and k==ord(' '):sel.remove(cursor) if cursor in sel else sel.add(cursor)
    elif k in (10,13) and sel:phase=2;cursor=0
    elif k in (ord('r'),ord('R')):models=recommend(purposes);sel=set();cursor=0
    elif k in (ord('b'),ord('B')):phase=0;cursor=0
   elif phase==2:
    if k in (curses.KEY_UP,ord('k'),curses.KEY_DOWN,ord('j')):i=SOLUTIONS.index(sol);sol=SOLUTIONS[(i+(1 if k in (curses.KEY_DOWN,ord('j')) else -1))%3]
    elif k in (10,13):phase=3
    elif k in (ord('b'),ord('B')):phase=1
   elif phase==3:
    if k in (ord('b'),ord('B')):phase=2
    elif k in (10,13):phase=4
   elif k in (ord('b'),ord('B')):phase=3
 curses.wrapper(app)
if __name__=='__main__':raise SystemExit(main())
