#!/usr/bin/env python3
"""One benchmark cell: start llama-server, run W1 (GSM8K) and optionally W4 (long context), stop it, parse cache stats.
    run_cell.py --bin build/bin/llama-server --model model.gguf --tag qwen-auto --cache-mib auto [--extra "..."]
    run_cell.py --bin upstream/build/bin/llama-server --model model.gguf --tag qwen-up --no-ngl --extra "-fit on -fitt 1024"
Writes <out>/<tag>.cell.json, <tag>.w1.json (and <tag>.w4.json) and <out>/<tag>.server.log.
LC_SAMPLING / LC_SEED (see common.py) pick the sampling arm; unset = greedy."""
import argparse, json, os, re, shlex, signal, subprocess, sys, time, urllib.request


def parse_stats(log):
    """The expert cache's end-of-run lines: 'hits = 1, misses = 2, hit rate = x%, uploaded = 3 MiB'."""
    rows = []
    for line in log.splitlines():
        if "llama_moe_cache:" not in line:
            continue
        m = re.search(r"hits\s*=\s*(\d+).*?misses\s*=\s*(\d+).*?uploaded\s*=\s*([\d.]+)\s*MiB", line)
        if m:
            rows.append({"line": line.split("llama_moe_cache:")[1].strip(),
                         "hits": int(m[1]), "misses": int(m[2]), "uploaded_mib": float(m[3])})
    return rows


def cpu_model():
    try:
        return next(l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    except Exception:
        return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True, help="llama-server binary (tandem.cpp or plain llama.cpp)")
    ap.add_argument("--model", required=True, help="GGUF (first shard)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--cache-mib", default="resident",
                    help="'resident' = no -cmoe; N or auto = -cmoe --moe-cache-mib N (tandem.cpp only)")
    ap.add_argument("--gpu", default="0", help="CUDA_VISIBLE_DEVICES")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--no-ngl", action="store_true", help="omit -ngl 99 (llama.cpp -fit only places layers when ngl is unset)")
    ap.add_argument("--extra", default="", help="extra server flags, e.g. speculative decoding (shlex-split)")
    ap.add_argument("--w1-n", type=int, default=200)
    ap.add_argument("--w1-max-tokens", type=int, default=2048)
    ap.add_argument("--w4", default="", help="also run W4 at these prompt lengths, e.g. 16384,32768,65536 (needs --corpus)")
    ap.add_argument("--corpus", default="", help="W4 text: a llama.cpp checkout")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cmd = [a.bin, "-m", a.model, *([] if a.no_ngl else ["-ngl", "99"]), "-c", str(a.ctx), "--port", str(a.port),
           "--alias", "m", "-np", "1", "--host", "127.0.0.1",
           "-lzm", "on", "-lv", "4"]  # info level: the cache's size and end-of-run statistics
    if a.cache_mib != "resident":
        cmd += ["-cmoe", "--moe-cache-mib", a.cache_mib]
    cmd += shlex.split(a.extra)
    logp = f"{a.out}/{a.tag}.server.log"
    # PCI_BUS_ID makes numeric GPU ids match nvidia-smi on boxes with mixed GPUs
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=a.gpu, CUDA_DEVICE_ORDER="PCI_BUS_ID")
    srv = subprocess.Popen(cmd, stdout=open(logp, "w"), stderr=subprocess.STDOUT, env=env)
    here = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable
    common = ["--port", str(a.port), "--model", "m"]
    out = {"tag": a.tag, "cmd": cmd, "model": os.path.basename(a.model), "cpu": cpu_model(),
           "sampling": os.environ.get("LC_SAMPLING", "greedy")}
    try:
        t0 = time.time()
        while True:
            if srv.poll() is not None:
                sys.exit(f"server died, see {logp}")
            try:
                if b"ok" in urllib.request.urlopen(f"http://127.0.0.1:{a.port}/health", timeout=2).read():
                    break
            except Exception:
                time.sleep(2)
        out["boot_s"] = time.time() - t0
        subprocess.run([py, f"{here}/w1_gsm8k.py", *common, "--n", str(a.w1_n), "--max-tokens", str(a.w1_max_tokens),
                        "--out", f"{a.out}/{a.tag}.w1.json"], check=True)
        out["w1"] = json.load(open(f"{a.out}/{a.tag}.w1.json"))["summary"]
        if a.w4:
            subprocess.run([py, f"{here}/w4_longctx.py", *common, "--lengths", a.w4, "--corpus", a.corpus,
                            "--out", f"{a.out}/{a.tag}.w4.json"], check=True)
            out["w4"] = json.load(open(f"{a.out}/{a.tag}.w4.json"))["summary"]
    finally:
        srv.send_signal(signal.SIGINT)
        try:
            srv.wait(60)
        except subprocess.TimeoutExpired:
            srv.kill()
    out["cache_stats"] = parse_stats(open(logp, errors="replace").read())
    json.dump(out, open(f"{a.out}/{a.tag}.cell.json", "w"), indent=1)
    print(json.dumps({k: out.get(k) for k in ("tag", "w1", "w4", "cache_stats")}, indent=1))


if __name__ == "__main__":
    main()
