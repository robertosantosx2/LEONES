"""tools/maya_quant/prep_calib.py - the calibration and evaluation token sequences of the Maya quants.

Every sample is rendered with GLM-5.3-Flash's own chat template (reasoning in reasoning_content, tool calls as
tool_calls, tool results as observations), tokenised, and packed into sequences of --len tokens.  The mix, by
tokens, follows docs/QUANT-PLAN.md: chat, multilingual chat, reasoning traces, web code (three.js / canvas / WebGL
first), other code, tool calls, plus any model-written conversations in --extra (jsonl of {"messages": [...]}).
The evaluation set takes disjoint samples of each source, plus wikitext-2 as plain text.

    python prep_calib.py --tok <fp8 dir> --data /mnt/nvme/maya/calib --out DIR [--n-calib 128] [--n-eval 24] [--len 2048]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re

import numpy as np
import pyarrow.parquet as pq

WEB = re.compile(r"three\.js|THREE\.|<canvas|requestAnimationFrame|WebGL|getContext\(|gl_FragColor|shader|"
                 r"@keyframes|animation:|svg", re.I)


def ultrachat(d):
    t = pq.read_table(d / "HuggingFaceH4/ultrachat_200k/data/test_sft-00000-of-00001-f7dfac4afe5b93f4.parquet")
    for row in t.column("messages").to_pylist():
        yield {"messages": [{"role": m["role"], "content": m["content"]} for m in row]}


def oasst(d):
    t = pq.read_table(d / "OpenAssistant/oasst2/data/train-00000-of-00001-88ba0162028a73fc.parquet",
                      columns=["message_id", "parent_id", "text", "role", "lang", "rank"]).to_pylist()
    kids = {}
    for m in t:
        kids.setdefault(m["parent_id"], []).append(m)
    for root in kids.get(None, []):
        conv, cur = [], root
        while cur is not None:
            conv.append({"role": "user" if cur["role"] == "prompter" else "assistant", "content": cur["text"]})
            nxt = [k for k in kids.get(cur["message_id"], [])]
            if not nxt:
                break
            nxt.sort(key=lambda k: (k["rank"] if k["rank"] is not None else 99))
            cur = nxt[0]
        if len(conv) >= 2 and conv[-1]["role"] == "assistant":
            yield {"messages": conv, "lang": root["lang"]}


def openthoughts(d):
    t = pq.read_table(d / "open-thoughts/OpenThoughts-114k/data/train-00005-of-00006.parquet").to_pylist()
    for r in t:
        msgs = [{"role": "system", "content": r["system"]}] if r.get("system") else []
        for c in r["conversations"]:
            v = c["value"]
            if c["from"] == "assistant":
                m = re.search(r"<\|begin_of_thought\|>(.*?)<\|end_of_thought\|>(.*)", v, re.S)
                if m:
                    sol = re.sub(r"<\|(begin|end)_of_solution\|>", "", m.group(2)).strip()
                    msgs.append({"role": "assistant", "reasoning_content": m.group(1).strip(), "content": sol})
                    continue
                msgs.append({"role": "assistant", "content": v})
            else:
                msgs.append({"role": "user", "content": v})
        yield {"messages": msgs}


def magicoder(d):
    for f, q, a in (("ise-uiuc/Magicoder-OSS-Instruct-75K/data-oss_instruct-decontaminated.jsonl", "problem", "solution"),
                    ("ise-uiuc/Magicoder-Evol-Instruct-110K/data-evol_instruct-decontaminated.jsonl", "instruction",
                     "response")):
        p = d / f
        if not p.exists():
            continue
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            yield {"messages": [{"role": "user", "content": r[q]}, {"role": "assistant", "content": r[a]}],
                   "web": bool(WEB.search(r[q] + r[a])) or r.get("lang") in ("javascript", "typescript", "html", "css")}


def stack(d):
    for lang, ext in (("html", "html"), ("css", "css"), ("javascript", "js"), ("typescript", "ts"), ("python", "py")):
        p = next((d / f"bigcode/{s}/data/{lang}/data.json" for s in ("the-stack-smol-xl", "the-stack-smol")
                  if (d / f"bigcode/{s}/data/{lang}/data.json").exists()), None)
        if p is None:
            continue
        txt = open(p, encoding="utf-8").read()
        rows = json.loads(txt) if txt.lstrip().startswith("[") else [json.loads(l) for l in txt.splitlines() if l.strip()]
        for r in rows:
            code = r.get("content", "")
            if not code or len(code) > 60000:
                continue
            ask = f"Write the {lang} file for this project." if lang != "html" else "Write the complete web page."
            yield {"messages": [{"role": "user", "content": ask},
                                {"role": "assistant", "content": f"```{ext}\n{code}\n```"}],
                   "web": lang != "python" and bool(WEB.search(code)) or lang in ("html",)}


def commitpack(d):
    """Code edits: the file before and the commit's subject, answered with the file after."""
    for lang in ("javascript", "html", "typescript", "css"):
        p = d / f"bigcode/commitpackft/data/{lang}/data.jsonl"
        if not p.exists():
            continue
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            old, new = r.get("old_contents", ""), r.get("new_contents", "")
            if not new or len(old) + len(new) > 40000:
                continue
            ask = (f"{r.get('subject') or r.get('message', '')}\n\n```{lang}\n{old}\n```" if old
                   else f"{r.get('subject') or r.get('message', '')} ({r.get('new_file', lang)})")
            yield {"messages": [{"role": "user", "content": ask},
                                {"role": "assistant", "content": f"```{lang}\n{new}\n```"}],
                   "web": True}


def glaive(d):
    rows = json.load(open(d / "glaiveai/glaive-function-calling-v2/glaive-function-calling-v2.json", encoding="utf-8"))
    for r in rows:
        tools = []
        for m in re.finditer(r"\{.*?\}\s*(?=\{|\Z)", r["system"].split("-", 1)[-1], re.S):
            try:
                tools.append({"type": "function", "function": json.loads(m.group(0))})
            except json.JSONDecodeError:
                pass
        if not tools:
            continue
        msgs = []
        bits = re.split(r"(USER:|ASSISTANT:|FUNCTION RESPONSE:)", r["chat"])
        for tag, body in zip(bits[1::2], bits[2::2]):
            body = body.replace("<|endoftext|>", "").strip()
            if tag == "USER:":
                msgs.append({"role": "user", "content": body})
            elif tag == "FUNCTION RESPONSE:":
                msgs.append({"role": "tool", "content": body})
            elif body.startswith("<functioncall>"):
                try:
                    call = json.loads(body[len("<functioncall>"):].strip().replace("'{", "{").replace("}'", "}"))
                    args = call.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    msgs.append({"role": "assistant", "content": "",
                                 "tool_calls": [{"type": "function", "function": {"name": call["name"], "arguments": args}}]})
                except (json.JSONDecodeError, KeyError, TypeError):
                    msgs = []
                    break
            else:
                msgs.append({"role": "assistant", "content": body})
        if len(msgs) >= 2:
            yield {"messages": msgs, "tools": tools}


def extra(paths):
    for p in paths:
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            yield {"messages": r["messages"], "web": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tok", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--n-calib", type=int, default=128)
    ap.add_argument("--n-eval", type=int, default=24)
    ap.add_argument("--len", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=1234)
    a = ap.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tok)
    d = pathlib.Path(a.data)
    rng = random.Random(a.seed)
    T = a.len

    def render(s):
        try:
            text = tok.apply_chat_template(s["messages"], tools=s.get("tools"), tokenize=False,
                                           reasoning_effort="high")
        except Exception:  # noqa: BLE001 - a sample the template refuses is skipped
            return None
        return tok(text, add_special_tokens=False)["input_ids"]

    sources = {
        "chat": list(ultrachat(d)),
        "multilingual": list(oasst(d)),
        "reasoning": list(openthoughts(d)),
        "tools": list(glaive(d)),
    }
    code = list(magicoder(d)) + list(stack(d)) + list(commitpack(d))
    sources["web"] = [s for s in code if s.get("web")] + list(extra(a.extra))
    sources["code"] = [s for s in code if not s.get("web")]
    # Portuguese and the other non-English conversations first in the multilingual share
    sources["multilingual"].sort(key=lambda s: (s.get("lang") == "en", rng.random()))
    share = {"chat": 0.20, "multilingual": 0.12, "reasoning": 0.20, "web": 0.25, "code": 0.10, "tools": 0.13}
    for k, v in sources.items():
        if k != "multilingual":
            rng.shuffle(v)
        print(f"{k:12s} {len(v):7d} samples")

    def pack(n_seq, offset):
        """n_seq sequences of T tokens, each source contributing its share of sequences; samples from `offset` on."""
        seqs, used = [], {}
        for k, frac in share.items():
            want = max(1, round(n_seq * frac))
            buf, i = [], offset
            pool = sources[k]
            while len(seqs) < n_seq and want > 0 and i < len(pool):
                ids = render(pool[i])
                i += 1
                if not ids:
                    continue
                buf.extend(ids)
                while len(buf) >= T and want > 0:
                    seqs.append(buf[:T])
                    buf = buf[T:]
                    want -= 1
            used[k] = i
        return seqs[:n_seq], used

    ev, used = pack(a.n_eval - 4, 0)
    wt = pq.read_table(d / "Salesforce/wikitext/wikitext-2-raw-v1/test-00000-of-00001.parquet").column("text").to_pylist()
    wids = tok("".join(wt), add_special_tokens=False)["input_ids"]
    ev += [wids[i * T:(i + 1) * T] for i in range(4)]
    cal, _ = pack(a.n_calib, max(used.values()) + 1)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "calib.npy", np.array(cal, dtype=np.int32))
    np.save(out / "eval.npy", np.array(ev, dtype=np.int32))
    print(f"calib {len(cal)} x {T}, eval {len(ev)} x {T} -> {out}")


if __name__ == "__main__":
    main()
