"""tools/maya_quant/zs_fp8.py - the zero-shot requests (zs_tasks.py) scored by the official FP8 model: the same
layer-by-layer pass as calib.py (one layer on the GPU at a time, the hidden streams on disk between layers), the
requests sorted by length and grouped into right-padded batches (causal attention: a padding token only follows the
request's own tokens, so it changes none of them).  The output has zs_engine.py's form, so zs_tasks.py --score reads
both and the comparison is paired.  Resumable at the first layer not yet done.

    python zs_fp8.py --fp8 DIR --reqs zs.jsonl --work DIR --out zs_fp8.jsonl [--tokens 16384]
    python zs_tasks.py --score zs.jsonl --logp zs_fp8.jsonl
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from calib import StatMoE, load_layer  # noqa: E402
from hf_map import Checkpoint, P  # noqa: E402

torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
torch.backends.cuda.matmul.allow_tf32 = False


def batches(reqs, budget):
    """Requests by length, cut into batches of at most `budget` padded tokens: [(request indices, padded length)]."""
    order = sorted(range(len(reqs)), key=lambda i: (len(reqs[i]["ids"]), i))
    out, cur, tb = [], [], 0
    for i in order:
        t = len(reqs[i]["ids"])
        if cur and (len(cur) + 1) * max(tb, t) > budget:
            out.append((cur, tb))
            cur, tb = [], 0
        cur.append(i)
        tb = max(tb, t)
    if cur:
        out.append((cur, tb))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fp8", required=True)
    ap.add_argument("--reqs", required=True)
    ap.add_argument("--work", required=True, help="the streams between layers and the resume state")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokens", type=int, default=16384, help="padded tokens per batch")
    a = ap.parse_args()
    from transformers import AutoConfig
    dev = torch.device("cuda")
    ck = Checkpoint(a.fp8)
    cfg = AutoConfig.from_pretrained(a.fp8).text_config
    cfg._attn_implementation = "sdpa"
    work = pathlib.Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    reqs = [json.loads(l) for l in open(a.reqs, encoding="utf-8")]
    bs = batches(reqs, a.tokens)
    offs = np.cumsum([0] + [len(r) * tb for r, tb in bs])
    H, HC, n_layers = int(cfg.hidden_size), int(cfg.hc_mult), int(cfg.num_hidden_layers)
    shape = (int(offs[-1]), HC, H)
    print(f"{len(reqs)} requests in {len(bs)} batches, {shape[0]} padded tokens "
          f"({sum(len(r['ids']) for r in reqs)} real)", flush=True)
    bufs = [work / "streams_a.bin", work / "streams_b.bin"]
    mm = [np.memmap(b, dtype=np.uint16, mode="r+" if b.exists() else "w+", shape=shape) for b in bufs]
    state_f, tp_file = work / "state.json", work / "topk_prev.pt"
    first = json.load(open(state_f))["next_layer"] if state_f.exists() else 0
    topk_prev = torch.load(tp_file) if first > 0 and tp_file.exists() else {}

    def padded(ix, tb):
        return np.array([reqs[i]["ids"] + [reqs[i]["ids"][-1]] * (tb - len(reqs[i]["ids"])) for i in ix], np.int64)

    if first == 0:
        emb = ck.get(P + "embed_tokens.weight")
        for b, (ix, tb) in enumerate(bs):
            e = emb[torch.from_numpy(padded(ix, tb).reshape(-1))].to(torch.bfloat16)        # [B*T, H]
            mm[0][offs[b]:offs[b + 1]] = e.unsqueeze(1).expand(-1, HC, H).contiguous().view(torch.uint16).numpy()
        mm[0].flush()
        del emb
    for il in range(first, n_layers):
        t0 = time.time()
        src, dst = mm[il % 2], mm[(il + 1) % 2]
        layer = load_layer(ck, cfg, il, dev)
        moe = StatMoE(ck, cfg, il, dev) if ck.is_moe(il) else None
        if moe is not None:
            moe.collect = False
        t_load = time.time() - t0
        new_topk = {}
        with torch.no_grad():
            for b, (ix, tb) in enumerate(bs):
                B = len(ix)
                h = torch.from_numpy(np.asarray(src[offs[b]:offs[b + 1]])).view(torch.bfloat16).to(dev).float()
                h = h.view(B, tb, HC, H)
                # Glm5NextTextDecoderLayer.forward, as calib.py runs it - the attention half in sub-batches (the KDA
                # chunk kernel's decay mask grows with sequences x 64-token chunks: 780 short ones asked for 97 GB)
                sb = max(1, 24 // ((tb + 63) // 64))
                prev = topk_prev.get(b)
                xs, posts, combs, ress, tks = [], [], [], [], []
                for s0 in range(0, B, sb):
                    hs = h[s0:s0 + sb]
                    n = hs.shape[0]
                    pos = torch.arange(tb, device=dev).unsqueeze(0).expand(n, tb)
                    mask = torch.ones(n, tb, dtype=torch.bool, device=dev)
                    residual = hs
                    post, comb, x = layer.attn_hc(hs)
                    x = layer.input_layernorm(x)
                    if layer.block_type == "linear_attention":
                        x = layer.self_attn(hidden_states=x, cache_params=None, attention_mask=mask)
                    else:
                        pv = prev[s0:s0 + n].to(dev) if prev is not None else None
                        x, _, tk = layer.self_attn(hidden_states=x, attention_mask=mask, position_ids=pos,
                                                  past_key_values=None, use_cache=False, position_embeddings=None,
                                                  prev_topk_indices=pv)
                        if tk is not None:
                            tks.append(tk)
                    hs = post.unsqueeze(-1) * x.unsqueeze(-2) + torch.matmul(comb.transpose(-1, -2), residual)
                    post, comb, x = layer.ffn_hc(hs)
                    xs.append(layer.post_attention_layernorm(x))
                    posts.append(post)
                    combs.append(comb)
                    ress.append(hs)
                if tks:   # [B, T, 2051]: past the last selectable column every entry is -1 (none)
                    tk = torch.cat(tks, 0)
                    w = int((tk >= 0).any(0).any(0).nonzero().max()) + 1 if bool((tk >= 0).any()) else 1
                    new_topk[b] = tk[..., :w].cpu()
                x, post, comb, residual = torch.cat(xs, 0), torch.cat(posts, 0), torch.cat(combs, 0), torch.cat(ress, 0)
                del xs, posts, combs, ress, tks
                y = moe(x) if moe is not None else layer.mlp(x)
                h = post.unsqueeze(-1) * y.unsqueeze(-2) + torch.matmul(comb.transpose(-1, -2), residual)
                dst[offs[b]:offs[b + 1]] = h.reshape(-1, HC, H).to(torch.bfloat16).view(torch.uint16).cpu().numpy()
        dst.flush()
        if new_topk:
            topk_prev.update(new_topk)
            torch.save(topk_prev, tp_file)
        json.dump({"next_layer": il + 1}, open(state_f, "w"))
        del layer, moe
        torch.cuda.empty_cache()
        print(f"layer {il:2d}: {time.time() - t0:6.1f} s (load {t_load:.1f} s)", flush=True)
    score(ck, cfg, mm[n_layers % 2], reqs, bs, offs, HC, H, a.out, dev)


def score(ck, cfg, streams, reqs, bs, offs, HC, H, out, dev):
    """Each request's continuation: the hc head (mean of the streams), the final norm, lm_head, log-softmax at the
    positions that predict its tokens from n_ctx on."""
    norm_w = ck.get(P + "norm.weight").to(dev)
    eps = float(cfg.rms_norm_eps)
    lm = ck.get("lm_head.weight").to(dev, torch.float16)
    with open(out, "w", encoding="utf-8") as fo, torch.no_grad():
        for b, (ix, tb) in enumerate(bs):
            hb = torch.from_numpy(np.asarray(streams[offs[b]:offs[b + 1]])).view(torch.bfloat16).view(len(ix), tb, HC, H)
            for k, i in enumerate(ix):
                r = reqs[i]
                ids, c = r["ids"], r["n_ctx"]
                h = hb[k, c - 1:len(ids) - 1].to(dev).float().mean(1)                        # [n, H]
                h = h * torch.rsqrt(h.square().mean(-1, keepdim=True) + eps) * norm_w
                lg = (h.half() @ lm.t()).float()
                tgt = torch.tensor(ids[c:], device=dev)
                lp = (lg.gather(1, tgt[:, None])[:, 0] - torch.logsumexp(lg, -1)).sum().item()
                greedy = bool((lg.argmax(-1) == tgt).all().item())
                fo.write(json.dumps({"task": r["task"], "item": r["item"], "choice": r["choice"], "logp": lp,
                                     "n": len(ids) - c, "greedy": int(greedy)}) + "\n")
    print(f"scored {len(reqs)} requests -> {out}", flush=True)


if __name__ == "__main__":
    main()
