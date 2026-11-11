"""tools/maya_quant/calib.py - the reference and statistics pass of the Maya quants (docs/QUANT-PLAN.md, stage 2).

The official GLM-5.3-Flash checkpoint (block FP8) runs layer by layer on one GPU: each layer is built from
transformers' own glm5_next modules (attention, KDA, mHC) with the routed experts replaced by a module that also
records, per expert:
    n          tokens routed to it
    imat_gu    sum over its tokens of x^2 per input channel (the imatrix of gate/up: the diagonal of X^T X)
    imat_d     the same for the down projection's input h = swiglu(gate, up)
    sal        sum of routing weight * ||expert output||  (REAP saliency)
and the dense / shared tensors get their imatrix too.  The hidden streams of every sequence live in two memmaps
(bf16) on disk between layers, so the pass resumes at the first layer whose stats file is missing.  After the last
layer the eval sequences' logits give the reference: top-64 log-probs and the logsumexp at every position
(ref_topk.npz) - the yardstick quants are scored against.  Each MoE layer's input over the calibration sequences
is kept too (ffn_in_XX.bin, bf16 [n_cal, T, hidden], ~2.1 GB a layer): the routing and every expert's X^T X are
recomputed from it by the error-feedback rounding in quantize.

    python calib.py --fp8 DIR --calib calib.npy --eval eval.npy --out DIR [--layers 0-44] [--batch 8]

calib.npy / eval.npy: int32 [n_seq, T] token ids (prep_calib.py).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hf_map import Checkpoint, P  # noqa: E402

torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
torch.backends.cuda.matmul.allow_tf32 = False


def module_key(il: int, name: str) -> str | None:
    """A decoder layer module's parameter name -> the checkpoint key (None: handled specially)."""
    L = f"{P}layers.{il}."
    for site in ("attn", "ffn"):
        for part in ("fn", "base", "scale"):
            if name == f"{site}_hc.{part}":
                return L + f"hc_{site}_{part}"
    if name == "self_attn.conv1d.weight":
        return None
    if name.startswith("self_attn.forget_gate."):
        return L + "self_attn." + name[len("self_attn.forget_gate."):]
    return L + name


def load_layer(ck: Checkpoint, cfg, il: int, dev):
    from transformers.models.glm5_next.modeling_glm5_next import Glm5NextTextDecoderLayer
    with torch.device("meta"):
        layer = Glm5NextTextDecoderLayer(cfg, il)
    moe = ck.is_moe(il)
    if moe:
        layer.mlp = torch.nn.Identity()   # replaced by StatMoE (the stock experts module would take 29 GB fp32)
    layer = layer.to_empty(device=dev)
    with torch.no_grad():
        for name, p in layer.named_parameters():
            k = module_key(il, name)
            if k is None:
                L = f"{P}layers.{il}.self_attn."
                w = torch.cat([ck.get(L + f"{c}_conv1d.weight") for c in ("q", "k", "v")], 0)
            else:
                w = ck.get(k)
            if tuple(w.shape) != tuple(p.shape):
                w = w.reshape(p.shape)
            p.copy_(w.to(p.dtype))
        for name, b in layer.named_buffers():
            k = module_key(il, name)
            if k is not None and ck.has(k):
                b.copy_(ck.get(k).to(b.dtype))
    layer.eval()
    return layer


class Stat:
    """Per-input-channel sums of squares and a token count (an imatrix entry)."""

    def __init__(self, n_in: int, dev):
        self.ss = torch.zeros(n_in, dtype=torch.float64, device=dev)
        self.n = 0

    def add(self, x: torch.Tensor):
        self.ss += x.double().square().sum(0)
        self.n += x.shape[0]


class StatMoE(torch.nn.Module):
    def __init__(self, ck: Checkpoint, cfg, il: int, dev):
        super().__init__()
        L = f"{P}layers.{il}.mlp."
        self.E = int(cfg.n_routed_experts)
        self.k = int(cfg.num_experts_per_tok)
        self.scale = float(cfg.routed_scaling_factor)
        self.norm = bool(cfg.norm_topk_prob)
        self.limit = float(cfg.swiglu_limit)
        self.router = ck.get(L + "gate.weight").to(dev)
        self.bias = ck.get(L + "gate.e_score_correction_bias").to(dev)
        H, I = int(cfg.hidden_size), int(cfg.moe_intermediate_size)
        # the experts as fp16 on the device: 288 x 3 x 2048 x 4096 x 2 B = 14.5 GB
        self.wgu = torch.empty(self.E, 2 * I, H, dtype=torch.float16, device=dev)
        self.wd = torch.empty(self.E, H, I, dtype=torch.float16, device=dev)
        for e in range(self.E):
            g = ck.get(f"{L}experts.{e}.gate_proj.weight")
            u = ck.get(f"{L}experts.{e}.up_proj.weight")
            self.wgu[e, :I].copy_(g.to(dev, torch.float16))
            self.wgu[e, I:].copy_(u.to(dev, torch.float16))
            self.wd[e].copy_(ck.get(f"{L}experts.{e}.down_proj.weight").to(dev, torch.float16))
        S = f"{L}shared_experts."
        self.sg = ck.get(S + "gate_proj.weight").to(dev)
        self.su = ck.get(S + "up_proj.weight").to(dev)
        self.sd = ck.get(S + "down_proj.weight").to(dev)
        self.I = I
        self.collect = True
        self.n = torch.zeros(self.E, dtype=torch.float64, device=dev)
        self.sal = torch.zeros(self.E, dtype=torch.float64, device=dev)
        self.imat_gu = torch.zeros(self.E, H, dtype=torch.float64, device=dev)
        self.imat_d = torch.zeros(self.E, I, dtype=torch.float64, device=dev)
        self.sh_gu = Stat(H, dev)
        self.sh_d = Stat(I, dev)
        self.router_in = Stat(H, dev)

    def _swiglu(self, g, u):
        g = g.clamp(max=self.limit)
        u = u.clamp(min=-self.limit, max=self.limit)
        return F.silu(g) * u

    def forward(self, hs: torch.Tensor) -> torch.Tensor:
        shape = hs.shape
        x = hs.reshape(-1, shape[-1]).float()
        # the router (Glm5NextTextTopkRouter, n_group 1): sigmoid scores, bias for the choice only
        logits = F.linear(x, self.router)
        scores = logits.sigmoid()
        idx = torch.topk(scores + self.bias, self.k, dim=-1, sorted=False)[1]
        w = scores.gather(1, idx)
        if self.norm:
            w = w / (w.sum(-1, keepdim=True) + 1e-20)
        w = w * self.scale
        out = torch.zeros_like(x)
        flat = idx.reshape(-1)
        order = torch.argsort(flat)
        counts = torch.bincount(flat, minlength=self.E).tolist()
        tok = (order // self.k)
        wk = w.reshape(-1)[order]
        pos = 0
        for e in range(self.E):
            c = counts[e]
            if c == 0:
                continue
            t = tok[pos:pos + c]
            we = wk[pos:pos + c]
            pos += c
            xe = x[t]
            gu = (xe.half() @ self.wgu[e].t()).float()
            h = self._swiglu(gu[:, :self.I], gu[:, self.I:])
            y = (h.half() @ self.wd[e].t()).float()
            if self.collect:
                self.n[e] += c
                self.imat_gu[e] += xe.double().square().sum(0)
                self.imat_d[e] += h.double().square().sum(0)
                self.sal[e] += (we.double() * y.double().norm(dim=1)).sum()
            out.index_add_(0, t, y * we[:, None])
        hsh = self._swiglu(F.linear(x, self.sg), F.linear(x, self.su))
        out += F.linear(hsh, self.sd)
        if self.collect:
            self.router_in.add(x)
            self.sh_gu.add(x)
            self.sh_d.add(hsh)
        return out.reshape(shape).to(hs.dtype)

    def stats(self):
        return {"n": self.n.cpu(), "sal": self.sal.cpu(), "imat_gu": self.imat_gu.float().cpu(),
                "imat_d": self.imat_d.float().cpu(), "sh_gu": self.sh_gu.ss.float().cpu(), "sh_d": self.sh_d.ss.float().cpu(),
                "sh_n": self.sh_gu.n}


def hook_linear_stats(layer, collect):
    """imatrix sums for every nn.Linear of the layer (attention, KDA, dense FFN), by module name."""
    stats, hooks = {}, []
    for name, m in layer.named_modules():
        if isinstance(m, torch.nn.Linear):
            def h(mod, inp, out, name=name):
                if not collect[0]:
                    return
                x = inp[0].reshape(-1, inp[0].shape[-1])
                s = stats.get(name)
                if s is None:
                    s = stats[name] = Stat(x.shape[-1], x.device)
                s.add(x)
            hooks.append(m.register_forward_hook(h))
    return stats, hooks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fp8", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--layers", default=None, help="a-b (default: all, resuming)")
    ap.add_argument("--batch", type=int, default=8, help="sequences per MoE batch")
    ap.add_argument("--topk", type=int, default=64)
    ap.add_argument("--save-ffn-in", type=int, default=1,
                    help="keep each MoE layer's input (calibration sequences, bf16 ffn_in_XX.bin) for quantize's rounding")
    a = ap.parse_args()
    from transformers import AutoConfig
    dev = torch.device("cuda")
    ck = Checkpoint(a.fp8)
    cfg = AutoConfig.from_pretrained(a.fp8).text_config
    cfg._attn_implementation = "sdpa"
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    calib = np.load(a.calib)
    evals = np.load(a.eval)
    if calib.shape[1] != evals.shape[1]:
        raise SystemExit("calib and eval sequences must share their length")
    seqs = np.concatenate([calib, evals], 0).astype(np.int64)
    n_cal, n_seq, T = calib.shape[0], seqs.shape[0], seqs.shape[1]
    H, HC = int(cfg.hidden_size), int(cfg.hc_mult)
    n_layers = int(cfg.num_hidden_layers)
    shape = (n_seq, T, HC, H)
    bufs = [out / "streams_a.bin", out / "streams_b.bin"]
    first, last = 0, n_layers - 1
    if a.layers:
        first, last = (int(v) for v in a.layers.split("-"))
    # resume: the first layer without its stats; the streams before it are in the buffer that layer reads
    while first <= last and (out / f"stats_{first:02d}.pt").exists():
        first += 1
    cur = first % 2
    mm = [np.memmap(b, dtype=np.uint16, mode="r+" if b.exists() else "w+", shape=shape) for b in bufs]
    if first == 0:
        emb = ck.get(P + "embed_tokens.weight")
        for s in range(n_seq):
            e = emb[torch.from_numpy(seqs[s])].to(torch.bfloat16)          # [T, H]
            mm[0][s] = e.unsqueeze(1).expand(T, HC, H).contiguous().view(torch.uint16).numpy()
        mm[0].flush()
        del emb
    topk_prev = {}   # the indexer's top-k of the previous full DSA layer, per sequence (shared DSA layers reuse it)
    tp_file = out / "topk_prev.pt"
    if first > 0 and tp_file.exists():
        topk_prev = torch.load(tp_file)
    pos = torch.arange(T, device=dev).unsqueeze(0)
    mask = torch.ones(1, T, dtype=torch.bool, device=dev)
    for il in range(first, last + 1):
        t0 = time.time()
        src, dst = mm[il % 2], mm[(il + 1) % 2]
        layer = load_layer(ck, cfg, il, dev)
        moe = StatMoE(ck, cfg, il, dev) if ck.is_moe(il) else None
        ffn_in = None
        if moe is not None and a.save_ffn_in:
            ffn_in = np.memmap(out / f"ffn_in_{il:02d}.bin", dtype=np.uint16, mode="w+", shape=(n_cal, T, H))
        collect = [True]
        lin_stats, hooks = hook_linear_stats(layer, collect)
        t_load = time.time() - t0
        new_topk = {}
        for b0 in range(0, n_seq, a.batch):
            bs = list(range(b0, min(n_seq, b0 + a.batch)))
            collect[0] = bs[0] < n_cal          # statistics from the calibration sequences only
            if moe is not None:
                moe.collect = collect[0]
            mids, posts, combs, res = [], [], [], []
            with torch.no_grad():
                # the attention half of each sequence (Glm5NextTextDecoderLayer.forward, split at the FFN)
                for s in bs:
                    h = torch.from_numpy(np.asarray(src[s])).view(torch.bfloat16).to(dev).float().unsqueeze(0)
                    residual = h
                    post, comb, x = layer.attn_hc(h)
                    x = layer.input_layernorm(x)
                    if layer.block_type == "linear_attention":
                        x = layer.self_attn(hidden_states=x, cache_params=None, attention_mask=mask)
                    else:
                        x, _, tk = layer.self_attn(hidden_states=x, attention_mask=mask, position_ids=pos,
                                                  past_key_values=None, use_cache=False, position_embeddings=None,
                                                  prev_topk_indices=topk_prev.get(s))
                        if tk is not None:
                            new_topk[s] = tk
                    h = post.unsqueeze(-1) * x.unsqueeze(-2) + torch.matmul(comb.transpose(-1, -2), residual)
                    residual = h
                    post, comb, x = layer.ffn_hc(h)
                    x = layer.post_attention_layernorm(x)
                    mids.append(x)
                    posts.append(post)
                    combs.append(comb)
                    res.append(residual)
                # the FFN over the whole batch (the MoE's GEMMs see ~T * batch * 8 / 288 tokens per expert)
                X = torch.cat(mids, 0)
                if ffn_in is not None:   # the MoE input of the calibration sequences, for the rounding pass
                    for i, s in enumerate(bs):
                        if s < n_cal:
                            ffn_in[s] = X[i].to(torch.bfloat16).view(torch.uint16).cpu().numpy()
                Y = moe(X) if moe is not None else layer.mlp(X)
                for i, s in enumerate(bs):
                    y = Y[i:i + 1]
                    h = posts[i].unsqueeze(-1) * y.unsqueeze(-2) + torch.matmul(combs[i].transpose(-1, -2), res[i])
                    dst[s] = h[0].to(torch.bfloat16).view(torch.uint16).cpu().numpy()
        for hk in hooks:
            hk.remove()
        dst.flush()
        if ffn_in is not None:
            ffn_in.flush()
            del ffn_in
        topk_prev.update(new_topk)
        torch.save(topk_prev, tp_file)
        st = {"layer": il, "linear": {k: {"ss": v.ss.float().cpu(), "n": v.n} for k, v in lin_stats.items()}}
        if moe is not None:
            st["moe"] = moe.stats()
        torch.save(st, out / f"stats_{il:02d}.pt")
        del layer, moe
        torch.cuda.empty_cache()
        print(f"layer {il:2d}: {time.time() - t0:6.1f} s (load {t_load:.1f} s)", flush=True)
    if last == n_layers - 1:
        reference(ck, cfg, mm[(last + 1) % 2], n_cal, n_seq, T, a.topk, out, dev)


def reference(ck, cfg, streams, n_cal, n_seq, T, topk, out, dev):
    """The eval sequences' next-token distributions: the hc head (mean of the streams), the final norm, lm_head."""
    norm_w = ck.get(P + "norm.weight").to(dev)
    eps = float(cfg.rms_norm_eps)
    lm = ck.get("lm_head.weight").to(dev, torch.float16)
    vals, idxs, lses = [], [], []
    with torch.no_grad():
        for s in range(n_cal, n_seq):
            h = torch.from_numpy(np.asarray(streams[s])).view(torch.bfloat16).to(dev).float().mean(1)   # [T, H]
            h = h * torch.rsqrt(h.square().mean(-1, keepdim=True) + eps) * norm_w
            lg = (h.half() @ lm.t()).float()
            lse = torch.logsumexp(lg, -1)
            v, i = torch.topk(lg, topk, -1)
            vals.append((v - lse[:, None]).cpu().numpy())
            idxs.append(i.int().cpu().numpy())
            lses.append(lse.cpu().numpy())
    np.savez(out / "ref_topk.npz", logprob=np.stack(vals), ids=np.stack(idxs), lse=np.stack(lses))
    print(f"reference: {n_seq - n_cal} sequences x {T} positions, top-{topk}", flush=True)


if __name__ == "__main__":
    main()
