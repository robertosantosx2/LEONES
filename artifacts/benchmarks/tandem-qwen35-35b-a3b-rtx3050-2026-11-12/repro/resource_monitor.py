#!/usr/bin/env python3
"""Per-request Linux/NVIDIA resource sampler for the Tandem battery. Stdlib only."""
from __future__ import annotations
import csv, json, os, pathlib, re, shutil, subprocess, threading, time, statistics
from datetime import datetime, timezone
from urllib.parse import urlparse

def now():
    return datetime.now(timezone.utc).astimezone().isoformat()

def read_meminfo():
    out={}
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":",1); m=re.search(r"(\d+)",v)
            if m: out[k+"_bytes"]=int(m.group(1))*1024
    except Exception: pass
    total=out.get("MemTotal_bytes",0); avail=out.get("MemAvailable_bytes",0)
    out["ram_used_bytes"]=max(0,total-avail) if total else None
    st=out.get("SwapTotal_bytes",0); sf=out.get("SwapFree_bytes",0)
    out["swap_used_bytes"]=max(0,st-sf)
    return out

def cpu_ticks():
    try:
        v=list(map(int,pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:]))
        idle=v[3]+(v[4] if len(v)>4 else 0)
        return sum(v), idle
    except Exception: return None

def proc_stat(pid):
    try:
        s=pathlib.Path(f"/proc/{pid}/stat").read_text()
        tail=s[s.rfind(")")+2:].split()
        return {"utime_ticks":int(tail[11]),"stime_ticks":int(tail[12]),"rss_bytes":int(tail[21])*os.sysconf("SC_PAGE_SIZE")}
    except Exception: return {}

def find_pid(port, explicit=None):
    if explicit: return int(explicit)
    for p in pathlib.Path("/proc").iterdir():
        if not p.name.isdigit(): continue
        try: cmd=(p/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="ignore")
        except Exception: continue
        if "llama-server" in cmd and (f"--port {port}" in cmd or f"--port={port}" in cmd):
            return int(p.name)
    return None

def gpu_sample():
    exe=shutil.which("nvidia-smi")
    if not exe: return {"available":False,"error":"nvidia-smi not found"}
    q="timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,clocks.gr"
    try:
        r=subprocess.run([exe,f"--query-gpu={q}","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=2)
        if r.returncode: return {"available":False,"error":r.stderr.strip()}
        rows=[]
        for row in csv.reader(r.stdout.splitlines()):
            if len(row)>=9:
                vals=[x.strip() for x in row]
                def num(x):
                    try:return float(x)
                    except:return None
                rows.append({"timestamp":vals[0],"index":vals[1],"gpu_util_pct":num(vals[2]),"memory_util_pct":num(vals[3]),"vram_used_mib":num(vals[4]),"vram_total_mib":num(vals[5]),"temperature_c":num(vals[6]),"power_w":num(vals[7]),"graphics_clock_mhz":num(vals[8])})
        return {"available":True,"gpus":rows}
    except Exception as e:return {"available":False,"error":str(e)}

def vmstat_sample():
    try:
        d={}
        for line in pathlib.Path("/proc/vmstat").read_text().splitlines():
            x=line.split()
            if len(x)==2 and x[0] in ("pswpin","pswpout"): d[x[0]]=int(x[1])
        return d
    except Exception: return {}

def disk_sample():
    # Whole block devices only; sector counters are Linux 512-byte sectors.
    result={}
    try:
        for line in pathlib.Path("/proc/diskstats").read_text().splitlines():
            x=line.split(); name=x[2]
            if (pathlib.Path("/sys/class/block")/name/"partition").exists(): continue
            if len(x)>=14:
                result[name]={"reads":int(x[3]),"sectors_read":int(x[5]),"writes":int(x[7]),"sectors_written":int(x[9]),"io_ms":int(x[12])}
    except Exception: pass
    return result

class RequestSampler:
    def __init__(self, outdir, request_id, port, pid=None, interval=1.0):
        self.outdir=pathlib.Path(outdir); self.request_id=request_id; self.port=port
        self.pid=find_pid(port,pid); self.interval=interval; self.samples=[]
        self.stop_event=threading.Event(); self.thread=None
    def sample(self):
        s={"time":now(),"monotonic":time.monotonic(),"ram":read_meminfo(),"cpu_ticks":cpu_ticks(),"process":proc_stat(self.pid) if self.pid else {},"gpu":gpu_sample(),"disks":disk_sample(),"vmstat":vmstat_sample()}
        s["pid"]=self.pid
        return s
    def _loop(self):
        while not self.stop_event.is_set():
            self.samples.append(self.sample())
            self.stop_event.wait(self.interval)
        self.samples.append(self.sample())
    def start(self):
        self.started=now(); self.thread=threading.Thread(target=self._loop,daemon=True); self.thread.start()
    def finish(self):
        self.stop_event.set(); self.thread.join(); self.finished=now()
        raw=self.outdir/"resource_samples.jsonl"
        with raw.open("a",encoding="utf-8") as f:
            for s in self.samples:
                f.write(json.dumps({"request_id":self.request_id,**s},ensure_ascii=False)+"\n")
        return self.summary()
    def summary(self):
        def nums(path):
            vals=[]
            for s in self.samples:
                v=s
                for k in path: v=v.get(k,{}) if isinstance(v,dict) else {}
                if isinstance(v,(int,float)): vals.append(v)
            return vals
        def stats(path):
            v=nums(path)
            return {"min":min(v),"max":max(v),"mean":statistics.fmean(v)} if v else None
        first=self.samples[0] if self.samples else {}; last=self.samples[-1] if self.samples else {}
        disk={}
        names=set(first.get("disks",{}))|set(last.get("disks",{}))
        for n in names:
            a=first.get("disks",{}).get(n,{}); b=last.get("disks",{}).get(n,{})
            disk[n]={"read_bytes_delta":max(0,b.get("sectors_read",0)-a.get("sectors_read",0))*512,"write_bytes_delta":max(0,b.get("sectors_written",0)-a.get("sectors_written",0))*512,"read_ops_delta":max(0,b.get("reads",0)-a.get("reads",0)),"write_ops_delta":max(0,b.get("writes",0)-a.get("writes",0)),"io_ms_delta":max(0,b.get("io_ms",0)-a.get("io_ms",0))}
        swapin=swapout=None
        try:
            vm=dict(line.split() for line in pathlib.Path("/proc/vmstat").read_text().splitlines() if len(line.split())==2)
            swapin=int(vm.get("pswpin",0)); swapout=int(vm.get("pswpout",0))
        except Exception: pass
        gpu=[]
        for s in self.samples:
            gpu.extend(s.get("gpu",{}).get("gpus",[]))
        def gstat(k):
            v=[x[k] for x in gpu if isinstance(x.get(k),(int,float))]
            return {"min":min(v),"max":max(v),"mean":statistics.fmean(v)} if v else None
        # CPU percentages from first/last counters over the monitored interval.
        cpu_pct=proc_pct=None
        if len(self.samples)>1:
            a=self.samples[0]; b=self.samples[-1]
            if a.get("cpu_ticks") and b.get("cpu_ticks"):
                dticks=b["cpu_ticks"][0]-a["cpu_ticks"][0]; didle=b["cpu_ticks"][1]-a["cpu_ticks"][1]
                if dticks>0: cpu_pct=100*(dticks-didle)/dticks
            pa=a.get("process",{}); pb=b.get("process",{})
            hz=os.sysconf("SC_CLK_TCK"); elapsed=b["monotonic"]-a["monotonic"]
            if pa and pb and elapsed>0:
                proc_pct=100*((pb["utime_ticks"]+pb["stime_ticks"])-(pa["utime_ticks"]+pa["stime_ticks"]))/(hz*elapsed)
        return {"request_id":self.request_id,"pid":self.pid,"started_at":self.started,"finished_at":self.finished,"sample_count":len(self.samples),"interval_seconds":self.interval,
          "ram_used_bytes":stats(["ram","ram_used_bytes"]),"ram_available_bytes":stats(["ram","MemAvailable_bytes"]),"process_rss_bytes":stats(["process","rss_bytes"]),
          "swap_used_bytes":stats(["ram","swap_used_bytes"]),"cpu_system_pct_avg_over_interval":cpu_pct,"process_cpu_pct_avg_over_interval":proc_pct,
          "gpu_util_pct":gstat("gpu_util_pct"),"gpu_memory_util_pct":gstat("memory_util_pct"),"vram_used_mib":gstat("vram_used_mib"),"gpu_temperature_c":gstat("temperature_c"),"gpu_power_w":gstat("power_w"),
          "disk_deltas_all_whole_devices":disk,"swap_in_bytes_delta_system_wide":swapin_delta,"swap_out_bytes_delta_system_wide":swapout_delta,"gpu_sample_count":len(gpu),"disk_note":"Disk deltas are system-wide per whole block device; isolate the model SSD before attributing I/O if multiple workloads are active.","swap_note":"Swap deltas are system-wide; unrelated processes may contribute."}
