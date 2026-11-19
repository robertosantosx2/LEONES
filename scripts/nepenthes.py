#!/usr/bin/env python3
"""NEPENTHES portable Linux process/GPU capture CLI; Python 3.10+, stdlib only."""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,html,json,os,platform,shlex,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
try:
 from nepenthes_privacy import redact_command
except ModuleNotFoundError:
 from scripts.nepenthes_privacy import redact_command
VERSION="0.2.0"
PROFILE_SETTINGS={
 "smoke":{"interval":2.0,"idle_interval":2.0,"host_sampling":True,"nsys_default":False,"probe_level":"minimal","adaptive_sampling":False},
 "standard":{"interval":1.0,"idle_interval":2.0,"host_sampling":True,"nsys_default":False,"probe_level":"standard","adaptive_sampling":True},
 "full":{"interval":0.5,"idle_interval":0.5,"host_sampling":True,"nsys_default":True,"probe_level":"full","adaptive_sampling":False},
 "moe-deep":{"interval":0.25,"idle_interval":1.0,"host_sampling":True,"nsys_default":True,"probe_level":"moe-deep","adaptive_sampling":True},
 "latency-critical":{"interval":0.0,"idle_interval":0.0,"host_sampling":False,"nsys_default":False,"probe_level":"request-only","adaptive_sampling":False},
}
PROFILES={name:settings["interval"] for name,settings in PROFILE_SETTINGS.items()}
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
      if event.get("run_id")!=run_id:
       warnings.append(name+":"+str(line_no)+":run_id_mismatch")
       continue
      if event.get("schema_version")!="1.0":
       warnings.append(name+":"+str(line_no)+":unsupported_schema_version")
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
 settings=PROFILE_SETTINGS[a.profile]
 nsys_exe=shutil.which("nsys")
 nsys_enabled=(a.nsys=="required" or (a.nsys=="auto" and settings["nsys_default"])) and bool(nsys_exe)
 if a.nsys=="required" and not nsys_exe:raise ValueError("nsys es obligatorio pero no está instalado o no está en PATH")
 launch=cmd
 redacted_cmd=redact_command(cmd)
 command_sha256=hashlib.sha256(json.dumps(redacted_cmd,separators=(",",":")).encode("utf-8")).hexdigest()
 rid=dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")+"_"+(a.name or Path(cmd[0]).name)+"_"+uuid.uuid4().hex[:8]
 root=Path(a.output).expanduser().resolve()/rid
 for d in ("raw","data","reports","environment"):(root/d).mkdir(parents=True,exist_ok=True)
 interval=a.interval if a.interval is not None else settings["interval"]
 host_sampling=bool(settings["host_sampling"] or a.interval is not None) and interval>0
 adaptive_enabled=bool(settings["adaptive_sampling"] and host_sampling)
 idle_interval=max(settings["idle_interval"],interval) if adaptive_enabled else interval
 m={"schema_version":"nepenthes-run-0.2","run_id":rid,"created_at":stamp(),"profile":a.profile,
    "profile_settings":settings,"sample_interval_seconds":interval if host_sampling else None,
    "host_sampling_enabled":host_sampling,"command":redacted_cmd,"command_sha256":command_sha256,
    "working_directory_basename":Path.cwd().name,"host_id_sha256":hashlib.sha256(platform.node().encode("utf-8")).hexdigest(),
    "status":"running","capabilities":{"procfs":Path("/proc").is_dir(),"nvidia_smi":bool(shutil.which("nvidia-smi")),"nsys_detected":bool(nsys_exe),"nsys_capture_enabled":nsys_enabled},
    "nsys":{"requested":a.nsys,"enabled":nsys_enabled,"executable":nsys_exe if nsys_enabled else None},
    "adaptive_sampling":{"enabled":adaptive_enabled,"trigger":"request_start/request_end in raw/engine-events.jsonl",
                         "active_interval_seconds":interval,"idle_interval_seconds":idle_interval,"transitions":[]}}
 m["engine_probe_activation"]={"environment_variables_set":True,"run_id_variable":"NEPENTHES_RUN_ID",
   "jsonl_variable":"NEPENTHES_TRACE_JSONL","jsonl_path":"raw/engine-events.jsonl",
   "profile_variable":"NEPENTHES_PROFILE","probe_level":settings["probe_level"],
   "adaptive_sampling_variable":"NEPENTHES_ADAPTIVE_SAMPLING"}
 save(root/"manifest.json",m);save(root/"environment"/"system.json",{"platform":platform.platform(),"python":sys.version,"cpu_count":os.cpu_count(),"nvidia_smi":shutil.which("nvidia-smi"),"nsys":shutil.which("nsys")});save(root/"environment"/"gpu-initial.json",gpu() or {"available":False})
 samples=[];ticks=os.sysconf("SC_CLK_TCK");pt=ptime=None;start=time.monotonic();code=127
 try:
  with (root/"session.log").open("w",encoding="utf-8") as log,(root/"raw"/"host-events.jsonl").open("w",encoding="utf-8") as ev:
   emit(ev,"capture_started",run_id=rid,command=redacted_cmd,profile=a.profile)
   log.write("$ "+shlex.join(redacted_cmd)+"\n")
   if a.capture_output:log.write("Output capture explicitly enabled.\n\n")
   else:log.write("Child output suppressed by default; use --capture-output to persist it.\n\n")
   log.flush()
   if nsys_enabled:launch=nsys_command(nsys_exe,str(root/"raw"/"nsys"),cmd)
   child_env=os.environ.copy();child_env["NEPENTHES_RUN_ID"]=rid;child_env["NEPENTHES_TRACE_JSONL"]=str(root/"raw"/"engine-events.jsonl")
   child_env["NEPENTHES_PROFILE"]=a.profile;child_env["NEPENTHES_PROBE_LEVEL"]=settings["probe_level"]
   child_env["NEPENTHES_ADAPTIVE_SAMPLING"]="1" if adaptive_enabled else "0"
   child=subprocess.Popen(launch,stdout=log if a.capture_output else subprocess.DEVNULL,stderr=subprocess.STDOUT,start_new_session=True,env=child_env)
   child_pgid=child.pid;m["pid"]=child.pid;m["process_group_id"]=child_pgid;m["launch_command"]=redact_command(launch);save(root/"manifest.json",m)
   adaptive_path=root/"raw"/"engine-events.jsonl";event_offset=0;pending=b"";active_requests=set()
   adaptive_state="idle";transitions=[];sample_counts={"active":0,"idle":0};next_sample=0.0
   if not host_sampling:
    code=child.wait()
   else:
    while True:
     now=time.monotonic()
     if adaptive_enabled:
      try:
       with adaptive_path.open("rb") as event_stream:
        event_stream.seek(event_offset);chunk=event_stream.read();event_offset=event_stream.tell()
      except OSError:chunk=b""
      pending+=chunk;lines=pending.split(b"\n");pending=lines.pop() if lines else b""
      for raw_line in lines:
       if not raw_line.strip():continue
       try:event=json.loads(raw_line)
       except json.JSONDecodeError:continue
       kind=event.get("event_kind");token=event.get("correlation_token",event.get("request_id",event.get("event_id")))
       if token is None:continue
       token=str(token)
       if kind=="request_start":active_requests.add(token)
       elif kind=="request_end":active_requests.discard(token)
      state="active" if active_requests else "idle"
      if state!=adaptive_state:
       adaptive_state=state
       transitions.append({"elapsed_seconds":round(now-start,4),"state":state,"active_request_count":len(active_requests)})
       next_sample=now
      current_interval=interval if state=="active" else idle_interval
     else:
      state="idle";current_interval=interval
     if now>=next_sample:
      sample={"elapsed_seconds":round(now-start,4),"timestamp_unix_ns":time.time_ns()}
      pinfo=proc_tree(child.pid)
      if pinfo:
       sample["process_rss_mib"]=pinfo[1];sample["process_count"]=pinfo[2]
       if pt is not None and ptime is not None:sample["process_cpu_percent"]=round(max(pinfo[0]-pt,0)/ticks/max(now-ptime,1e-6)*100,2)
       pt,ptime=pinfo[0],now
      gpu_sample=gpu()
      if gpu_sample:sample.update(gpu_sample)
      if adaptive_enabled:
       sample["adaptive_state"]=state;sample["active_request_count"]=len(active_requests);sample_counts[state]+=1
      samples.append(sample);emit(ev,"sample",run_id=rid,**sample)
      next_sample=now+current_interval
     if child.poll() is not None:break
     sleep_for=min(0.05,max(0.01,next_sample-time.monotonic())) if adaptive_enabled else max(0.01,min(interval,next_sample-time.monotonic()))
     time.sleep(sleep_for)
    code=child.returncode
   m["adaptive_sampling"]["transitions"]=transitions
   m["adaptive_sampling"]["sample_counts"]=sample_counts

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
def validate_event_contract(events):
 errors=[]
 request_starts={};request_ends={};nvtx_starts={};nvtx_ends={};clock_points=[];clock_labels={}
 allowed={"exact","windowed","device_wide","estimated"}
 for line_no,event in enumerate(events,1):
  token=event.get("correlation_token")
  level=event.get("attribution_level")
  kind=event.get("event_kind")
  if level is not None and level not in allowed:
   errors.append("invalid attribution_level at event "+str(line_no))
  if token is not None:
   if isinstance(token,bool) or not isinstance(token,int) or not 0<token<=0xffffffffffffffff:
    errors.append("invalid correlation_token at event "+str(line_no));token=None
   elif level!="exact":
    errors.append("correlation_token requires exact attribution at event "+str(line_no))
  elif level=="exact":
   errors.append("exact attribution requires correlation_token at event "+str(line_no))
  clock_domain=event.get("clock_domain")
  if clock_domain is not None and clock_domain!="steady_clock":
   errors.append("unsupported clock_domain at event "+str(line_no))
  if kind in ("request_start","request_end") and token is not None:
   target=request_starts if kind=="request_start" else request_ends
   target[token]=target.get(token,0)+1
  if kind=="clock_calibration":
   mono=event.get("monotonic_ns");wall=event.get("timestamp_unix_ns")
   if not isinstance(mono,int) or isinstance(mono,bool) or mono<=0 or not isinstance(wall,int) or isinstance(wall,bool) or wall<=0:
    errors.append("invalid clock_calibration timestamp at event "+str(line_no))
   else:
    label=event.get("label")
    clock_labels[label]=clock_labels.get(label,0)+1
    clock_points.append((mono,wall,label))
  if kind=="nvtx_marker":
   if token is None or level!="exact":
    errors.append("NVTX marker requires exact correlation token at event "+str(line_no))
   label=event.get("label")
   phase="start" if label=="request.start" else "end" if label=="request.end" else None
   before=event.get("value0");after=event.get("value1")
   if phase is None:
    errors.append("invalid NVTX marker phase at event "+str(line_no))
   elif not isinstance(before,int) or isinstance(before,bool) or not isinstance(after,int) or isinstance(after,bool) or after<before:
    errors.append("invalid NVTX marker host bracket at event "+str(line_no))
   elif token is not None:
    target=nvtx_starts if phase=="start" else nvtx_ends
    target[token]=target.get(token,0)+1
   if not isinstance(event.get("timestamp_unix_ns"),int) or event.get("timestamp_unix_ns",0)<=0:
    errors.append("NVTX marker requires source wall timestamp at event "+str(line_no))
   if clock_domain!="steady_clock":
    errors.append("NVTX marker requires steady_clock at event "+str(line_no))
 unmatched_request_starts=sum(max(0,n-request_ends.get(token,0)) for token,n in request_starts.items())
 unmatched_request_ends=sum(max(0,n-request_starts.get(token,0)) for token,n in request_ends.items())
 unmatched_nvtx_starts=sum(max(0,n-nvtx_ends.get(token,0)) for token,n in nvtx_starts.items())
 unmatched_nvtx_ends=sum(max(0,n-nvtx_starts.get(token,0)) for token,n in nvtx_ends.items())
 for token in set(request_starts)|set(request_ends):
  if request_starts.get(token,0)!=1 or request_ends.get(token,0)!=1:
   errors.append("request token lifecycle is not one start/one end: "+str(token))
 for token in set(nvtx_starts)|set(nvtx_ends):
  if nvtx_starts.get(token,0)!=1 or nvtx_ends.get(token,0)!=1:
   errors.append("NVTX token lifecycle is not one start/one end: "+str(token))
 clock_points.sort(key=lambda item:item[0])
 if clock_points and (clock_labels.get("clock.calibration.start")!=1 or clock_labels.get("clock.calibration.end")!=1):
  errors.append("clock_calibration requires exactly one start and one end marker")
 host_clock={"point_count":len(clock_points),"offset_start_ns":None,"offset_end_ns":None,
             "drift_ns":None,"drift_ppm":None,"calibrated":False}
 if clock_points:
  host_clock["offset_start_ns"]=clock_points[0][1]-clock_points[0][0]
  host_clock["offset_end_ns"]=clock_points[-1][1]-clock_points[-1][0]
 if len(clock_points)>=2:
  span=clock_points[-1][0]-clock_points[0][0]
  if span>0:
   drift=host_clock["offset_end_ns"]-host_clock["offset_start_ns"]
   host_clock["drift_ns"]=drift;host_clock["drift_ppm"]=drift/span*1_000_000
   host_clock["calibrated"]=True
 request_token_ids=sorted(set(request_starts)|set(request_ends))
 nvtx_token_ids=sorted(set(nvtx_starts)|set(nvtx_ends))
 if nvtx_token_ids and request_token_ids!=nvtx_token_ids:
  errors.append("request token set differs from NVTX marker token set")
 summary={"request_tokens":len(request_token_ids),"request_token_ids":request_token_ids,
          "nvtx_token_ids":nvtx_token_ids,
          "unmatched_request_starts":unmatched_request_starts,
          "unmatched_request_ends":unmatched_request_ends,
          "nvtx_tokens":len(set(nvtx_starts)|set(nvtx_ends)),
          "nvtx_marker_events":sum(nvtx_starts.values())+sum(nvtx_ends.values()),
          "unmatched_nvtx_starts":unmatched_nvtx_starts,
          "unmatched_nvtx_ends":unmatched_nvtx_ends,
          "host_clock_calibration":host_clock}
 return summary,errors



def verify_run(a):
 run=Path(a.path).expanduser().resolve();manifest_path=run/"manifest.json"
 result={"run":str(run),"checks":{},"errors":[]}
 if not manifest_path.is_file():raise ValueError("manifest no encontrado: "+str(manifest_path))
 manifest=json.loads(manifest_path.read_text(encoding="utf-8"));run_id=manifest.get("run_id")
 if not isinstance(run_id,str) or not run_id:result["errors"].append("manifest run_id missing")
 if manifest.get("schema_version")!="nepenthes-run-0.1":result["errors"].append("unsupported manifest schema_version")
 if manifest.get("status") not in ("completed","command_failed"):result["errors"].append("manifest status is not terminal")
 checksums=run/"checksums.sha256";listed=set()
 if not checksums.is_file():result["errors"].append("checksums.sha256 missing")
 else:
  for line in checksums.read_text(encoding="utf-8").splitlines():
   if not line.strip():continue
   parts=line.split("  ",1)
   if len(parts)!=2:result["errors"].append("invalid checksum line");continue
   expected,relative=parts;target=(run/relative).resolve()
   if run not in target.parents and target!=run:result["errors"].append("checksum path escapes run directory: "+relative);continue
   listed.add(relative)
   if not target.is_file():result["errors"].append("missing file: "+relative);continue
   actual=__import__("hashlib").sha256(target.read_bytes()).hexdigest()
   if actual!=expected:result["errors"].append("checksum mismatch: "+relative)
  actual_files={str(p.relative_to(run)) for p in run.rglob("*") if p.is_file() and p.name!="checksums.sha256"}
  for missing in sorted(actual_files-listed):result["errors"].append("unhashed file: "+missing)
  for missing in sorted(listed-actual_files):result["errors"].append("checksum references missing file: "+missing)
 result["checks"]["checksums"]=not any(x.startswith(("checksum","missing file","unhashed file")) for x in result["errors"])
 events_path=run/"raw"/"events.jsonl";seen=set();events=[];event_errors=[]
 required={"schema_version","run_id","event_id","source","timestamp_unix_ns","monotonic_ns","request_id","event_kind","label","value0","value1","duration_ns","flags"}
 if not events_path.is_file():result["errors"].append("raw/events.jsonl missing")
 else:
  try:
   for line_no,line in enumerate(events_path.read_text(encoding="utf-8").splitlines(),1):
    event=json.loads(line);events.append(event)
    if not required.issubset(event):event_errors.append("event schema missing fields at line "+str(line_no))
    if event.get("schema_version")!="1.0":event_errors.append("event schema version mismatch at line "+str(line_no))
    if event.get("run_id")!=run_id:event_errors.append("event run_id mismatch at line "+str(line_no))
    if event.get("event_id") in seen:event_errors.append("duplicate event_id at line "+str(line_no))
    seen.add(event.get("event_id"))
    for field in ("timestamp_unix_ns","monotonic_ns","request_id","value0","value1","duration_ns","flags"):
     value=event.get(field)
     if isinstance(value,bool) or not isinstance(value,int):event_errors.append("event field "+field+" is not integer at line "+str(line_no))
     elif field in ("timestamp_unix_ns","monotonic_ns","request_id","duration_ns","flags") and value<0:event_errors.append("event field "+field+" is negative at line "+str(line_no))
  except (OSError,json.JSONDecodeError) as exc:event_errors.append("event JSONL invalid: "+str(exc))
 result["errors"].extend(event_errors)
 if not events:result["errors"].append("raw/events.jsonl empty")
 result["checks"]["events_valid"]=events_path.is_file() and bool(events) and not event_errors
 result["event_count"]=len(events)
 correlation,correlation_errors=validate_event_contract(events)
 result["correlation"]=correlation
 result["errors"].extend(correlation_errors)
 result["checks"]["correlation_contract"]=not correlation_errors
 merged=manifest.get("event_merge",{})
 if merged and merged.get("total")!=len(events):result["errors"].append("manifest event_merge total does not match events.jsonl")
 if merged.get("warnings"):result["errors"].append("manifest event_merge contains warnings")
 result["checks"]["event_merge_consistency"]=not any(x.startswith("manifest event_merge") for x in result["errors"])
 import sqlite3
 observations=run/"data"/"observations.sqlite"
 if not observations.is_file():result["errors"].append("data/observations.sqlite missing")
 else:
  try:
   with sqlite3.connect("file:"+str(observations)+"?mode=ro",uri=True) as db:
    integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity!="ok":result["errors"].append("observations.sqlite integrity check: "+str(integrity))
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"samples","events"}.issubset(tables):result["errors"].append("observations.sqlite missing expected tables")
    else:
     result["sample_rows"]=db.execute("SELECT count(*) FROM samples").fetchone()[0]
     result["event_rows"]=db.execute("SELECT count(*) FROM events").fetchone()[0]
     if result["event_rows"]!=len(events):result["errors"].append("observations.sqlite event count mismatch")
     if result["sample_rows"]!=manifest.get("sample_count"):result["errors"].append("observations.sqlite sample count mismatch")
  except sqlite3.Error as exc:result["errors"].append("observations.sqlite unreadable: "+str(exc))
 result["checks"]["observations_sqlite"]=not any(x.startswith(("data/observations.sqlite","observations.sqlite")) for x in result["errors"])
 summary_path=run/"data"/"summary.json"
 if not summary_path.is_file():result["errors"].append("data/summary.json missing")
 else:
  try:
   summary=json.loads(summary_path.read_text(encoding="utf-8"))
   if summary.get("run_id")!=run_id:result["errors"].append("summary.json run_id mismatch")
   if summary.get("sample_count")!=manifest.get("sample_count"):result["errors"].append("summary.json sample count mismatch")
  except (OSError,json.JSONDecodeError) as exc:result["errors"].append("summary.json invalid: "+str(exc))
 result["checks"]["summary_consistent"]=not any(x.startswith(("data/summary.json","summary.json")) for x in result["errors"])
 nsys_enabled=bool(manifest.get("nsys",{}).get("enabled"))
 nsys_meta_path=run/"data"/"nsys-import.json"
 nsys_import_status="not_requested"
 if nsys_enabled:
  if not nsys_meta_path.is_file():
   result["errors"].append("data/nsys-import.json missing while Nsight capture is enabled")
   nsys_import_status="missing"
  else:
   try:nsys_import_status=json.loads(nsys_meta_path.read_text(encoding="utf-8")).get("status","unknown")
   except (OSError,json.JSONDecodeError) as exc:
    result["errors"].append("data/nsys-import.json invalid: "+str(exc));nsys_import_status="invalid"
   if nsys_import_status!="imported":result["errors"].append("Nsight import status is not imported: "+str(nsys_import_status))
 else:
  if nsys_meta_path.is_file():
   try:nsys_import_status=json.loads(nsys_meta_path.read_text(encoding="utf-8")).get("status","not_requested")
   except (OSError,json.JSONDecodeError):nsys_import_status="invalid"
 result["nsys_import_status"]=nsys_import_status
 nsys_db=run/"data"/"nepenthes-import.sqlite"
 if nsys_enabled and nsys_db.is_file():
  try:
   with sqlite3.connect("file:"+str(nsys_db)+"?mode=ro",uri=True) as db:
    integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity!="ok":result["errors"].append("nepenthes-import.sqlite integrity check: "+str(integrity))
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"nepenthes_imports","nsys_activities"}.issubset(tables):
     result["errors"].append("nepenthes-import.sqlite missing paired import tables")
    else:
     import_row=db.execute("SELECT run_id FROM nepenthes_imports WHERE run_id=?",(run_id,)).fetchone()
     if import_row is None:result["errors"].append("Nsight import run_id does not match manifest")
     columns={row[1] for row in db.execute("PRAGMA table_info(nsys_activities)")}
     if correlation["nvtx_marker_events"]>0:
      if "nsys_clock_calibration_json" not in {row[1] for row in db.execute("PRAGMA table_info(nepenthes_imports)")}:
       result["errors"].append("Nsight importer schema lacks nsys_clock_calibration_json")
      else:
       calibration=json.loads(db.execute("SELECT nsys_clock_calibration_json FROM nepenthes_imports WHERE run_id=?",(run_id,)).fetchone()[0])
       result["nsys_clock_calibration"]=calibration
       if calibration.get("matched_marker_pairs",0)<2 or not calibration.get("nsight_clock_calibrated"):
        result["errors"].append("NVTX markers present but host↔Nsight clock calibration is incomplete")
      required_cols={"attributed_request_token","attribution_level","attribution_status"}
      if not required_cols.issubset(columns):
       result["errors"].append("Nsight activity schema lacks explicit attribution columns")
      else:
       false_exact=db.execute("SELECT count(*) FROM nsys_activities WHERE activity_kind IN ('cuda_kernel','cuda_memcpy','cuda_memset') AND attribution_level='exact'").fetchone()[0]
       missing_window_token=db.execute("SELECT count(*) FROM nsys_activities WHERE attribution_level='windowed' AND attributed_request_token IS NULL").fetchone()[0]
       ambiguous_with_token=db.execute("SELECT count(*) FROM nsys_activities WHERE attribution_status='overlapping_request_windows' AND attributed_request_token IS NOT NULL").fetchone()[0]
       if false_exact:result["errors"].append("Nsight GPU activities claim exact request attribution")
       if missing_window_token:result["errors"].append("windowed Nsight activity lacks request token")
       if ambiguous_with_token:result["errors"].append("ambiguous overlapping window carries a request token")
       if {"nvtx_correlation_token","nvtx_marker_phase"}.issubset(columns):
        bad_marker=db.execute("SELECT count(*) FROM nsys_activities WHERE activity_kind='nvtx_event' AND nvtx_marker_phase IS NOT NULL AND (nvtx_correlation_token IS NULL OR attributed_request_token!=nvtx_correlation_token OR attribution_level!='exact')").fetchone()[0]
        if bad_marker:result["errors"].append("Nsight NVTX marker identity is not exact or token-consistent")
  except (sqlite3.Error,TypeError,ValueError) as exc:result["errors"].append("nepenthes-import.sqlite invalid: "+str(exc))
 elif nsys_enabled:
  result["errors"].append("data/nepenthes-import.sqlite missing while Nsight capture is enabled")
 result["checks"]["nsys_import"]=not any(x.startswith(("data/nsys-import.json","data/nepenthes-import.sqlite","Nsight import","nepenthes-import.sqlite","NVTX markers","Nsight GPU","windowed Nsight","ambiguous overlapping","Nsight NVTX marker")) for x in result["errors"])
 nsys_calibration=result.get("nsys_clock_calibration",{})
 c07_pass=(nsys_enabled and correlation.get("request_tokens",0)>0
           and correlation.get("nvtx_marker_events",0)>=2
           and correlation.get("request_token_ids")==correlation.get("nvtx_token_ids")
           and correlation.get("host_clock_calibration",{}).get("calibrated") is True
           and nsys_calibration.get("matched_marker_pairs",0)>=2
           and nsys_calibration.get("nsight_clock_calibrated") is True
           and result["checks"]["nsys_import"])
 result["checks"]["c07_correlation"]=bool(c07_pass)
 c08_path=Path(a.c08_report).expanduser().resolve() if getattr(a,"c08_report",None) else run/"data"/"c08-overhead-report.json"
 c08_status="not_run";c08_pass=False
 if getattr(a,"c08_report",None) and not c08_path.is_file():
  result["errors"].append("C08 report path does not exist: "+str(c08_path));c08_status="missing"
 if c08_path.is_file():
  result["c08_report"]={"path":str(c08_path),"sha256":hashlib.sha256(c08_path.read_bytes()).hexdigest()}
  try:
   c08=json.loads(c08_path.read_text(encoding="utf-8"))
   c08_status=c08.get("overall_status","unknown")
   conditions=c08.get("conditions",{})
   c08_pass=(c08.get("schema")=="nepenthes-overhead-gate.v1"
             and c08.get("profile")=="standard"
             and c08_status=="accepted"
             and all(conditions.get(name,{}).get("paired_repetitions",0)>=3
                     and conditions.get(name,{}).get("gate_status")=="accepted"
                     for name in ("jsonl","nsys","combined")))
   if c08_status not in ("accepted","informational_only"):
    result["errors"].append("C08 overhead gate is not accepted: "+str(c08_status))
  except (OSError,json.JSONDecodeError) as exc:
   result["errors"].append("data/c08-overhead-report.json invalid: "+str(exc));c08_status="invalid"
 result["c08_overhead_status"]=c08_status
 result["checks"]["c08_overhead"]=bool(c08_pass)
 result["acceptance"]={
  "c07":"passed" if c07_pass else "pending",
  "c08":"passed" if c08_pass else ("informational_only" if c08_status=="informational_only" else "pending"),
  "scope":"run-level evidence gates only; project CI and physical hardware acceptance remain separate",
 }
 result["functional_complete"]=bool(c07_pass and c08_pass)
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
 v=sub.add_parser("verify");v.add_argument("path");v.add_argument("--c08-report",default=None,help="external paired-overhead report JSON; otherwise use data/c08-overhead-report.json");v.set_defaults(func=verify_run)
 t=sub.add_parser("self-test",help="run a tiny synthetic capture and verify its bundle");t.add_argument("--output",default=str(Path.home()/"NEPENTHES-runs"));t.set_defaults(func=self_test);return p
def main(argv=None):
 p=parser();a=p.parse_args(argv)
 if getattr(a,"interval",None) is not None and a.interval<=0:p.error("--interval debe ser positivo")
 try:return a.func(a)
 except (OSError,ValueError,json.JSONDecodeError) as e:print("nepenthes: error: "+str(e),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
