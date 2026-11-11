"""tools/maya_quant/zs_tasks.py - the zero-shot multiple-choice suite (ARC-Easy, ARC-Challenge, HellaSwag, WinoGrande,
PIQA) as scoring requests, the way lm-evaluation-harness builds them: one (context, continuation) per choice, the
answer the choice with the highest summed log-likelihood (acc) or the highest per byte of the continuation (acc_norm).
The same fixed subset of every task goes to the FP8 model (zs_fp8.py) and to a quant (the engine's LOGP), so the
comparison is paired.

    python zs_tasks.py --data /mnt/nvme/maya/evaldata --tok tokenizer.json --out zs.jsonl [--n 400] [--seed 1234]
    python zs_tasks.py --score zs.jsonl --logp results.jsonl            # accuracy from the scored requests
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

PREFIX = "[gMASK]<sop>"   # GLM's start of a document: both models read the same first tokens


def hs_pre(text: str) -> str:
    text = text.strip().replace(" [title]", ". ")
    text = re.sub("\\[.*?\\]", "", text)
    return text.replace("  ", " ")


def load(data: Path):
    import pyarrow.parquet as pq
    tasks = {}
    for name, fn in (("arc_easy", "arc_easy_test.parquet"), ("arc_challenge", "arc_challenge_test.parquet")):
        items = []
        for r in pq.read_table(data / fn).to_pylist():
            labels, texts = list(r["choices"]["label"]), list(r["choices"]["text"])
            if r["answerKey"] not in labels:
                continue
            items.append({"ctx": [f"Question: {r['question']}\nAnswer:"] * len(texts), "cont": [" " + t for t in texts],
                          "gold": labels.index(r["answerKey"])})
        tasks[name] = items
    items = []
    for r in pq.read_table(data / "hellaswag_validation.parquet").to_pylist():
        ctx = hs_pre(r["activity_label"] + ": " + r["ctx_a"] + " " + r["ctx_b"].capitalize())
        ends = [hs_pre(e) for e in r["endings"]]
        items.append({"ctx": [ctx] * len(ends), "cont": [" " + e for e in ends], "gold": int(r["label"])})
    tasks["hellaswag"] = items
    items = []
    for r in pq.read_table(data / "winogrande_xl_validation.parquet").to_pylist():
        s = r["sentence"]
        i = s.index("_")
        cont = " " + s[i + 1:].strip()
        items.append({"ctx": [s[:i] + r["option1"], s[:i] + r["option2"]], "cont": [cont, cont],
                      "gold": int(r["answer"]) - 1})
    tasks["winogrande"] = items
    items = []
    for r in pq.read_table(data / "piqa_validation.parquet").to_pylist():
        q = f"Question: {r['goal']}\nAnswer:"
        items.append({"ctx": [q, q], "cont": [" " + r["sol1"], " " + r["sol2"]], "gold": int(r["label"])})
    tasks["piqa"] = items
    return tasks


def build(a):
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tok)
    enc = lambda s: tok.encode(s, add_special_tokens=False).ids
    rng = random.Random(a.seed)
    n_req = 0
    with open(a.out, "w", encoding="utf-8") as fo:
        for task, items in load(Path(a.data)).items():
            idx = list(range(len(items)))
            rng.shuffle(idx)
            for k in sorted(idx[: a.n]):
                it = items[k]
                for c, (ctx, cont) in enumerate(zip(it["ctx"], it["cont"])):
                    whole, cids = enc(PREFIX + ctx + cont), enc(PREFIX + ctx)
                    if whole[: len(cids)] != cids:   # the tokenizer merged across the boundary: split on the text
                        cids = enc(PREFIX + ctx)
                        whole = cids + enc(cont)
                    fo.write(json.dumps({"task": task, "item": k, "choice": c, "gold": it["gold"],
                                         "n_ctx": len(cids), "ids": whole,
                                         "cont_bytes": len(cont.encode("utf-8"))}) + "\n")
                    n_req += 1
    print(f"{a.out}: {n_req} requests")


def score(a):
    reqs = [json.loads(l) for l in open(a.score, encoding="utf-8")]
    logp = {}
    for l in open(a.logp, encoding="utf-8"):
        r = json.loads(l)
        logp[(r["task"], r["item"], r["choice"])] = r["logp"]
    per = {}
    for r in reqs:
        key = (r["task"], r["item"])
        per.setdefault(key, {"gold": r["gold"], "lp": {}, "bytes": {}})
        lp = logp.get((r["task"], r["item"], r["choice"]))
        if lp is not None:
            per[key]["lp"][r["choice"]] = lp
            per[key]["bytes"][r["choice"]] = r["cont_bytes"]
    out = {}
    for (task, _), v in per.items():
        if not v["lp"]:
            continue
        acc = max(v["lp"], key=v["lp"].get) == v["gold"]
        norm = max(v["lp"], key=lambda c: v["lp"][c] / max(1, v["bytes"][c])) == v["gold"]
        t = out.setdefault(task, [0, 0, 0])
        t[0] += acc
        t[1] += norm
        t[2] += 1
    print(json.dumps({k: {"acc": round(100 * v[0] / v[2], 2), "acc_norm": round(100 * v[1] / v[2], 2), "n": v[2]}
                      for k, v in sorted(out.items())}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    ap.add_argument("--tok")
    ap.add_argument("--out")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--score")
    ap.add_argument("--logp")
    a = ap.parse_args()
    if a.score:
        score(a)
    else:
        build(a)


if __name__ == "__main__":
    main()
