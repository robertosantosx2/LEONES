#!/usr/bin/env python3
"""Serial, state-gated benchmark for OpenAI-compatible local inference servers.

The harness never kills unrelated processes, downloads models, or changes host
settings. Engine command lines are configured in JSON; every profile is a fresh
server process so load/unload and resource recovery are observable.
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, platform, re, shutil, signal
import socket, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

PROMPT_DEFAULTS = {"temperature": 0.0, "top_p": 1.0, "seed": 42}
SENSITIVE_ENV = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD)", re.I)

def utc():
    return datetime.now(timezone.utc).isoformat()

def run(cmd, timeout=10):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def machine_snapshot():
    d = {"timestamp": utc(), "platform": platform.platform(), "kernel": platform.release(),
         "python": platform.python_version(), "cpu_count": os.cpu_count()}
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:")):
                k, v = line.split(":", 1); d[k] = int(v.strip().split()[0]) * 1024
    except Exception as e: d["meminfo_error"] = str(e)
    d["uptime"] = pathlib.Path("/proc/uptime").read_text().split()[0] if pathlib.Path("/proc/uptime").exists() else None
    d["nvidia_smi"] = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw,driver_version",
                           "--format=csv,noheader,nounits"])
    d["nvidia_processes"] = run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                                 "--format=csv,noheader,nounits"])
    d["loadavg"] = run(["cat", "/proc/loadavg"])
    return d

def available_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]

def render(value, fields):
    if isinstance(value, str):
        return value.format(**fields)
    if isinstance(value, list):
        return [render(x, fields) for x in value]
    return value

def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def log_line(path, msg):
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{utc()}] {msg}\n")

def health(base, path, proc, timeout):
    deadline = time.monotonic() + timeout
    url = base + path
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"engine exited before health check (exit={proc.returncode})")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if 200 <= r.status < 300: return
        except Exception:
            time.sleep(.5)
    raise TimeoutError(f"health timeout: {url}")

def stream_request(base, path, api_key, messages, settings, timeout):
    body = dict(messages=messages, stream=True, stream_options={"include_usage": True}, **settings)
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if api_key: headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(base + path, data=data, headers=headers)
    started = time.perf_counter(); first = last = None
    chunks, usage, raw_lines = [], None, []
    with urllib.request.urlopen(req, timeout=timeout) as response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"): continue
            payload = line[5:].strip()
            if payload == "[DONE]": break
            try: item = json.loads(payload)
            except json.JSONDecodeError:
                raw_lines.append(line); continue
            if item.get("usage"): usage = item["usage"]
            for choice in item.get("choices", []):
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if isinstance(content, str) and content:
                    now = time.perf_counter()
                    if first is None: first = now
                    last = now
                    chunks.append(content)
    ended = time.perf_counter()
    text = "".join(chunks)
    completion = usage.get("completion_tokens") if isinstance(usage, dict) else None
    prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    decode_s = (last-first) if first is not None and last is not None else None
    return {"text": text, "usage": usage, "prompt_tokens": prompt_tokens,
            "completion_tokens": completion,
            "ttft_s": (first-started) if first is not None else None,
            "wall_s": ended-started,
            "decode_tokens_per_s": ((completion-1)/decode_s if completion and decode_s and decode_s > 0 else None),
            "stream_fragments": len(chunks), "raw_unparsed_sse": raw_lines}

def proc_rss(pid):
    try:
        status = pathlib.Path(f"/proc/{pid}/status").read_text()
        m = re.search(r"VmRSS:\s+(\d+)\s+kB", status)
        return int(m.group(1))*1024 if m else None
    except Exception: return None

def process_tree_rss(pid):
    # Best-effort direct child + server RSS. Do not require psutil.
    total = proc_rss(pid) or 0
    try:
        children = pathlib.Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        total += sum(proc_rss(int(x)) or 0 for x in children)
    except Exception: pass
    return total or None

def stop_child(proc, timeout=30):
    if proc.poll() is not None: return {"exit_code": proc.returncode, "forced_kill": False}
    try: os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError: pass
    try: return {"exit_code": proc.wait(timeout=timeout), "forced_kill": False}
    except subprocess.TimeoutExpired:
        try: os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        return {"exit_code": proc.wait(timeout=10), "forced_kill": True}

def mib_delta(a, b, key):
    x, y = a.get(key), b.get(key)
    return ((x-y)/1048576) if isinstance(x, (int,float)) and isinstance(y, (int,float)) else None

def gpu_values(snapshot):
    s = snapshot.get("nvidia_smi", {}).get("stdout", "")
    if not s: return None
    try:
        p = [x.strip() for x in s.splitlines()[0].split(",")]
        return {"name":p[0], "memory_total_mib":float(p[1]), "memory_used_mib":float(p[2]),
                "util_pct":float(p[3]), "temperature_c":float(p[4])}
    except Exception: return None

def wait_settled(baseline, cfg):
    settle = cfg["settle"]
    deadline = time.monotonic() + settle["timeout_s"]
    streak = 0; last = None
    while time.monotonic() < deadline:
        last = machine_snapshot()
        ram_delta = mib_delta(baseline, last, "MemAvailable:")
        # /proc values are bytes; threshold configured in MiB.
        ram_ok = ram_delta is None or ram_delta <= settle["ram_available_delta_mib"] * 1048576
        bg, ag = gpu_values(baseline), gpu_values(last)
        vram_ok = True; util_ok = True
        if bg and ag:
            vram_ok = (ag["memory_used_mib"] - bg["memory_used_mib"]) <= settle["vram_used_delta_mib"]
            util_ok = ag["util_pct"] <= settle["gpu_util_max_pct"]
        if ram_ok and vram_ok and util_ok: streak += 1
        else: streak = 0
        if streak >= settle["consecutive_idle_samples"]: return True, last
        time.sleep(settle["sample_interval_s"])
    return False, last

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="artifacts/engine-comparison")
    ap.add_argument("--only", help="comma-separated engine ids")
    ap.add_argument("--allow-dirty-baseline", action="store_true",
                    help="continue despite a dirty initial GPU; still record it")
    args = ap.parse_args()
    cfg = json.loads(pathlib.Path(args.config).read_text())
    model = pathlib.Path(args.model).expanduser().resolve()
    if not model.is_file(): ap.error(f"model not found: {model}")
    model_hash = sha256(model)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = pathlib.Path(args.out) / stamp
    for p in ["engines", "responses", "machine"]: (out/p).mkdir(parents=True, exist_ok=True)
    results = out/"results.jsonl"; session_log = out/"session.log"
    baseline = machine_snapshot()
    manifest = {"schema_version":1, "created_at":utc(), "config":cfg, "model":{"path":str(model),"size_bytes":model.stat().st_size,"sha256":model_hash},
                "host_baseline":baseline, "argv":sys.argv, "environment":{k:("<redacted>" if SENSITIVE_ENV.search(k) else v) for k,v in os.environ.items() if k.startswith(("CUDA","HIP","TENSORFOLD","LLAMA","TF_"))}}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    summary = {"session":str(out), "model_sha256":model_hash, "engines":[], "aborted":False}
    allowed = set(args.only.split(",")) if args.only else None
    dirty_gpu = gpu_values(baseline)
    if dirty_gpu and dirty_gpu["util_pct"] > cfg["settle"]["gpu_util_max_pct"] and not args.allow_dirty_baseline:
        raise SystemExit("GPU baseline is busy. Stop unrelated GPU workloads or use --allow-dirty-baseline to record and proceed.")
    for engine in cfg["engines"]:
        if not engine.get("enabled", False) or (allowed and engine["id"] not in allowed): continue
        engine_id = engine["id"]
        engine_model = pathlib.Path(engine.get("model", str(model))).expanduser().resolve()
        if not engine_model.is_file():
            append_jsonl(results,{"type":"engine","engine":engine_id,"status":"MODEL_MISSING","model":str(engine_model)})
            continue
        engine_model_hash = sha256(engine_model)
        asset_records = []
        for asset in engine.get("model_assets", []):
            asset_path = pathlib.Path(asset).expanduser()
            if not asset_path.is_absolute(): asset_path = pathlib.Path(__file__).resolve().parents[1] / asset_path
            asset_records.append({"path":str(asset_path),"sha256":sha256(asset_path) if asset_path.is_file() else None,"exists":asset_path.is_file()})
        source_meta_path = pathlib.Path(engine.get("source_meta", "unused")) if engine.get("source_meta") else None
        source_meta = None
        if source_meta_path:
            if not source_meta_path.is_absolute(): source_meta_path = pathlib.Path(__file__).resolve().parents[1] / source_meta_path
            if source_meta_path.is_file(): source_meta = json.loads(source_meta_path.read_text())
        if engine.get("require_source_snapshot", True) and not source_meta:
            append_jsonl(results,{"type":"engine","engine":engine_id,"status":"SOURCE_NOT_VENDORED","source_meta":str(source_meta_path) if source_meta_path else None})
            continue
        build_meta_path = pathlib.Path(engine["build_meta"]) if engine.get("build_meta") else None
        build_meta = None
        if build_meta_path:
            if not build_meta_path.is_absolute(): build_meta_path = pathlib.Path(__file__).resolve().parents[1] / build_meta_path
            if build_meta_path.is_file(): build_meta = json.loads(build_meta_path.read_text())
        if engine.get("require_build_evidence", True) and not build_meta:
            append_jsonl(results,{"type":"engine","engine":engine_id,"status":"BUILD_EVIDENCE_REQUIRED","build_meta":str(build_meta_path) if build_meta_path else None})
            continue
        engine_summary = {"id":engine_id,"model_assets":asset_records,"profiles":[]}
        summary["engines"].append(engine_summary)
        for profile in cfg["profiles"]:
            prof = dict(profile)
            port = available_port()
            fields = {"model":str(engine_model),"port":port,"ctx":prof.get("ctx",512),"threads":prof.get("threads",4),
                      "gpu_layers":prof.get("gpu_layers",0),"parallel":prof.get("parallel",1),"device":prof.get("device","auto")}
            cmd = render(engine["command"], fields)
            env = os.environ.copy()
            env.update({k: str(render(v, fields)) for k,v in engine.get("env", {}).items()})
            if not isinstance(cmd,list) or not cmd or any("/ABS/PATH/" in x for x in cmd):
                append_jsonl(results,{"type":"profile","engine":engine_id,"profile":prof["name"],"status":"CONFIG_REQUIRED","command":cmd,"model":str(engine_model),"model_sha256":engine_model_hash})
                continue
            base = render(engine["base_url"],fields)
            engdir = out/"engines"/engine_id; engdir.mkdir(parents=True,exist_ok=True)
            stdout_path, stderr_path = engdir/(prof["name"]+".stdout.log"), engdir/(prof["name"]+".stderr.log")
            before = machine_snapshot()
            (out/"machine"/engine_id).mkdir(parents=True,exist_ok=True)
            (out/"machine"/engine_id/(prof["name"]+".before.json")).write_text(json.dumps(before,indent=2)+"\n")
            start = time.perf_counter()
            load_s = None
            with open(stdout_path,"w") as so, open(stderr_path,"w") as se:
                proc = subprocess.Popen(cmd,stdout=so,stderr=se,start_new_session=True,env=env)
                try:
                    health(base, engine.get("health_path", cfg["api"]["health_path"]), proc, cfg["api"]["startup_timeout_s"])
                    load_s = time.perf_counter()-start
                    during = machine_snapshot()
                    (out/"machine"/engine_id/(prof["name"]+".loaded.json")).write_text(json.dumps(during,indent=2)+"\n")
                    if cfg.get("warmup",True):
                        stream_request(base,engine.get("chat_path", cfg["api"]["chat_path"]),engine.get("api_key", cfg["api"].get("api_key")),[{"role":"user","content":"Responde solamente: listo."}],
                                       {**PROMPT_DEFAULTS,"max_tokens":8},cfg["api"]["request_timeout_s"])
                    for prompt in cfg["prompts"]:
                        prompt_file = out/"responses"/engine_id/prof["name"]/(prompt["id"]+".txt")
                        prompt_file.parent.mkdir(parents=True,exist_ok=True)
                        for rep in range(cfg.get("repetitions",1)):
                            settings = {**PROMPT_DEFAULTS,"max_tokens":prompt.get("max_tokens",128),
                                        "temperature":prompt.get("temperature",0.0),"top_p":prompt.get("top_p",1.0),
                                        "seed":prompt.get("seed",42)}
                            t0 = time.perf_counter()
                            try:
                                measured = stream_request(base,engine.get("chat_path", cfg["api"]["chat_path"]),engine.get("api_key", cfg["api"].get("api_key")),
                                                          prompt["messages"],settings,cfg["api"]["request_timeout_s"])
                                measured.update({"type":"measurement","status":"OK","engine":engine_id,"model":str(engine_model),"model_sha256":engine_model_hash,"source_commit":source_meta.get("commit") if source_meta else None,"build_binary_sha256":(build_meta or {}).get("binary",{}).get("sha256"),"model_assets":asset_records,"profile":prof["name"],
                                                 "prompt_id":prompt["id"],"repetition":rep+1,"settings":settings,
                                                 "load_s":load_s,"process_rss_bytes":process_tree_rss(proc.pid),
                                                 "elapsed_s":time.perf_counter()-t0,"timestamp":utc()})
                                with open(prompt_file,"a",encoding="utf-8") as f:
                                    f.write(f"\n--- repetition {rep+1} ---\n{measured['text']}\n")
                            except Exception as e:
                                measured = {"type":"measurement","status":"ERROR","engine":engine_id,"model":str(engine_model),"model_sha256":engine_model_hash,"source_commit":source_meta.get("commit") if source_meta else None,"build_binary_sha256":(build_meta or {}).get("binary",{}).get("sha256"),"profile":prof["name"],
                                            "prompt_id":prompt["id"],"repetition":rep+1,"error":str(e),"timestamp":utc()}
                            measured["machine_after_request"] = machine_snapshot()
                            append_jsonl(results,measured)
                            log_line(session_log,f"{engine_id}/{prof['name']} {prompt['id']} rep={rep+1} status={measured['status']}")
                    engine_status = "COMPLETED"
                except Exception as e:
                    engine_status = "ENGINE_ERROR"
                    append_jsonl(results,{"type":"profile","engine":engine_id,"model":str(engine_model),"model_sha256":engine_model_hash,"profile":prof["name"],"status":engine_status,"error":str(e),"command":cmd})
                    log_line(session_log,f"ERROR {engine_id}/{prof['name']}: {e}")
                finally:
                    stop = stop_child(proc)
            after = machine_snapshot()
            (out/"machine"/engine_id/(prof["name"]+".after.json")).write_text(json.dumps(after,indent=2)+"\n")
            recovered, settled = wait_settled(baseline,cfg)
            if settled:
                (out/"machine"/engine_id/(prof["name"]+".settled.json")).write_text(json.dumps(settled,indent=2)+"\n")
            binary_path = shutil.which(cmd[0]) if cmd and not pathlib.Path(cmd[0]).is_absolute() else (cmd[0] if cmd else None)
            binary_hash = sha256(binary_path) if binary_path and pathlib.Path(binary_path).is_file() else None
            prof_result = {"name":prof["name"],"status":engine_status,"command":cmd,"base_url":base,"binary_path":binary_path,"binary_sha256":binary_hash,"source":source_meta,"build_evidence":build_meta,"model_path":str(engine_model),"model_sha256":engine_model_hash,"model_assets":asset_records,"environment":{k:("<redacted>" if SENSITIVE_ENV.search(k) else v) for k,v in env.items() if k in ("PATH","LD_LIBRARY_PATH","CC","CXX") or k.startswith(("CUDA","HIP","TENSORFOLD","LLAMA","TF_","RUST","CMAKE"))},
                           "load_s":locals().get("load_s"),"stop":stop,"post_unload_recovered":recovered,
                           "machine_before":before,"machine_after":after}
            engine_summary["profiles"].append(prof_result)
            append_jsonl(results,{"type":"profile","engine":engine_id,"profile":prof["name"],"status":engine_status,
                                  "load_s":prof_result["load_s"],"stop":stop,"post_unload_recovered":recovered})
            if not recovered:
                summary["aborted"] = True
                summary["abort_reason"] = f"Machine did not return to baseline after {engine_id}/{prof['name']}; no next model will be loaded."
                log_line(session_log,summary["abort_reason"])
                break
        if summary["aborted"]: break
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    print(out)
    print("Results:",results)
    print("Summary:",out/"summary.json")
    if summary["aborted"]: sys.exit(3)

if __name__ == "__main__":
    main()
