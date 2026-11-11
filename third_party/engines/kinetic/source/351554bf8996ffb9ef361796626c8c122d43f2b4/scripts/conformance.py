#!/usr/bin/env python3
"""Greedy token agreement between Kinetic and llama.cpp on one GGUF file.

Runs `kinetic serve` and then `llama-server` on the same model, one at a
time, sends each the same raw prompts with greedy sampling and compares
the generated tokens one by one. Where they part, it prints llama.cpp's
two likeliest tokens there; a gap under --tie nats is flagged as a
near-tie, which quantized kernels may break either way. Kinetic's tokens
come from a second run with logprobs, whose text has to match the plain
run's.

    python scripts/conformance.py model.gguf --kinetic target/release/kinetic \\
        --llama path/to/llama.cpp/bin --device cpu

Standard library only. Exits 1 when a prompt parts before --early tokens
without a near-tie.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROMPTS = [
    "The capital of France is",
    "def fibonacci(n):\n    \"\"\"Return the n-th Fibonacci number.\"\"\"\n",
    "Here are three tips for staying focused while working from home:\n1.",
    "Translate to German: The weather is nice today, so we are going for a walk.\nGerman:",
]


def post(url, body):
    req = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def wait_ready(url, proc, seconds=180):
    end = time.time() + seconds
    while time.time() < end:
        if proc.poll() is not None:
            sys.exit(f"server exited early: {' '.join(proc.args)}")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.5)
    proc.kill()
    sys.exit(f"server not ready after {seconds} s: {' '.join(proc.args)}")


class Server:
    def __init__(self, args, health):
        self.proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        wait_ready(health, self.proc)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.proc.kill()
        self.proc.wait()


def kinetic_texts(a):
    port = a.port
    args = [a.kinetic, "serve", a.model, "--port", str(port), "--device", a.device,
            "--parallel", "1", "--no-prompt-cache", "-c", "4096"]
    base = f"http://127.0.0.1:{port}"
    with Server(args, base + "/health"):
        out = []
        for p in PROMPTS:
            body = {"prompt": p, "max_tokens": a.n, "temperature": 0, "top_k": 1,
                    "repeat_penalty": 1.0}
            text = post(base + "/v1/completions", body)["choices"][0]["text"]
            # text alone hides where tokens part: llama.cpp's '#' prefixes a '###'
            r = post(base + "/v1/completions", {**body, "logprobs": 1})
            out.append((text, r["choices"][0]["logprobs"]["tokens"]))
        return out


def llama_runs(a):
    port = a.port + 1
    exe = os.path.join(a.llama, "llama-server" + (".exe" if os.name == "nt" else ""))
    ngl = "0" if a.device == "cpu" else "99"
    args = [exe, "-m", a.model, "--port", str(port), "-ngl", ngl, "-c", "4096",
            "-np", "1", "--no-warmup"] + a.llama_arg
    base = f"http://127.0.0.1:{port}"
    with Server(args, base + "/health"):
        out = []
        for p in PROMPTS:
            r = post(base + "/completion", {
                "prompt": p, "n_predict": a.n, "temperature": 0, "top_k": 1,
                "repeat_penalty": 1.0, "n_probs": 2, "cache_prompt": False,
            })
            out.append(r["completion_probabilities"])
        return out


def logprob(entry):
    # newer servers send logprob, older ones prob
    if "logprob" in entry:
        return entry["logprob"]
    return math.log(max(entry["prob"], 1e-30))


def compare(tokens, steps, tie):
    """Tokens agreed, and at the first difference (position, top two, gap)."""
    for i, step in enumerate(steps):
        if tokens[i:i + 1] == [step["token"]]:
            continue
        # kinetic leaves out the end-of-text token llama.cpp shows as ''
        if i == len(tokens) and not step["token"]:
            continue
        tops = step.get("top_logprobs") or step.get("top_probs") or []
        top = [(t["token"], logprob(t)) for t in tops[:2]]
        gap = top[0][1] - top[1][1] if len(top) == 2 else None
        return i, (i, top, gap, gap is not None and gap < tie, "".join(tokens[i:])[:24])
    return len(steps), None


def self_check():
    tie = {"token": "b", "top_logprobs": [{"token": "b", "logprob": -0.60},
                                          {"token": "c", "logprob": -0.65}]}
    assert compare(["a", "b"], [{"token": "a"}, tie], 0.1) == (2, None)
    agreed, diff = compare(["a", "c"], [{"token": "a"}, tie], 0.1)
    assert agreed == 1 and diff[3] and diff[4] == "c"
    agreed, diff = compare(["bc"], [tie, {"token": "c"}], 0.1)
    assert agreed == 0 and diff[4] == "bc"
    assert compare(["a"], [{"token": "a"}, {"token": ""}], 0.1) == (2, None)


def main():
    self_check()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model")
    ap.add_argument("--kinetic", default="kinetic")
    ap.add_argument("--llama", required=True, help="folder with llama-server")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    ap.add_argument("-n", type=int, default=64, help="tokens per prompt")
    ap.add_argument("--port", type=int, default=18080)
    ap.add_argument("--llama-arg", action="append", default=[],
                    help="extra llama-server argument, e.g. --llama-arg=-ncmoe --llama-arg=12")
    ap.add_argument("--tie", type=float, default=0.1, help="near-tie gap in nats")
    ap.add_argument("--early", type=int, default=16)
    a = ap.parse_args()

    texts = kinetic_texts(a)
    runs = llama_runs(a)
    print(f"{os.path.basename(a.model)} on {a.device}, {a.n} greedy tokens per prompt")
    failed = False
    total = agreed_all = 0
    for k, ((text, tokens), steps) in enumerate(zip(texts, runs)):
        if "".join(tokens) != text:
            print(f"prompt {k + 1}: kinetic text changes with logprobs")
            failed = True
            continue
        agreed, diff = compare(tokens, steps, a.tie)
        total += len(steps)
        agreed_all += agreed
        line = f"prompt {k + 1}: {agreed}/{len(steps)} tokens agree"
        if diff:
            pos, top, gap, tied, kin = diff
            alts = ", ".join(f"{t!r} {lp:.3f}" for t, lp in top)
            kind = "near-tie" if tied else "DIVERGES"
            gap = f"{gap:.3f}" if gap is not None else "?"
            line += f"; {kind} at token {pos}: llama.cpp top two {alts} (gap {gap}), kinetic {kin!r}"
            failed |= not tied and pos < a.early
        print(line)
    print(f"total: {agreed_all}/{total} tokens agree")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
