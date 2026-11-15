#!/usr/bin/env python3
"""NEPENTHES portable Linux process/GPU capture CLI; Python 3.10+, stdlib only."""
from __future__ import annotations
import argparse,csv,datetime as dt,html,json,os,platform,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
VERSION="0.1.0"
PROFILES={"smoke":2.0,"standard":1.0,"full":0.5}
def stamp(): return dt.datetime.now(dt.timezone.utc).isoformat()
def save(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def proc_info(pid):
 try:
  raw=(Path("/proc")/str(pid)/"stat").read_text();t=raw[raw.rfind(")")+2:].split()
  ppid=int(t[1]);ticks=int(t[11])+int(t[12])
  rss=int((Path("/proc")/str(pid)/"statm").read_text().split()[1])*os.sysconf("SC_PAGE_SIZE")
  return ppid,ticks,rss
 except (OSError,ValueError,IndexError):return None
def proc_tree(root_pid):
 infos={}
 try:entries=list(Path("/proc").iterdir())
 except OSError:return None
 for entry in entries:
  if entry.name.isdigit():
   info=proc_info(int(entry.name))
   if info:infos[int(entry.name)]=info
 if root_pid not in infos:return None
 children={}
 for pid,(ppid,_,_) in infos.items():children.setdefault(ppid,[]).append(pid)
 pending=[root_pid];seen=set();ticks=rss=count=0
 while pending:
  pid=pending.pop()
  if pid in seen or pid not in infos:continue
  seen.add(pid);_,cpu,mem=infos[pid];ticks+=cpu;rss+=mem;count+=1
  pending.extend(children.get(pid,[]))
 return ticks,round(rss/1048576,3),count
def gpu():
 exe=shutil.which("nvidia-smi")
 if not exe:return None
 try:
  p=subprocess.run([exe,"--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=3)
  if p.returncode:return None
  row=p.stdout.splitlines()[0].split(",")
  def n(x):
   try:return int(x.strip())
   except ValueError:return None
  return dict(zip(("gpu_utilization_percent","gpu_memory_used_mib","gpu_memory_total_mib","gpu_temperature_c"),map(n,row)))
 except (OSError,subprocess.TimeoutExpired,IndexError):return None
def emit(f,k,run_id,**v):
 timestamp=int(v.pop("timestamp_unix_ns",time.time_ns()))
 rss=v.get("process_rss_mib")
 cpu=v.get("process_cpu_percent")
 event={"schema_version":"1.0","run_id":run_id,"event_id":uuid.uuid4().hex,
  "source":"nepenthes-host","timestamp_unix_ns":timestamp,"monotonic_ns":time.monotonic_ns(),
  "request_id":0,"event_kind":k,"label":str(v.pop("label",k)),
  "value0":int(v.pop("value0",float(rss)*1048576 if rss is not None else 0)),
  "value1":int(v.pop("value1",float(cpu)*100 if cpu is not None else 0)),
  "duration_ns":int(v.pop("duration_ns",0)),"flags":int(v.pop("flags",0))}
 event.update(v)
 f.write(json.dumps(event,separators=(",",":"))+"\n");f.flush()
def chart(title,values):
 if not values:return f"<h3>{html.escape(title)}</h3><p>Sin muestras.</p>"
 w,h=900,220;lo,hi=min(values),max(values);span=max(hi-lo,1.0);pts=[]
 for i,v in enumerate(values):
  x=36+(w-72)*i/max(len(values)-1,1);y=h-30-(h-65)*(v-lo)/span;pts.append(f"{x:.1f},{y:.1f}")
 return f"<h3>{html.escape(title)}</h3><svg viewBox='0 0 {w} {h}'><polyline points='{' '.join(pts)}' fill='none' stroke='#2878c8' stroke-width='2.5'/><text x='36' y='18'>{hi:.2f}</text><text x='36' y='{h-8}'>{lo:.2f}</text></svg>"
def make_report(root,m,samples):
 data=root/"data";reports=root/"reports";data.mkdir(exist_ok=True);reports.mkdir(exist_ok=True)
 cols=["elapsed_seconds","process_cpu_percent","process_rss_mib","process_count","gpu_utilization_percent","gpu_memory_used_mib","gpu_temperature_c"]
 with (data/"samples.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
  for s in samples:w.writerow({k:s.get(k) for k in cols})
 limits=["CPU/RSS se agregan sobre el árbol de procesos descendientes observado mediante /proc; los procesos que se desacoplan o salen de ese árbol pueden no contabilizarse.","GPU es telemetría global, no atribuida al proceso.","Nsight/CUPTI y sondas internas aún no se capturan.","No se infiere correlación request-kernel ni entre relojes."]
 summary={"run_id":m["run_id"],"exit_code":m["exit_code"],"duration_seconds":m["duration_seconds"],"sample_count":len(samples),
 "process_cpu_percent_max":max((s["process_cpu_percent"] for s in samples if s.get("process_cpu_percent") is not None),default=None),
 "process_rss_mib_max":max((s["process_rss_mib"] for s in samples if s.get("process_rss_mib") is not None),default=None),
 "gpu_samples_available":sum(s.get("gpu_utilization_percent") is not None for s in samples),"event_count":m.get("event_merge",{}).get("total",0),"event_sources":m.get("event_merge",{}).get("counts",{}),"process_count_max":max((s.get("process_count",0) for s in samples),default=0),"limitations":limits}
 save(data/"summary.json",summary)
 with __import__("sqlite3").connect(data/"observations.sqlite") as db:
  db.executescript("""CREATE TABLE samples(sample_id INTEGER PRIMARY KEY,elapsed_seconds REAL,timestamp_unix_ns INTEGER,process_cpu_percent REAL,process_rss_mib REAL,gpu_utilization_percent REAL,gpu_memory_used_mib REAL,gpu_memory_total_mib REAL,gpu_temperature_c REAL);
  CREATE TABLE events(event_id INTEGER PRIMARY KEY,timestamp_unix_ns INTEGER,monotonic_ns INTEGER,event_kind TEXT NOT NULL,payload_json TEXT NOT NULL);""")
  for n,s in enumerate(samples,1):
   db.execute("INSERT INTO samples VALUES(?,?,?,?,?,?,?,?,?)",(n,s.get("elapsed_seconds"),s.get("timestamp_unix_ns"),s.get("process_cpu_percent"),s.get("process_rss_mib"),s.get("gpu_utilization_percent"),s.get("gpu_memory_used_mib"),s.get("gpu_memory_total_mib"),s.get("gpu_temperature_c")))
  with (root/"raw"/"events.jsonl").open(encoding="utf-8") as stream:
   for n,line in enumerate(stream,1):
    event=json.loads(line)
    db.execute("INSERT INTO events VALUES(?,?,?,?,?)",(n,event.get("timestamp_unix_ns"),event.get("monotonic_ns"),event.get("event_kind"),json.dumps(event,separators=(",",":"))))
 def vals(k):return [float(s[k]) for s in samples if s.get(k) is not None]
 plots="".join([chart("CPU del árbol de procesos (%)",vals("process_cpu_percent")),chart("RSS del árbol de procesos (MiB)",vals("process_rss_mib")),chart("Utilización GPU global (%)",vals("gpu_utilization_percent")),chart("Memoria GPU global (MiB)",vals("gpu_memory_used_mib"))])
 items="".join("<li>"+html.escape(x)+"</li>" for x in limits)
 import_links='<li><a href="../data/nepenthes-import.sqlite">nepenthes-import.sqlite</a></li>' if (data/"nepenthes-import.sqlite").is_file() else ""
 nsys_links="".join('<li><a href="../'+html.escape(x)+'">'+html.escape(x)+'</a></li>' for x in m.get("nsys",{}).get("outputs",[]))
 raw_links="".join('<li><a href="../raw/'+name+'">'+name+'</a></li>' for name in ("host-events.jsonl","engine-events.jsonl") if (root/"raw"/name).is_file())
 metrics=[("Muestras",summary["sample_count"]),("CPU máximo (%)",summary["process_cpu_percent_max"]),("RSS máximo (MiB)",summary["process_rss_mib_max"]),("Procesos observados",summary["process_count_max"]),("Eventos",summary["event_count"]),("Muestras GPU",summary["gpu_samples_available"])]
 table="".join("<tr><th>"+html.escape(str(k))+"</th><td>"+html.escape(str(v if v is not None else "no disponible"))+"</td></tr>" for k,v in metrics)
 page=f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>NEPENTHES</title>
<style>body{{font:15px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}}section,header{{padding:1rem;border:1px solid #ddd;border-radius:10px;margin:1rem 0}}svg{{width:100%;background:#f7f9fb}}pre{{white-space:pre-wrap}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.5rem;border-bottom:1px solid #ddd;text-align:left}}</style>
<header><h1>Informe NEPENTHES</h1><p>{html.escape(m['run_id'])} · {m['profile']} · exit {m['exit_code']} · {m['duration_seconds']:.2f}s · {len(samples)} muestras</p></header>
<section><h2>Resumen cuantitativo</h2><table>{table}</table></section>
<section><h2>Actividad observada</h2>{plots}</section><section><h2>Comando</h2><pre>{html.escape(json.dumps(m['command'],ensure_ascii=False))}</pre></section>
<section><h2>Límites</h2><ul>{items}</ul></section><section><h2>Ficheros</h2><ul><li><a href="../manifest.json">manifest.json</a></li><li><a href="../raw/events.jsonl">events.jsonl</a></li>{raw_links}<li><a href="../data/samples.csv">samples.csv</a></li><li><a href="../data/observations.sqlite">observations.sqlite</a></li><li><a href="../data/summary.json">summary.json</a></li><li><a href="../data/nsys-import.json">nsys-import.json</a></li>{import_links}{nsys_links}<li><a href="../session.log">session.log</a></li><li><a href="../checksums.sha256">checksums.sha256</a></li></ul></section></html>"""
 (reports/"index.html").write_text(page,encoding="utf-8")
 (reports/"report.md").write_text("# Informe NEPENTHES\n\n- Run: "+m["run_id"]+"\n- Perfil: "+m["profile"]+"\n- Exit: "+str(m["exit_code"])+"\n- Duración: "+str(m["duration_seconds"])+"s\n- Muestras: "+str(len(samples))+"\n",encoding="utf-8")
 import hashlib
 lines=[]
 for file in sorted(root.rglob("*")):
  if file.is_file() and file.name!="checksums.sha256":
   digest=hashlib.sha256(file.read_bytes()).hexdigest()
   lines.append(digest+"  "+str(file.relative_to(root)))
 (root/"checksums.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8")
def nsys_command(executable,output_prefix,command):
 return [executable,"profile","--trace=cuda,nvtx,osrt","--sample=none","--cpuctxsw=none",
         "--export=sqlite","--force-overwrite=true","--kill=none",f"--output={output_prefix}",*command]
def merge_event_files(root,run_id):
 raw=root/"raw";combined=raw/"events.jsonl";counts={};warnings=[]
 with combined.open("w",encoding="utf-8") as out:
  for name in ("host-events.jsonl","engine-events.jsonl"):
   source=raw/name;count=0
   if source.is_file():
    with source.open(encoding="utf-8") as stream:
     for line_no,line in enumerate(stream,1):
      if not line.strip():continue
      try:
       event=json.loads(line)
       if event.get("run_id")!=run_id:warnings.append(name+":"+str(line_no)+":run_id_mismatch")
       if event.get("schema_version")!="1.0":warnings.append(name+":"+str(line_no)+":schema_version_mismatch")
       if name=="engine-events.jsonl":
        event["source_event_id"]=event.get("event_id")
        event["event_id"]="engine-"+str(line_no)+"-"+str(event.get("event_id","unknown"))
        line=json.dumps(event,separators=(",",":"))+"\n"
      except json.JSONDecodeError as exc:
       warnings.append(name+":"+str(line_no)+":invalid_json:"+str(exc))
       continue
      if event.get("run_id")!=run_id or event.get("schema_version")!="1.0":
       continue
      out.write(line if line.endswith("\n") else line+"\n");count+=1
   counts[name]=count
 return {"counts":counts,"total":sum(counts.values()),"warnings":warnings}
def stop_process_group(child, pgid):
 try:
  os.killpg(pgid,signal.SIGINT)
 except ProcessLookupError:
  pass
 try:
  child.wait(timeout=10)
 except subprocess.TimeoutExpired:
  try:os.killpg(pgid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:child.wait(timeout=3)
  except subprocess.TimeoutExpired:
   try:os.killpg(pgid,signal.SIGKILL)
   except ProcessLookupError:pass
   child.wait()
 # The wrapper may exit while descendants remain in its session.
 try:os.killpg(pgid,0)
 except ProcessLookupError:
  return
 try:os.killpg(pgid,signal.SIGTERM)
 except ProcessLookupError:
  return
 time.sleep(0.2)
 try:os.killpg(pgid,0)
 except ProcessLookupError:
  return
 try:os.killpg(pgid,signal.SIGKILL)
 except ProcessLookupError:
  pass
def import_nsys_bundle(root,m):
 meta=m.get("nsys",{})
 merge_warnings=m.get("event_merge",{}).get("warnings",[])
 if merge_warnings:
  result={"status":"blocked","reason":"event stream contains invalid or mismatched records","warnings":merge_warnings}
  save(root/"data"/"nsys-import.json",result)
  return result
 sqlite_rel=meta.get("sqlite")
 if not sqlite_rel:
  result={"status":"not_available","reason":"Nsight SQLite export not found"}
  save(root/"data"/"nsys-import.json",result)
  return result
 sqlite_path=root/sqlite_rel
 data_home=Path(os.environ.get("NEPENTHES_DATA_DIR",str(Path.home()/".local"/"share"/"nepenthes"))).expanduser()
 candidates=[Path(__file__).resolve().with_name("nepenthes_nsys_import.py"),data_home/"scripts"/"nepenthes_nsys_import.py"]
 importer=next((p for p in candidates if p.is_file()),None)
 if importer is None:
  result={"status":"unavailable","reason":"LEONES Nsight importer not installed"}
  save(root/"data"/"nsys-import.json",result)
  return result
 output=root/"data"/"nepenthes-import.sqlite"
 try:
  p=subprocess.run([sys.executable,str(importer),"--jsonl",str(root/"raw"/"events.jsonl"),
   "--nsys-sqlite",str(sqlite_path),"--output",str(output)],capture_output=True,text=True,timeout=600,check=False)
  result={"status":"imported" if p.returncode==0 else "failed","returncode":p.returncode,
   "importer":str(importer),"output":str(output) if p.returncode==0 else None,
   "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:]}
 except (OSError,subprocess.TimeoutExpired) as exc:
  result={"status":"failed","reason":str(exc),"importer":str(importer)}
 save(root/"data"/"nsys-import.json",result)
 return result
def run(a):
 cmd=list(a.command)
 if cmd and cmd[0]=="--":cmd=cmd[1:]
 if not cmd:raise ValueError("uso: nepenthes run -- COMANDO [ARG ...]")
 if shutil.which(cmd[0]) is None and not Path(cmd[0]).exists():raise ValueError("ejecutable no encontrado: "+cmd[0])
 nsys_exe=shutil.which("nsys")
 nsys_enabled=(a.nsys=="required" or (a.nsys=="auto" and a.profile=="full")) and bool(nsys_exe)
 if a.nsys=="required" and not nsys_exe:raise ValueError("nsys es obligatorio pero no está instalado o no está en PATH")
 launch=cmd
 rid=dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")+"_"+(a.name or Path(cmd[0]).name)+"_"+uuid.uuid4().hex[:8]
 root=Path(a.output).expanduser().resolve()/rid
 for d in ("raw","data","reports","environment"):(root/d).mkdir(parents=True,exist_ok=True)
 interval=a.interval or PROFILES[a.profile]
 m={"schema_version":"nepenthes-run-0.1","run_id":rid,"created_at":stamp(),"profile":a.profile,"sample_interval_seconds":interval,"command":cmd,"working_directory":os.getcwd(),"host":platform.node(),"status":"running","capabilities":{"procfs":Path("/proc").is_dir(),"nvidia_smi":bool(shutil.which("nvidia-smi")),"nsys_detected":bool(nsys_exe),"nsys_capture_enabled":nsys_enabled},"nsys":{"requested":a.nsys,"enabled":nsys_enabled,"executable":nsys_exe if nsys_enabled else None}}
 m["engine_probe_activation"]={"environment_variables_set":True,"run_id_variable":"NEPENTHES_RUN_ID","jsonl_variable":"NEPENTHES_TRACE_JSONL","jsonl_path":"raw/engine-events.jsonl"}
 save(root/"manifest.json",m);save(root/"environment"/"system.json",{"platform":platform.platform(),"python":sys.version,"cpu_count":os.cpu_count(),"nvidia_smi":shutil.which("nvidia-smi"),"nsys":shutil.which("nsys")});save(root/"environment"/"gpu-initial.json",gpu() or {"available":False})
 samples=[];ticks=os.sysconf("SC_CLK_TCK");pt=ptime=None;start=time.monotonic();code=127
 try:
  with (root/"session.log").open("w",encoding="utf-8") as log,(root/"raw"/"host-events.jsonl").open("w",encoding="utf-8") as ev:
   emit(ev,"capture_started",run_id=rid,command=cmd,profile=a.profile);log.write("$ "+" ".join(cmd)+"\n\n");log.flush()
   if nsys_enabled:launch=nsys_command(nsys_exe,str(root/"raw"/"nsys"),cmd)
   child_env=os.environ.copy();child_env["NEPENTHES_RUN_ID"]=rid;child_env["NEPENTHES_TRACE_JSONL"]=str(root/"raw"/"engine-events.jsonl")
   child=subprocess.Popen(launch,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=child_env);child_pgid=child.pid;m["pid"]=child.pid;m["process_group_id"]=child_pgid;m["launch_command"]=launch;save(root/"manifest.json",m)
   while True:
    now=time.monotonic();s={"elapsed_seconds":round(now-start,4),"timestamp_unix_ns":time.time_ns()};p=proc_tree(child.pid)
    if p:
     s["process_rss_mib"]=p[1];s["process_count"]=p[2]
     if pt is not None and ptime is not None:s["process_cpu_percent"]=round(max(p[0]-pt,0)/ticks/max(now-ptime,1e-6)*100,2)
     pt,ptime=p[0],now
    g=gpu()
    if g:s.update(g)
    samples.append(s);emit(ev,"sample",run_id=rid,**s)
    if child.poll() is not None:break
    time.sleep(interval)
   code=child.returncode
   if nsys_enabled:
    outputs=[str(x.relative_to(root)) for x in sorted((root/"raw").glob("nsys*")) if x.is_file()]
    m["nsys"]["outputs"]=outputs
    m["nsys"]["sqlite"]=next((x for x in outputs if x.endswith(".sqlite")),None)
   emit(ev,"capture_finished",run_id=rid,exit_code=code,duration_ns=int((time.monotonic()-start)*1e9))
 except KeyboardInterrupt:
  if "child" in locals() and child.poll() is None:
   stop_process_group(child,locals().get("child_pgid",child.pid))
  code=child.returncode if "child" in locals() else 130;m["interrupted"]=True
 except OSError as e:m["collector_error"]=str(e)
 m["event_merge"]=merge_event_files(root,rid)
 if nsys_enabled:m["nsys"]["import"]=import_nsys_bundle(root,m)
 else:
  m["nsys"]["import"]={"status":"not_requested"}
  save(root/"data"/"nsys-import.json",m["nsys"]["import"])
 m.update({"finished_at":stamp(),"duration_seconds":round(time.monotonic()-start,4),"exit_code":code,"status":"completed" if code==0 else "command_failed","sample_count":len(samples)})
 save(root/"manifest.json",m);make_report(root,m,samples)
 print("NEPENTHES run: "+str(root));print("Report: "+str(root/"reports"/"index.html"));print("Exit code: "+str(code));return code
def doctor(_):
 print(json.dumps({"version":VERSION,"platform":platform.platform(),"python":sys.version,"procfs":Path("/proc").is_dir(),"nvidia_smi":shutil.which("nvidia-smi") or "optional/not found","nsys":shutil.which("nsys") or "optional/not found; adapter pending","default_output":str(Path.home()/"NEPENTHES-runs")},indent=2));return 0
def inspect(a):
 p=Path(a.path).expanduser().resolve();f=p/"manifest.json" if p.is_dir() else p
 if not f.is_file():raise ValueError("manifest no encontrado: "+str(f))
 print(json.dumps(json.loads(f.read_text()),indent=2));return 0
def verify_run(a):
 run=Path(a.path).expanduser().resolve();manifest_path=run/"manifest.json"
 result={"run":str(run),"checks":{},"errors":[]}
 if not manifest_path.is_file():raise ValueError("manifest no encontrado: "+str(manifest_path))
 manifest=json.loads(manifest_path.read_text(encoding="utf-8"));run_id=manifest.get("run_id")
 checksums=run/"checksums.sha256";listed=set()
 if not checksums.is_file():result["errors"].append("checksums.sha256 missing")
 else:
  for line in checksums.read_text(encoding="utf-8").splitlines():
   if not line.strip():continue
   parts=line.split("  ",1)
   if len(parts)!=2:result["errors"].append("invalid checksum line");continue
   expected,relative=parts
   target=(run/relative).resolve()
   if run not in target.parents and target!=run:result["errors"].append("checksum path escapes run directory: "+relative);continue
   listed.add(relative)
   if not target.is_file():result["errors"].append("missing file: "+relative);continue
   actual=__import__("hashlib").sha256(target.read_bytes()).hexdigest()
   if actual!=expected:result["errors"].append("checksum mismatch: "+relative)
  actual_files={str(p.relative_to(run)) for p in run.rglob("*") if p.is_file() and p.name!="checksums.sha256"}
  for missing in sorted(actual_files-listed):result["errors"].append("unhashed file: "+missing)
  for missing in sorted(listed-actual_files):result["errors"].append("checksum references missing file: "+missing)
 result["checks"]["checksums"]=not any(x.startswith(("checksum","missing file","unhashed file")) for x in result["errors"])
 events_path=run/"raw"/"events.jsonl";seen=set();count=0
 required={"schema_version","run_id","event_id","source","timestamp_unix_ns","monotonic_ns","request_id","event_kind","label","value0","value1","duration_ns","flags"}
 if not events_path.is_file():result["errors"].append("raw/events.jsonl missing")
 else:
  try:
   for line_no,line in enumerate(events_path.read_text(encoding="utf-8").splitlines(),1):
    event=json.loads(line);count+=1
    if not required.issubset(event):result["errors"].append("event schema missing fields at line "+str(line_no))
    if event.get("schema_version")!="1.0":result["errors"].append("event schema version mismatch at line "+str(line_no))
    if event.get("run_id")!=run_id:result["errors"].append("event run_id mismatch at line "+str(line_no))
    if event.get("event_id") in seen:result["errors"].append("duplicate event_id at line "+str(line_no))
    seen.add(event.get("event_id"))
  except (OSError,json.JSONDecodeError) as exc:result["errors"].append("event JSONL invalid: "+str(exc))
 if count==0:result["errors"].append("raw/events.jsonl empty")
 result["checks"]["events_valid"]=events_path.is_file() and count>0 and not any("event " in x or "duplicate event_id" in x for x in result["errors"])
 result["event_count"]=count
 import sqlite3
 for name in ("observations.sqlite","nepenthes-import.sqlite"):
  dbpath=run/"data"/name
  if not dbpath.is_file():
   if name=="observations.sqlite":result["errors"].append("data/observations.sqlite missing")
   continue
  try:
   with sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True) as db:
    status=db.execute("PRAGMA integrity_check").fetchone()[0]
    if status!="ok":result["errors"].append(name+" integrity check: "+str(status))
    if name=="observations.sqlite":
     tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
     if not {"samples","events"}.issubset(tables):result["errors"].append("observations.sqlite missing expected tables")
     result["sample_rows"]=db.execute("SELECT count(*) FROM samples").fetchone()[0]
     result["event_rows"]=db.execute("SELECT count(*) FROM events").fetchone()[0]
  except sqlite3.Error as exc:result["errors"].append(name+" unreadable: "+str(exc))
 result["checks"]["report_html"]=(run/"reports"/"index.html").is_file()
 if not result["checks"]["report_html"]:result["errors"].append("reports/index.html missing")
 result["ok"]=not result["errors"]
 print(json.dumps(result,indent=2,ensure_ascii=False))
 return 0 if result["ok"] else 1

def self_test(a):
 output=Path(a.output).expanduser().resolve()
 before={p.resolve() for p in output.iterdir()} if output.is_dir() else set()
 args=argparse.Namespace(command=[sys.executable,"-c","print('NEPENTHES_SELF_TEST_OK')"],
  profile="smoke",interval=0.1,output=str(output),name="self-test",nsys="off")
 code=run(args)
 if code!=0:return code
 after={p.resolve() for p in output.iterdir()} if output.is_dir() else set()
 created=after-before
 if not created:
  print("NEPENTHES self-test failed: run bundle was not created",file=sys.stderr);return 1
 target=max(created,key=lambda p:p.stat().st_mtime)
 print("Self-test bundle verification:")
 return verify_run(argparse.Namespace(path=str(target)))

def parser():
 p=argparse.ArgumentParser(prog="nepenthes");p.add_argument("--version",action="version",version="NEPENTHES "+VERSION);sub=p.add_subparsers(dest="action",required=True)
 d=sub.add_parser("doctor");d.set_defaults(func=doctor)
 r=sub.add_parser("run",aliases=["capture"]);r.add_argument("--profile",choices=sorted(PROFILES),default="standard");r.add_argument("--interval",type=float);r.add_argument("--nsys",choices=("auto","required","off"),default="auto",help="auto enables Nsight for full profile; required fails if unavailable; off disables it");r.add_argument("--output",default=str(Path.home()/"NEPENTHES-runs"));r.add_argument("--name");r.add_argument("command",nargs=argparse.REMAINDER);r.set_defaults(func=run)
 i=sub.add_parser("inspect");i.add_argument("path");i.set_defaults(func=inspect)
 v=sub.add_parser("verify");v.add_argument("path");v.set_defaults(func=verify_run)
 t=sub.add_parser("self-test",help="run a tiny synthetic capture and verify its bundle");t.add_argument("--output",default=str(Path.home()/"NEPENTHES-runs"));t.set_defaults(func=self_test);return p
def main(argv=None):
 p=parser();a=p.parse_args(argv)
 if getattr(a,"interval",None) is not None and a.interval<=0:p.error("--interval debe ser positivo")
 try:return a.func(a)
 except (OSError,ValueError,json.JSONDecodeError) as e:print("nepenthes: error: "+str(e),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
