#!/usr/bin/env python3
"""Shell-free runtime benchmark harness producing LEONES evidence v1.1."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, platform, re, selectors, shutil, subprocess, time, uuid
from pathlib import Path
from statistics import mean, median, stdev

TPS_RE = re.compile(r"(?:Generation:\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:tok(?:ens)?|t)/s", re.I)
TOKENS_RE = re.compile(r"([0-9]+)\s+tokens?", re.I)

def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def sha256_file(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def sha256_text(s): return hashlib.sha256(s.encode()).hexdigest()
def version(exe):
    try:
        p=subprocess.run([exe,"--version"],capture_output=True,text=True,timeout=10,check=False); t=(p.stdout or p.stderr).strip()
        return t.splitlines()[0] if t else "unknown"
    except Exception as e: return f"unavailable: {e}"
def hardware():
    try: ram=round(os.sysconf("SC_PHYS_PAGES")*os.sysconf("SC_PAGE_SIZE")/1024/1024,2)
    except Exception: ram=None
    threads=os.cpu_count(); physical=None
    try:
        s={x for x in subprocess.run(["lscpu","-p=CPU,Core"],capture_output=True,text=True,timeout=5).stdout.splitlines() if x and not x.startswith("#")}
        physical=len({x.split(",",1)[1] for x in s if "," in x}) or None
    except Exception: pass
    gpu=vram=None
    if shutil.which("nvidia-smi"):
        try:
            x=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=5).stdout.strip().splitlines()[0]
            gpu,m=x.split(",",1); gpu=gpu.strip(); vram=float(m.strip())
        except Exception: pass
    return {"host":platform.node(),"os":platform.platform(),"kernel":platform.release(),"architecture":platform.machine(),"cpu":platform.processor() or platform.uname().processor,"cpu_threads":threads,"physical_cores":physical,"ram_total_mb":ram,"gpu":gpu,"vram_total_mb":vram}
def child_rss():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024,2)
    except Exception:return None
def gpu_snapshot():
    if not shutil.which("nvidia-smi"): return None,None
    try:
        x=subprocess.run(["nvidia-smi","--query-gpu=memory.used,power.draw","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=5).stdout.strip().splitlines()[0]
        a,b=x.split(",",1); return float(a),float(b)
    except Exception:return None,None
def run_once(command):
    t=time.perf_counter(); first=None; out=[]; err=[]
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    sel=selectors.DefaultSelector(); sel.register(p.stdout,selectors.EVENT_READ,"stdout"); sel.register(p.stderr,selectors.EVENT_READ,"stderr")
    while sel.get_map():
        for k,_ in sel.select(.1):
            line=k.fileobj.readline()
            if line=="": sel.unregister(k.fileobj); continue
            if first is None and line.strip(): first=(time.perf_counter()-t)*1000
            (out if k.data=="stdout" else err).append(line)
    code=p.wait(); total=(time.perf_counter()-t)*1000; text="".join(out)+"\n"+"".join(err)
    m=TPS_RE.findall(text); tps=float(m[-1].replace(",",".")) if m else None
    tok= TOKENS_RE.findall(text); tokens=int(tok[-1]) if tok else None
    gen=max(0,total-first) if first is not None else None
    vram,power=gpu_snapshot()
    return {"ttft_ms":first,"first_output_ms":first,"generation_time_ms":gen,"output_tokens":tokens,"tokens_per_second":tps,"total_time_ms":round(total,3),"peak_memory_mb":child_rss(),"peak_vram_mb":vram,"power_w":power,"exit_code":code,"stdout":"".join(out),"stderr":"".join(err)}
def summarize(ms):
    metrics={}
    for k in ("ttft_ms","generation_time_ms","output_tokens","tokens_per_second","total_time_ms","peak_memory_mb","peak_vram_mb","power_w"):
        v=[float(x[k]) for x in ms if x.get(k) is not None]
        if not v: continue
        d={"mean":mean(v),"median":median(v),"min":min(v),"max":max(v)}
        if len(v)>1:d["stdev"]=stdev(v)
        metrics[k]=d
    return {"measurement_count":len(ms),"metrics":metrics}
def main():
    a=argparse.ArgumentParser(); a.add_argument("--command-json",type=Path,required=True); a.add_argument("--output",type=Path,required=True); a.add_argument("--artifact",type=Path,required=True)
    a.add_argument("--model-id",required=True); a.add_argument("--model-name",required=True); a.add_argument("--model-revision",required=True); a.add_argument("--model-source",default=None); a.add_argument("--quantization",required=True); a.add_argument("--context",type=int,required=True)
    a.add_argument("--prompt-protocol-id",required=True); a.add_argument("--prompt",default=""); a.add_argument("--input-tokens",type=int,default=None); a.add_argument("--output-token-limit",type=int,default=128); a.add_argument("--temperature",type=float,default=0.0); a.add_argument("--top-p",type=float,default=None); a.add_argument("--seed",type=int,default=None); a.add_argument("--warmup",type=int,default=1); a.add_argument("--iterations",type=int,default=5); a.add_argument("--runtime",default="llama.cpp"); a.add_argument("--backend",default=None)
    x=a.parse_args(); command=json.loads(x.command_json.read_text())
    if not isinstance(command,list) or not command or not all(isinstance(i,str) for i in command): raise SystemExit("command-json must be a non-empty JSON string array")
    artifact=x.artifact.resolve()
    if not artifact.is_file(): raise SystemExit(f"artifact does not exist: {artifact}")
    binary=Path(command[0]).resolve(); bh=sha256_file(binary) if binary.is_file() else None
    for _ in range(x.warmup): run_once(command)
    start=now(); ms=[]
    for i in range(1,x.iterations+1):
        m=run_once(command); m["iteration"]=i; ms.append(m)
    end=now()
    ev={"schema":"runtime-benchmark-evidence.v1.1","execution_id":"rt-"+uuid.uuid4().hex,"timestamp_start":start,"timestamp_end":end,
      "model":{"id":x.model_id,"name":x.model_name,"revision":x.model_revision,"source":x.model_source,"artifact":str(artifact),"quantization":x.quantization,"context_length":x.context},
      "protocol":{"prompt_protocol_id":x.prompt_protocol_id,"prompt_sha256":sha256_text(x.prompt) if x.prompt else None,"input_tokens":x.input_tokens,"output_token_limit":x.output_token_limit,"temperature":x.temperature,"top_p":x.top_p,"seed":x.seed,"context":x.context,"warmup_iterations":x.warmup,"measurement_iterations":x.iterations},
      "runtime":{"name":x.runtime,"version":version(command[0]),"revision":None,"backend":x.backend,"binary":str(binary),"binary_sha256":bh,"command":command},"hardware":hardware(),"measurements":ms,"summary":summarize(ms),
      "process":{"exit_code":max(m["exit_code"] for m in ms),"stdout":"\n".join(m["stdout"] for m in ms),"stderr":"\n".join(m["stderr"] for m in ms)},"artifact":{"path":str(artifact),"sha256":sha256_file(artifact),"size":artifact.stat().st_size}}
    x.output.parent.mkdir(parents=True,exist_ok=True); x.output.write_text(json.dumps(ev,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"execution_id":ev["execution_id"],"output":str(x.output),"summary":ev["summary"]},indent=2)); return 0 if all(m["exit_code"]==0 for m in ms) else 1
if __name__=="__main__": raise SystemExit(main())
