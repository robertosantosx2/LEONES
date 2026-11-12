#!/usr/bin/env python3
"""W4: long-context correctness and speed. Per context length, prompts of real text (the docs and sources of a llama.cpp
checkout, --corpus) with two planted code words at given depths; turn 1 asks for the first, turn 2 (same conversation, so the
prompt cache is reused) for the second. Greedy, ignore_eos, fixed max_tokens: decode tok/s at that context, TTFT (prefill)
of turn 1 and of turn 2, and whether each answer (content or reasoning) contains its code word.
    w4_longctx.py --port 9000 --corpus ~/llama.cpp --lengths 16384,32768,65536 --depths 0.1,0.5,0.9 --out results/<tag>.w4.json
"""
import argparse, glob, json, os, random, statistics, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from common import stream_chat

WORDS = ["ultramarine", "quokka", "saxifrage", "zeppelin", "obsidian", "marzipan", "kestrel", "tamarind", "vortex",
         "juniper", "nebula", "halcyon", "cobalt", "ptarmigan", "riviera", "sardonyx", "tundra", "wisteria"]


def corpus(root):
    files = sorted(glob.glob(f"{root}/docs/**/*.md", recursive=True)) + sorted(glob.glob(f"{root}/src/*.cpp"))
    return "\n\n".join(open(f, errors="ignore").read() for f in files)


def tokenize(port, text):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/tokenize", data=json.dumps({"content": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    return len(json.load(urllib.request.urlopen(req, timeout=600))["tokens"])


def haystack(port, text, n_tok, depths, words):
    # characters per token measured on a sample, then trimmed to the target length
    sample = text[:200000]
    cpt = len(sample) / tokenize(port, sample)
    body = text[:int(n_tok * cpt)]
    for d, w in sorted(zip(depths, words), reverse=True):
        at = body.rfind("\n", 0, int(len(body) * d)) + 1
        body = body[:at] + f"\nIMPORTANT NOTE: the code word number {words.index(w) + 1} is \"{w}\".\n" + body[at:]
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--model", default="m")
    ap.add_argument("--lengths", default="16384,32768,65536")
    ap.add_argument("--depths", default="0.1,0.5,0.9", help="depth of code word 1; code word 2 goes at 1 - depth")
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--corpus", required=True, help="a llama.cpp checkout: its docs/**/*.md and src/*.cpp are the text")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    text = corpus(os.path.expanduser(a.corpus))
    rng = random.Random(1)
    rows = []
    for n_tok in [int(x) for x in a.lengths.split(",")]:
        for d in [float(x) for x in a.depths.split(",")]:
            w1, w2 = rng.sample(WORDS, 2)
            words = [w1, w2]
            doc = haystack(a.port, text, n_tok, [d, 1.0 - d], words)
            msgs = [{"role": "user", "content": doc + "\n\nWhat is code word number 1? Answer with the word only."}]
            m1, t1 = stream_chat(a.port, a.model, msgs, a.max_tokens)
            msgs += [{"role": "assistant", "content": t1}, {"role": "user", "content": "What is code word number 2? Answer with the word only."}]
            m2, t2 = stream_chat(a.port, a.model, msgs, a.max_tokens)
            ok1 = w1 in (t1 + m1["reasoning"]).lower()
            ok2 = w2 in (t2 + m2["reasoning"]).lower()
            rows.append({"ctx": n_tok, "depth": d, "prompt_tokens": m1["prompt_tokens"], "ok1": ok1, "ok2": ok2,
                         "ttft1_s": m1["ttft_s"], "ttft2_s": m2["ttft_s"],
                         # from the wall time after the first token (stream chunks can arrive in bursts)
                         "decode_tok_s": (m1["completion_tokens"] - 1) / (m1["wall_s"] - m1["ttft_s"]),
                         "decode2_tok_s": (m2["completion_tokens"] - 1) / (m2["wall_s"] - m2["ttft_s"]),
                         "completion_tokens": [m1["completion_tokens"], m2["completion_tokens"]]})
            r = rows[-1]
            print(f"ctx {n_tok} depth {d}: prompt {r['prompt_tokens']} ok {ok1}/{ok2} ttft {r['ttft1_s']:.2f}/{r['ttft2_s']:.2f} s "
                  f"decode {r['decode_tok_s']:.1f}/{r['decode2_tok_s']:.1f} tok/s", flush=True)
    summ = {}
    for n_tok in sorted({r["ctx"] for r in rows}):
        rs = [r for r in rows if r["ctx"] == n_tok]
        summ[n_tok] = {"correct": sum(r["ok1"] + r["ok2"] for r in rs), "of": 2 * len(rs),
                       "ttft1_median_s": statistics.median(r["ttft1_s"] for r in rs),
                       "ttft2_median_s": statistics.median(r["ttft2_s"] for r in rs),
                       "decode_tok_s": statistics.median(r["decode_tok_s"] for r in rs)}
        s = summ[n_tok]
        print(f"W4 ctx={n_tok} correct={s['correct']}/{s['of']} ttft1={s['ttft1_median_s']:.2f} ttft2={s['ttft2_median_s']:.2f} "
              f"decode_tok_s={s['decode_tok_s']:.1f}", flush=True)
    json.dump({"rows": rows, "summary": summ}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
