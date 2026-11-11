"""Compares Kinetic's llama-server API with llama-server's own.

Starts both servers on the same GGUF with the same llama.cpp flags (or uses
running ones), sends each the same requests, and lists every JSON key and
type that differs. Standard library only.

    python scripts/llama_server_compat.py --model model.gguf \
        --llama-server path/to/llama-server --kinetic path/to/kinetic
    python scripts/llama_server_compat.py --oracle-url http://127.0.0.1:8080 \
        --kinetic-url http://127.0.0.1:8081
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROMPT = "The capital of France is"
GREEDY = {"temperature": 0, "top_k": 1, "repeat_penalty": 1.0}

REQUESTS = [
    ("GET", "/health", None),
    ("GET", "/props", None),
    ("GET", "/slots", None),
    ("POST", "/tokenize", {"content": "Hello world"}),
    ("POST", "/tokenize", {"content": "Hello world", "with_pieces": True}),
    ("POST", "/tokenize", {"content": "Hello world", "add_special": True}),
    ("POST", "/detokenize", None),  # the ids the oracle gave for "Hello world"
    ("POST", "/completion", {"prompt": PROMPT, "n_predict": 8, **GREEDY}),
    ("POST", "/completions", {"prompt": PROMPT, "n_predict": 8, **GREEDY}),
    ("POST", "/completion", {"prompt": PROMPT, "n_predict": 4, "stream": True, **GREEDY}),
    ("POST", "/completion", {"prompt": "1, 2, 3,", "n_predict": 16, "stop": [" 5"], **GREEDY}),
    (
        "POST",
        "/completion",
        {
            "prompt": "Answer in JSON:",
            "n_predict": 24,
            "json_schema": {
                "type": "object",
                "properties": {"a": {"type": "integer"}},
                "required": ["a"],
            },
            **GREEDY,
        },
    ),
    ("POST", "/embedding", {"content": "hello"}),
]

# compared by value, the rest only by key and type
SAME_VALUE = {"content", "tokens", "tokens_predicted", "tokens_evaluated", "stop_type"}


def call(base, method, path, body):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            status, text = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode()
    if body and body.get("stream"):
        events = [line[6:] for line in text.splitlines() if line.startswith("data: ")]
        events = [json.loads(e) for e in events if e != "[DONE]"]
        return status, {"first": events[0], "last": events[-1]} if events else None
    return status, json.loads(text)


def kind(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    return {float: "float", str: "str", type(None): "null", list: "list", dict: "dict"}[type(v)]


def diff(a, b, at, out):
    """Appends to `out` how `b` (Kinetic) differs from `a` (llama-server)."""
    if kind(a) != kind(b):
        if not (kind(a) == "float" and kind(b) == "int"):
            out.append(f"{at}: {kind(a)} in llama-server, {kind(b)} in Kinetic")
        return
    if isinstance(a, dict):
        missing = [k for k in a if k not in b]
        extra = [k for k in b if k not in a]
        if missing:
            out.append(f"{at}: missing {', '.join(missing)}")
        if extra:
            out.append(f"{at}: extra {', '.join(extra)}")
        for k in a:
            if k in b:
                diff(a[k], b[k], f"{at}.{k}", out)
    elif isinstance(a, list) and a and b:
        diff(a[0], b[0], f"{at}[0]", out)
    if at.rsplit(".", 1)[-1] in SAME_VALUE and a != b and not isinstance(a, dict):
        out.append(f"{at}: {json.dumps(a)[:60]} vs {json.dumps(b)[:60]}")


def wait(base, proc):
    for _ in range(300):
        if proc and proc.poll() is not None:
            sys.exit(f"{proc.args[0]} exited with {proc.returncode}")
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    sys.exit(f"{base} did not come up")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--model", help="GGUF to start both servers on")
    p.add_argument("--llama-server", default="llama-server")
    p.add_argument("--kinetic", default="kinetic")
    p.add_argument("--oracle-url", default="http://127.0.0.1:18080")
    p.add_argument("--kinetic-url", default="http://127.0.0.1:18081")
    args = p.parse_args()

    procs = []
    if args.model:
        flags = ["-m", args.model, "-ngl", "0", "-c", "4096", "-t", "4", "-np", "1"]
        for cmd, url in [([args.llama_server], args.oracle_url), ([args.kinetic, "serve"], args.kinetic_url)]:
            port = url.rsplit(":", 1)[1]
            procs.append(
                subprocess.Popen(
                    cmd + flags + ["--port", port],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
    try:
        wait(args.oracle_url, procs[0] if procs else None)
        wait(args.kinetic_url, procs[1] if procs else None)
        report(args.oracle_url, args.kinetic_url)
    finally:
        for proc in procs:
            proc.kill()


def report(oracle, kinetic):
    total = 0
    ids = None
    for method, path, body in REQUESTS:
        if path == "/detokenize":
            body = {"tokens": ids}
        sa, a = call(oracle, method, path, body)
        sb, b = call(kinetic, method, path, body)
        if path == "/tokenize" and ids is None:
            ids = a["tokens"]
        label = f"{method} {path}" + (f" {json.dumps(body)[:70]}" if body else "")
        out = []
        if sa != sb:
            out.append(f"status {sa} in llama-server, {sb} in Kinetic")
        if sa == 200 and sb == 200:
            diff(a, b, "$", out)
        total += len(out)
        print(f"{'same' if not out else str(len(out)) + ' differences'}: {label}")
        for line in out:
            print(f"    {line}")
    print(f"\n{total} differences")


if __name__ == "__main__":
    main()
