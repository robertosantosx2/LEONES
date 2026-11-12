#!/usr/bin/env python3
"""W1: GSM8K-200 (first N test questions, zero-shot chat). Reports accuracy and generation tok/s.
Concurrency C > 1 reports total throughput as C * sum(tokens) / sum(per-request generation time).
    w1_gsm8k.py --port 9000 --model X --n 200 --conc 1 --max-tokens 2048 --out results/<tag>.w1.json
"""
import argparse, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from common import stream_chat

PROMPT = ("Solve the problem step by step. End your answer with a line 'Final answer: <number>'.\n\n{q}")


def last_number(text):
    tail = text.split("Final answer:")[-1] if "Final answer:" in text else text
    nums = re.findall(r"-?\d[\d,]*\.?\d*", tail)
    return nums[-1].replace(",", "").rstrip(".") if nums else None


def same(a, b):
    try:
        return a is not None and abs(float(a) - float(b)) < 1e-6
    except ValueError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--model", default="m")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--conc", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "data", "gsm8k_test.jsonl"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = [json.loads(l) for l in open(a.data)][:a.n]

    def run(it):
        m, text = stream_chat(a.port, a.model, [{"role": "user", "content": PROMPT.format(q=it["question"])}],
                              a.max_tokens, extra={"ignore_eos": False})
        gold = it["answer"].split("####")[-1].strip().replace(",", "")
        m["correct"] = same(last_number(text), gold)
        return m

    with ThreadPoolExecutor(a.conc) as ex:
        rows = list(ex.map(run, items))
    tok = sum(r["completion_tokens"] - 1 for r in rows)
    gen = sum(r["gen_s"] for r in rows)
    summ = {"n": len(rows), "correct": sum(r["correct"] for r in rows), "conc": a.conc,
            "gen_tok_s": a.conc * tok / gen if gen else 0.0, "completion_tokens": tok,
            "ttft_median_s": sorted(r["ttft_s"] for r in rows)[len(rows) // 2]}
    json.dump({"summary": summ, "rows": rows}, open(a.out, "w"), indent=1)
    print("W1 " + " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in summ.items()))


if __name__ == "__main__":
    main()
