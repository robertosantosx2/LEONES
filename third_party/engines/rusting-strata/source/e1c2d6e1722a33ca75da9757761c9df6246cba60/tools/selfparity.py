# Usage: python -I tools/selfparity.py  (needs llama-server on port 8199, ~1 h with --n-cpu-moe 20)
# llama.cpp against itself: argmax at every continuation position with the context run as one prompt batch
# (cache_prompt off), versus the token-by-token reference in target/parity-ref.json. Also vs strata GPU runs.
import glob
import json
import pathlib
import urllib.error
import urllib.request

root = pathlib.Path(__file__).resolve().parent.parent
prompts = json.load(open(root / "tools/prompts.json"))[:20]
ref = json.load(open(root / "target/parity-ref.json"))


def post(body):
    r = urllib.request.Request(
        "http://127.0.0.1:8199/completion",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(r))


batch = []
for i, p in enumerate(prompts):
    ids, cont = ref[p]["ids"], ref[p]["cont"][:32]
    row = []
    for j in range(len(cont)):
        try:
            r = post(
                {
                    "prompt": ids + cont[:j],
                    "n_predict": 1,
                    "temperature": 0,
                    "top_k": 1,
                    "cache_prompt": False,
                    "return_tokens": True,
                }
            )
            row.append(r["tokens"][0] if r.get("tokens") else -1)
        except (
            urllib.error.HTTPError
        ):  # server's output-format check rejects some special tokens
            row.append(-1)
    batch.append(row)
    print(i, sum(a == b for a, b in zip(row, cont)), "/", len(cont), flush=True)
json.dump(batch, open(root / "target/llama-batch-argmax.json", "w"))
tot = sum(x >= 0 for r in batch for x in r)
print("positions llama-server refused:", sum(x < 0 for r in batch for x in r))
print(
    "llama batch vs llama token-by-token ref:",
    sum(
        a == b
        for i, r in enumerate(batch)
        for a, b in zip(r, ref[prompts[i]]["cont"])
        if a >= 0
    ),
    "/",
    tot,
)
for f in sorted(glob.glob(str(root / "target/parity-result-gpu-*-r*.json"))):
    rows = json.load(open(f))["rows"]
    print(
        pathlib.Path(f).name,
        "vs llama batch:",
        sum(
            a == b
            for i, r in enumerate(rows)
            for a, b in zip(r["argmax"], batch[i])
            if b >= 0
        ),
        "/",
        tot,
    )
