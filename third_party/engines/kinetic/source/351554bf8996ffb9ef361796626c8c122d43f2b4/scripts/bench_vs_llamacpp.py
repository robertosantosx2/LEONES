#!/usr/bin/env python3
"""Kinetic against llama.cpp on the same GGUF file and CPU threads.

Two comparisons, printed as one markdown table:

- plain: `kinetic bench` against `llama-bench`, prompt 512 and generate 128
  tokens with no drafting, best of the repetitions on both sides;
- edit: one greedy chat request that rewrites a piece of code, served by
  `kinetic serve` and by `llama-server` with its speculative decoding on
  (`--spec-type`, n-gram drafts by default), measured once, the same way on
  the client: generated tokens over the time from first to last token.

The GPUs are hidden from llama.cpp so both run on the CPU. Servers run one
at a time and are stopped afterwards; nothing but 127.0.0.1 is contacted.

    python scripts/bench_vs_llamacpp.py model.gguf --llama-dir path/to/llama.cpp/bin
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROMPT, GENERATE = 512, 128

EDIT_CODE = '''def summarize(orders):
    x = 0
    count = 0
    biggest = None
    for order in orders:
        if order.get("status") != "paid":
            continue
        amount = order["amount"]
        x += amount
        count += 1
        if biggest is None or amount > biggest["amount"]:
            biggest = order
    average = x / count if count else 0
    return {
        "total": x,
        "count": count,
        "average": round(average, 2),
        "biggest": biggest["id"] if biggest else None,
    }


def report(orders, out):
    s = summarize(orders)
    out.write(f"paid orders: {s['count']}\\n")
    out.write(f"total: {s['total']}\\n")
    out.write(f"average: {s['average']}\\n")
    out.write(f"biggest: {s['biggest']}\\n")
'''

EDIT_REQUEST = (
    "Rename the variable `x` to `total_paid` in this code. "
    "Reply with the whole updated code only.\n\n```python\n" + EDIT_CODE + "```"
)


def tool(directory, name):
    exe = name + (".exe" if os.name == "nt" else "")
    path = os.path.join(directory, exe) if directory else shutil.which(name)
    if not path or not os.path.isfile(path):
        sys.exit(f"cannot find {exe}" + (f" in {directory}" if directory else " on PATH"))
    return path


def run_json(cmd, env=None):
    out = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    return json.loads(out.stdout)


def cpu_only_env():
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = "-1"
    env["HIP_VISIBLE_DEVICES"] = "-1"
    return env


def plain(args, kinetic, llama_bench):
    k = run_json([kinetic, "bench", args.model, "--device", "cpu", "-r", str(args.repetitions), "-t", str(args.threads), "--json"])
    llama_cmd = [
        llama_bench, "-m", args.model, "-p", str(PROMPT), "-n", str(GENERATE),
        "-r", str(args.repetitions), "-t", str(args.threads), "-ngl", "0", "-fa", "on", "-o", "json",
    ]
    rows = run_json(llama_cmd, cpu_only_env())
    best = {}
    for row in rows:
        test = "prompt" if row["n_prompt"] else "generate"
        best[test] = max(row.get("samples_ts") or [row["avg_ts"]])
    return {
        "prompt": (k["prefill_tokens_per_second"], best["prompt"]),
        "generate": (k["decode_tokens_per_second"], best["generate"]),
    }, " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(llama_cmd))


def wait_ready(base, proc, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"server exited with code {proc.returncode}")
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.5)
    sys.exit("server did not become ready")


def stream_chat(base, max_tokens):
    body = json.dumps({
        "messages": [{"role": "user", "content": EDIT_REQUEST}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "top_k": 1,
        "repeat_penalty": 1.0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    first = last = None
    pieces, text, tokens = 0, [], None
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                tokens = chunk["usage"]["completion_tokens"]
            for choice in chunk.get("choices", []):
                content = (choice.get("delta") or {}).get("content")
                if content:
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    pieces += 1
                    text.append(content)
    tokens = tokens or pieces
    rate = (tokens - 1) / (last - first) if first and last > first else 0.0
    return rate, "".join(text)


def serve_and_measure(cmd, port, env, max_tokens):
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_ready(base, proc)
        stream_chat(base, 8)
        # Measured once: a repeated answer would let Kinetic draft from the
        # previous one, which says nothing about a first edit.
        return stream_chat(base, max_tokens)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()


def edit(args, kinetic, llama_server):
    k_rate, k_text = serve_and_measure(
        [kinetic, "serve", args.model, "--device", "cpu", "--port", str(args.port), "-t", str(args.threads),
         "-c", "8192"],
        args.port, None, args.max_tokens,
    )
    llama_cmd = [
        llama_server, "-m", args.model, "--host", "127.0.0.1", "--port", str(args.port + 1),
        "-t", str(args.threads), "-c", "8192", "-ngl", "0", "-fa", "on", "-np", "1",
        "--temp", "0", "--top-k", "1", "--repeat-penalty", "1.0", "--spec-type", args.llama_spec,
    ]
    l_rate, l_text = serve_and_measure(llama_cmd, args.port + 1, cpu_only_env(), args.max_tokens)
    return (k_rate, l_rate), k_text == l_text, " ".join(
        os.path.basename(c) if i == 0 else c for i, c in enumerate(llama_cmd)
    )


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", help="the .gguf file both engines run")
    p.add_argument("--llama-dir", required=True, help="folder with llama-bench and llama-server")
    p.add_argument("--kinetic", help="the kinetic binary [default: kinetic on PATH]")
    p.add_argument("-t", "--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                   help="CPU threads for both [default: half the logical CPUs]")
    p.add_argument("-r", "--repetitions", type=int, default=3)
    p.add_argument("--max-tokens", type=int, default=512, help="limit for the edit answer")
    p.add_argument("--llama-spec", default="ngram-mod",
                   help="llama-server --spec-type; add draft-mtp for models with an MTP block")
    p.add_argument("--port", type=int, default=8181, help="Kinetic's port; llama-server takes the next one")
    p.add_argument("--skip-edit", action="store_true", help="only the plain llama-bench tests")
    args = p.parse_args()

    kinetic = args.kinetic or tool(None, "kinetic")
    version = subprocess.run([kinetic, "--version"], capture_output=True, text=True).stdout.strip()
    rates, bench_cmd = plain(args, kinetic, tool(args.llama_dir, "llama-bench"))
    rows = [
        (f"prompt {PROMPT}, tok/s", *rates["prompt"]),
        (f"generate {GENERATE}, tok/s", *rates["generate"]),
    ]
    notes = [f"llama.cpp plain: `{bench_cmd}`"]
    if not args.skip_edit:
        (k, l), same, server_cmd = edit(args, kinetic, tool(args.llama_dir, "llama-server"))
        rows.append(("edit, speculative, tok/s", k, l))
        notes.append(f"llama.cpp edit: `{server_cmd}`")
        notes.append(f"edit answers identical: {'yes' if same else 'no'}")

    print(f"{os.path.basename(args.model)}, CPU, {args.threads} threads, plain tests best of {args.repetitions}, {version}\n")
    print("| Test | Kinetic | llama.cpp | Kinetic / llama.cpp |")
    print("|---|---:|---:|---:|")
    for name, k, l in rows:
        ratio = f"{k / l:.2f}x" if l else "n/a"
        print(f"| {name} | {k:.1f} | {l:.1f} | {ratio} |")
    print()
    for note in notes:
        print(f"- {note}")


if __name__ == "__main__":
    main()
