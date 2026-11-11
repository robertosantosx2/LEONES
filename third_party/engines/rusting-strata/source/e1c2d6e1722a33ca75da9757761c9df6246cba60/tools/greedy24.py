# Greedy gate: strata and llama-server produce the same greedy continuation of one prompt.
# Usage: python -I tools/greedy24.py <model.gguf> [--extra=--gpu] [--port 8199] [--bin target/release/rustingstrata]
# Needs llama-server running on --port with the same model. Exit status 0 = identical.
import argparse
import json
import subprocess
import sys
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("--extra", default="")
ap.add_argument("--port", type=int, default=8199)
ap.add_argument("--bin", default="target/release/rustingstrata")
ap.add_argument("--prompt", default="The capital of France is")
ap.add_argument("-n", type=int, default=24)
a = ap.parse_args()
body = {
    "prompt": a.prompt,
    "n_predict": a.n,
    "temperature": 0,
    "top_k": 1,
    "cache_prompt": False,
}
r = urllib.request.Request(
    f"http://127.0.0.1:{a.port}/completion",
    json.dumps(body).encode(),
    {"Content-Type": "application/json"},
)
want = json.load(urllib.request.urlopen(r))["content"]
got = subprocess.run(
    [
        a.bin,
        "generate",
        "--model",
        a.model,
        "--prompt",
        a.prompt,
        "-n",
        str(a.n),
        *a.extra.split(),
    ],
    capture_output=True,
    text=True,
    check=True,
).stdout
print("llama.cpp:", repr(want))
print("strata:   ", repr(got))
sys.exit(0 if want and want in got else 1)
