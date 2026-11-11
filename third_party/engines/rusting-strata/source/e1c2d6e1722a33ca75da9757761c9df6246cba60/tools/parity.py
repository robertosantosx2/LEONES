# M1 parity gate: llama.cpp greedy continuations, teacher-forced through `strata score`.
# Usage: python -I tools/parity.py <model.gguf> [--n 32] [--limit 20] [--port 8199] [--bin target/release/rustingstrata] [--ref target/parity-ref.json]
#        [--extra "--gpu"] [--tag gpu]  (result goes to target/parity-result[-tag].json)
# Phase 1 needs llama-server running on --port (e.g. ~/Clones/llama.cpp/build/bin/llama-server -m M --port 8199);
# its outputs are cached in target/parity-ref.json so phase 2 can run without it.
import argparse
import json
import pathlib
import subprocess
import sys
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("--n", type=int, default=32)
ap.add_argument("--limit", type=int, default=20)
ap.add_argument("--port", type=int, default=8199)
ap.add_argument("--bin", default="target/release/rustingstrata")
ap.add_argument("--extra", default="")
ap.add_argument("--tag", default="")
ap.add_argument(
    "--ref",
    default="target/parity-ref.json",
    help="reference cache (per llama.cpp build)",
)
ap.add_argument(
    "--alt",
    default="target/llama-batch-argmax.json",
    help="llama.cpp argmax with the context run as one batch (tools/selfparity.py); the v1 gate counts a "
    "token if it matches either llama.cpp mode",
)
ap.add_argument(
    "--start", type=int, default=0, help="score only prompts from this index (resume)"
)
ap.add_argument(
    "--no-think",
    action="store_true",
    help="drop the empty think block (models without thinking, e.g. *-Instruct-2507)",
)
a = ap.parse_args()
root = pathlib.Path(__file__).resolve().parent.parent
cache = root / a.ref


def post(path, body):
    r = urllib.request.Request(
        f"http://127.0.0.1:{a.port}{path}",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(r))


prompts = json.load(open(root / "tools/prompts.json"))[: a.limit]
if a.no_think:
    prompts = [p.replace("<think>\n\n</think>\n\n", "") for p in prompts]
ref = json.load(open(cache)) if cache.exists() else {}
for p in prompts:
    if p in ref and len(ref[p]["cont"]) >= a.n:
        continue
    ids = post(
        "/tokenize", {"content": p, "add_special": False, "parse_special": True}
    )["tokens"]
    r = post(
        "/completion",
        {
            "prompt": ids,
            "n_predict": a.n,
            "temperature": 0,
            "top_k": 1,
            "cache_prompt": False,
            "return_tokens": True,
        },
    )
    ref[p] = {"ids": ids, "cont": r["tokens"]}
    json.dump(ref, open(cache, "w"))
    print("ref", len(ids), "prompt tokens ->", len(r["tokens"]), flush=True)

alt = json.load(open(root / a.alt)) if (root / a.alt).exists() else None
agree = either = total = 0
rows = []
for pi, p in enumerate(prompts[a.start :], a.start):
    ids, cont = ref[p]["ids"], ref[p]["cont"][: a.n]
    out = subprocess.run(
        [
            str(root / a.bin),
            "score",
            "--model",
            a.model,
            "--input",
            "-",
            *a.extra.split(),
        ],
        input=json.dumps({"prompt": ids, "continuation": cont}),
        capture_output=True,
        text=True,
    )
    if out.returncode:
        sys.exit(
            f"strata score failed on {p.splitlines()[1][:50]!r}:\n{out.stderr[-2000:]}"
        )
    res = json.loads(out.stdout)
    mine = res["argmax"]
    k = sum(x == y for x, y in zip(mine, cont))
    # First disagreement and our top-2 logprob gap there (small gap = near-tie).
    bad = next((i for i, (x, y) in enumerate(zip(mine, cont)) if x != y), None)
    gap = (
        None
        if bad is None
        else round(res["top5"][bad][0][1] - res["top5"][bad][1][1], 4)
    )
    e = sum(
        x == y or (alt is not None and x == alt[pi][i])
        for i, (x, y) in enumerate(zip(mine, cont))
    )
    agree += k
    either += e
    total += len(cont)
    rows.append(
        {
            "prompt": p.split("\n")[1][:50],
            "prompt_tokens": len(ids),
            "agree": k,
            "n": len(cont),
            "first_miss": bad,
            "top2_gap_at_miss": gap,
            "argmax": mine,
            # Top-5 (token, logprob) pairs per position. target/ only, never committed: the
            # cross-backend report needs each backend's top-5 gap at a divergent position
            # (tools/consistency.py, M2-T7).
            "top5": res["top5"],
        }
    )
    print({k: v for k, v in rows[-1].items() if k not in ("argmax", "top5")}, flush=True)
pct = 100 * agree / total
print(f"TOP1 AGREEMENT {agree}/{total} = {pct:.2f}%")
if alt is not None:
    print(f"EITHER LLAMA MODE {either}/{total} = {100 * either / total:.2f}% (v1 gate)")
json.dump(
    {"rows": rows, "agree": agree, "either": either if alt else None, "total": total},
    open(root / f"target/parity-result{'-' + a.tag if a.tag else ''}.json", "w"),
    indent=1,
)
sys.exit(0 if (either if alt else agree) >= 0.99 * total else 1)
