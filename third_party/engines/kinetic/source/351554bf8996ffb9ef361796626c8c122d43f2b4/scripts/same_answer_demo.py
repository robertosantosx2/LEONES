"""Same input, same output, every time: one chat request sent ten times,
sampled at temperature 0.8 with a fixed seed, while three other clients keep
the server busy with different long requests.

Starts `kinetic serve --parallel 4` (or uses a running server) and, if given,
llama.cpp's `llama-server --parallel 4` on the same GGUF, and prints, for
each server, every run's first 40 characters and the hash of its full
answer. Standard library only.

    python scripts/same_answer_demo.py --model model.gguf --kinetic target/release/kinetic
    python scripts/same_answer_demo.py --model model.gguf --kinetic-url http://127.0.0.1:8080 \
        --llama-server path/to/llama-server
"""

import argparse
import hashlib
import json
import random
import subprocess
import sys
import threading
import time
import urllib.request

RUNS = 10
LOADERS = 3
QUESTION = "Invent a name for a coffee shop on the Moon and say why it fits, in two sentences."
SAMPLING = {"temperature": 0.8, "top_p": 0.95, "top_k": 40, "seed": 1234, "max_tokens": 64}
# both servers answer directly rather than reasoning first
NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}
TOPICS = [
    "a lighthouse keeper who collects clocks",
    "the history of the bicycle",
    "how bridges carry load",
    "a city where it always rains",
    "the life of a honeybee",
    "a chess match that lasted a week",
]


def post(url, body, timeout=600):
    req = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def wait_ready(url, proc, seconds=300):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            sys.exit(f"the server at {url} exited with code {proc.returncode}")
        try:
            with urllib.request.urlopen(url + "/health", timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    sys.exit(f"{url} did not become ready")


def load(url, stop):
    rng = random.Random()
    while not stop.is_set():
        topic = rng.choice(TOPICS)
        body = {
            "messages": [{"role": "user", "content": f"Write a long essay about {topic}."}],
            "temperature": 0.8,
            "seed": rng.randrange(1 << 31),
            "max_tokens": 256,
            **NO_THINKING,
        }
        try:
            post(url, body)
        except OSError:
            time.sleep(0.5)


def answers(url, receipt=None):
    stop = threading.Event()
    loaders = [threading.Thread(target=load, args=(url, stop), daemon=True) for _ in range(LOADERS)]
    for t in loaders:
        t.start()
    time.sleep(2)  # let the load start before the first measured request
    out = []
    try:
        for _ in range(RUNS):
            body = {"messages": [{"role": "user", "content": QUESTION}], **SAMPLING, **NO_THINKING}
            if receipt:
                body["receipt"] = True
            reply = post(url, body)
            message = reply["choices"][0]["message"]
            out.append(message.get("content") or message.get("reasoning_content") or "")
            if receipt:
                with open(receipt, "w", encoding="utf-8") as f:
                    json.dump(reply["receipt"], f, indent=2)
    finally:
        stop.set()
    return out


def table(name, texts):
    print(f"\n{name}")
    print(f"{'run':>3}  {'answer (first 40 characters)':<42}  sha256 of the full answer")
    for i, text in enumerate(texts, 1):
        head = text.strip().replace("\n", " ")[:40]
        print(f"{i:>3}  {head:<42}  {hashlib.sha256(text.encode()).hexdigest()[:16]}")
    distinct = len({hashlib.sha256(t.encode()).digest() for t in texts})
    print(f"     {distinct} distinct answer{'s' if distinct != 1 else ''} in {len(texts)} runs")


def run(name, url, command, receipt=None):
    proc = None
    if command is not None:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_ready(url, proc)
        table(name, answers(url, receipt))
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--model", help="the GGUF both servers load")
    p.add_argument("--kinetic", help="the kinetic executable to start")
    p.add_argument("--kinetic-url", default="http://127.0.0.1:8090")
    p.add_argument("--kinetic-args", default="", help="more flags for kinetic serve, such as '--device cpu'")
    p.add_argument("--receipt", help="save the receipt of Kinetic's last run here")
    p.add_argument("--llama-server", help="llama-server to start and compare with")
    p.add_argument("--llama-url", default="http://127.0.0.1:8091")
    p.add_argument("--llama-args", default="", help="more flags for llama-server, such as '-ngl 0'")
    a = p.parse_args()
    if (a.kinetic or a.llama_server) and not a.model:
        p.error("--model is needed to start a server")

    print(f"Question: {QUESTION}")
    print(f"Sampling: {json.dumps(SAMPLING)}; {LOADERS} other clients send long requests meanwhile")
    port = lambda url: url.rsplit(":", 1)[1]
    kinetic = None
    if a.kinetic:
        kinetic = [a.kinetic, "serve", a.model, "--parallel", "4", "--port", port(a.kinetic_url)]
        kinetic += a.kinetic_args.split()
    run("Kinetic, kinetic serve --parallel 4", a.kinetic_url, kinetic, a.receipt)
    if a.receipt:
        print(f"     receipt of the last run: {a.receipt}; check it with kinetic verify-receipt")
    if a.llama_server:
        llama = [a.llama_server, "-m", a.model, "--parallel", "4", "--port", port(a.llama_url)]
        llama += a.llama_args.split()
        run("llama.cpp, llama-server --parallel 4", a.llama_url, llama)


if __name__ == "__main__":
    main()
