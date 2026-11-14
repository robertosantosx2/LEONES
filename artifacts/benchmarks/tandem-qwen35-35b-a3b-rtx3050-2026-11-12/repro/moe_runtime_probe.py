#!/usr/bin/env python3
"""Low-overhead per-request MoE host/PCIe telemetry; standard library only."""
from __future__ import annotations
import json,pathlib,statistics,threading,time
from datetime import datetime

def stamp(): return datetime.now().astimezone().isoformat()
def pressure(name):
    out={}
    try:
        for line in pathlib.Path('/proc/pressure/'+name).read_text().splitlines():
            p=line.split(); row={}
            for item in p[1:]:
                k,_,v=item.partition('=')
                try: row[k]=float(v)
                except ValueError: pass
            if p: out[p[0]]=row
    except Exception: pass
    return out
def proc(pid):
    if not pid:return {}
    root=pathlib.Path('/proc')/str(pid); out={}
    try:
        for line in (root/'io').read_text().splitlines():
            k,v=line.split(':',1);out[k.strip()]=int(v.strip())
    except Exception:pass
    try:
        for line in (root/'status').read_text().splitlines():
            if line.startswith(('VmRSS:','VmHWM:','Threads:')):
                k,v=line.split(':',1);out[k]=int(v.split()[0])
    except Exception:pass
    try:
        v=(root/'schedstat').read_text().split()
        if len(v)>1:out['sched_runtime_ns']=int(v[0]);out['sched_wait_ns']=int(v[1])
    except Exception:pass
    try:out['fd_count']=len(list((root/'fd').iterdir()))
    except Exception:pass
    return out
def cpufreq():
    v=[]
    for p in pathlib.Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq'):
        try:v.append(int(p.read_text())/1000)
        except Exception:pass
    return {'mean_mhz':statistics.fmean(v),'min_mhz':min(v),'max_mhz':max(v)} if v else {}
class RuntimeProbe:
    def __init__(self,outdir,request_id,pid=None,interval=.5):
        self.outdir=pathlib.Path(outdir);self.request_id=request_id;self.pid=pid;self.interval=max(.2,float(interval));self.samples=[];self.stop_event=threading.Event()
    def sample(self):
        return {'time':stamp(),'monotonic':time.monotonic(),'pid':self.pid,'process':proc(self.pid),'pressure':{k:pressure(k) for k in ('cpu','memory','io')},'cpu_frequency':cpufreq()}
    def loop(self):
        while not self.stop_event.is_set():self.samples.append(self.sample());self.stop_event.wait(self.interval)
        self.samples.append(self.sample())
    def start(self):
        self.started=stamp();self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
    def finish(self):
        self.stop_event.set();self.thread.join();self.finished=stamp()
        with (self.outdir/'moe_runtime_samples.jsonl').open('a',encoding='utf-8') as f:
            for s in self.samples:f.write(json.dumps({'request_id':self.request_id,**s},ensure_ascii=False)+chr(10))
        return self.summary()
    def summary(self):
        def vals(path):
            out=[]
            for s in self.samples:
                v=s
                for k in path:v=v.get(k,{}) if isinstance(v,dict) else {}
                if isinstance(v,(int,float)):out.append(v)
            return out
        def stat(path):
            v=vals(path);return {'min':min(v),'mean':statistics.fmean(v),'max':max(v)} if v else None
        a=self.samples[0] if self.samples else {};b=self.samples[-1] if self.samples else {};p0=a.get('process',{});p1=b.get('process',{})
        delta={k:max(0,p1[k]-p0[k]) for k in ('read_bytes','write_bytes','rchar','wchar','syscr','syscw','sched_runtime_ns','sched_wait_ns') if k in p0 and k in p1}
        return {'request_id':self.request_id,'pid':self.pid,'sample_count':len(self.samples),'interval_seconds':self.interval,'process_io_scheduler_deltas':delta,'threads':stat(['process','Threads']),'rss_kib':stat(['process','VmRSS']),'peak_rss_kib':stat(['process','VmHWM']),'fd_count':stat(['process','fd_count']),'cpu_frequency_mhz':stat(['cpu_frequency','mean_mhz']),'cpu_pressure_some_avg10':stat(['pressure','cpu','some','avg10']),'memory_pressure_some_avg10':stat(['pressure','memory','some','avg10']),'memory_pressure_full_avg10':stat(['pressure','memory','full','avg10']),'io_pressure_some_avg10':stat(['pressure','io','some','avg10']),'io_pressure_full_avg10':stat(['pressure','io','full','avg10']),'limitations':['PCIe throughput is device-wide, not process-attributed.','PSI is host-wide.','Short requests may not provide stable percentiles.','GPU and PCIe measurements are collected by resource_monitor.py to avoid duplicate nvidia-smi polling.','Per-layer routing and expert-cache hits require engine trace/log support.']}
