"""tools/maya_quant/gptq.py - error-feedback rounding of the routed experts (docs/QUANT-PLAN.md, stage 3).

GPTQ at superblock granularity, for any ggml type whose rows are independent 256-weight superblocks (the IQ lattice
types and the K-quants): per expert, the input dimension is walked in 256-column blocks.  Each block is quantized by
llama.cpp's own quantizer (ggml_quantize_chunk) with the importance of its columns once the later columns may still
move (the diagonal of the inverse of the block's inverse-Hessian), and its rounding error is pushed into the columns
not yet quantized through the Cholesky factor of the inverse Hessian - the lazy-batch form of GPTQ with the block's
columns removed jointly.  The bytes are exactly the GGUF's: a row is its superblocks in order.

Hessians come from calib.py's ffn_in_XX.bin (the MoE input of the calibration sequences): the routing is recomputed,
an expert's gate/up Hessian is sum(w^2 x x^T) over its tokens (w its routing weight), plus a prior of `prior` tokens'
worth of the layer-wide input Hessian so that rarely routed experts are not fitted to a handful of tokens.  The down
projection's Hessian is built from the already-rounded gate/up (h = swiglu of the quantized projections), so down
absorbs their error too.

    python gptq.py test --stats DIR --fp8 DIR --layer 3 [--types IQ2_XXS,IQ2_XXS,IQ2_S] [--experts 32]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import ctypes
import pathlib
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hf_map import Checkpoint, P  # noqa: E402

torch.backends.cuda.matmul.allow_tf32 = False
BLOCK = 256


class _Traits(ctypes.Structure):
    _fields_ = [("type_name", ctypes.c_char_p), ("blck_size", ctypes.c_int64), ("blck_size_interleave", ctypes.c_int64),
                ("type_size", ctypes.c_size_t), ("is_quantized", ctypes.c_bool), ("to_float", ctypes.c_void_p),
                ("from_float_ref", ctypes.c_void_p)]


class Codec:
    """ggml's quantizer and dequantizer for one type (libggml-base through ctypes; the calls release the GIL)."""

    def __init__(self, lib, t: int):
        self.lib, self.t = lib, t
        lib.ggml_quantize_init(t)
        lib.ggml_get_type_traits.restype = ctypes.POINTER(_Traits)
        lib.ggml_get_type_traits.argtypes = [ctypes.c_int]
        tr = lib.ggml_get_type_traits(t).contents
        self.to_float = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64)(tr.to_float)
        self.bpb = int(lib.ggml_row_size(t, BLOCK))     # bytes of one 256-weight block

    def quantize(self, src: np.ndarray, imat: np.ndarray) -> np.ndarray:
        """src float32 [rows, 256] -> uint8 [rows, bpb]"""
        rows = src.shape[0]
        dst = np.empty((rows, self.bpb), dtype=np.uint8)
        self.lib.ggml_quantize_chunk(self.t, src.ctypes.data, dst.ctypes.data, 0, rows, BLOCK, imat.ctypes.data)
        return dst

    def dequantize(self, q: np.ndarray) -> np.ndarray:
        rows = q.shape[0]
        y = np.empty((rows, BLOCK), dtype=np.float32)
        self.to_float(q.ctypes.data, y.ctypes.data, rows * BLOCK)
        return y


def gptq(W: torch.Tensor, H: torch.Tensor, codec: Codec, pool, damp: torch.Tensor):
    """W [C, R, n] fp32 (modified), H [C, n, n] fp32 (consumed) -> (uint8 [C, R, n/256*bpb], dequantized [C, R, n])."""
    C, R, n = W.shape
    dev = W.device
    dg = H.diagonal(dim1=1, dim2=2)
    m = dg.mean(-1)
    m = torch.where(m > 0, m, torch.ones_like(m))           # an expert that saw no token: plain rounding
    dead = dg <= 0                                            # channels never active: their own diagonal
    dg += torch.where(dead, m[:, None], torch.zeros_like(dg)) + damp[:, None] * m[:, None]
    L = torch.linalg.cholesky(H)
    Hinv = torch.cholesky_inverse(L)
    del L, H
    U = torch.linalg.cholesky(Hinv, upper=True)
    del Hinv
    out = np.empty((C, R, n // BLOCK * codec.bpb), dtype=np.uint8)
    deq = torch.empty_like(W)
    Ib = torch.eye(BLOCK, device=dev)
    for b0 in range(0, n, BLOCK):
        b1 = b0 + BLOCK
        Uss = U[:, b0:b1, b0:b1]
        Uinv = torch.linalg.solve_triangular(Uss, Ib.expand(C, BLOCK, BLOCK), upper=True)
        imp = Uinv.square().sum(-1).clamp(min=1e-20)          # diag(inv(Hinv_SS)): [C, 256]
        imp = imp / imp.mean(-1, keepdim=True)
        Wb = W[:, :, b0:b1].contiguous().cpu().numpy()
        im = imp.cpu().numpy().astype(np.float32)
        k0 = b0 // BLOCK * codec.bpb
        Qn = np.empty((C, R, BLOCK), dtype=np.float32)
        step = max(64, -(-R * C // (4 * pool._max_workers)))   # ~4 jobs a thread

        def one(job):
            e, r0 = job
            q = codec.quantize(np.ascontiguousarray(Wb[e, r0:r0 + step]), np.ascontiguousarray(im[e]))
            out[e, r0:r0 + step, k0:k0 + codec.bpb] = q
            Qn[e, r0:r0 + step] = codec.dequantize(q)

        list(pool.map(one, [(e, r0) for e in range(C) for r0 in range(0, R, step)]))
        Qb = torch.from_numpy(Qn).to(dev)
        deq[:, :, b0:b1] = Qb
        if b1 < n:
            Err = torch.linalg.solve_triangular(Uss, W[:, :, b0:b1] - Qb, upper=True, left=False)   # E Uss^-1
            W[:, :, b1:] -= Err @ U[:, b0:b1, b1:]
    return out, deq


class Layer:
    """One MoE layer's routed experts, router, and calibration inputs."""

    def __init__(self, ck: Checkpoint, cfg: dict, stats: pathlib.Path, il: int, dev):
        self.ck, self.il, self.dev = ck, il, dev
        self.E, self.k = int(cfg["n_routed_experts"]), int(cfg["num_experts_per_tok"])
        self.H, self.I = int(cfg["hidden_size"]), int(cfg["moe_intermediate_size"])
        self.limit = float(cfg.get("swiglu_limit") or 0.0)
        self.L = f"{P}layers.{il}.mlp."
        X = np.memmap(stats / f"ffn_in_{il:02d}.bin", dtype=np.uint16, mode="r").reshape(-1, self.H)
        self.X = torch.from_numpy(np.ascontiguousarray(X)).to(dev).view(torch.bfloat16)          # [N, H]
        router = ck.get(self.L + "gate.weight").to(dev)
        bias = ck.get(self.L + "gate.e_score_correction_bias").to(dev)
        idx, w = [], []
        for c0 in range(0, self.X.shape[0], 65536):
            s = F.linear(self.X[c0:c0 + 65536].float(), router).sigmoid()
            i = torch.topk(s + bias, self.k, dim=-1, sorted=False)[1]
            ww = s.gather(1, i)
            ww = ww / (ww.sum(-1, keepdim=True) + 1e-20) if cfg.get("norm_topk_prob", True) else ww
            idx.append(i)
            w.append(ww)
        idx, w = torch.cat(idx), torch.cat(w)
        flat = idx.reshape(-1)
        order = torch.argsort(flat)
        self.counts = torch.bincount(flat, minlength=self.E).tolist()
        self.starts = np.concatenate([[0], np.cumsum(self.counts)]).tolist()
        self.tok = order // self.k
        self.w = w.reshape(-1)[order]
        # the layer-wide input Hessian per token (the prior of rarely routed experts)
        Hb = torch.zeros(self.H, self.H, device=dev)
        for c0 in range(0, self.X.shape[0], 65536):
            x = self.X[c0:c0 + 65536].float()
            Hb += x.t() @ x
        self.Hbar = Hb / self.X.shape[0]

    def tokens(self, e, sel=None):
        """(x [n, H] fp32, w [n]) of expert e; sel: a boolean mask over the layer's token rows (train/held-out)."""
        a, b = self.starts[e], self.starts[e + 1]
        t, w = self.tok[a:b], self.w[a:b]
        if sel is not None:
            m = sel[t]
            t, w = t[m], w[m]
        return self.X[t].float(), w

    def weights(self, e):
        g = self.ck.get(f"{self.L}experts.{e}.gate_proj.weight").to(self.dev)
        u = self.ck.get(f"{self.L}experts.{e}.up_proj.weight").to(self.dev)
        d = self.ck.get(f"{self.L}experts.{e}.down_proj.weight").to(self.dev)
        return g.float(), u.float(), d.float()

    def swiglu(self, g, u):
        if self.limit > 0:
            g, u = g.clamp(max=self.limit), u.clamp(min=-self.limit, max=self.limit)
        return F.silu(g) * u


def round_gate_up(layer: Layer, experts, cg: Codec, cu: Codec, pool, prior=16384.0, damp=0.1, sel=None, Ws=None):
    """GPTQ of the experts' gate and up (they share the Hessian: one [2I, H] matrix each) -> (gate bytes [C, I, .],
    up bytes [C, I, .], dequantized [C, 2I, H], the tokens [(x, w)] used).  Measured on layer 3 at IQ2_XXS: the
    expert output error 27% below llama.cpp's imatrix rounding on held-out tokens (prior 16384, damp 0.1)."""
    C = len(experts)
    Ws = Ws or [layer.weights(e) for e in experts]
    xs = [layer.tokens(e, sel) for e in experts]
    Hgu = torch.empty(C, layer.H, layer.H, device=layer.dev)
    for i, (x, w) in enumerate(xs):
        xw = x * w[:, None]
        Hgu[i] = xw.t() @ xw + prior * float(w.square().mean() if len(w) else 1.0) * layer.Hbar
    Wgu = torch.stack([torch.cat([g, u], 0) for g, u, _ in Ws])
    dmp = torch.full((C,), damp, device=layer.dev)
    if cg.t == cu.t:
        qgu, dgu = gptq(Wgu, Hgu, cg, pool, dmp)
        return qgu[:, :layer.I], qgu[:, layer.I:], dgu, xs
    qg, dg_ = gptq(Wgu[:, :layer.I].contiguous(), Hgu.clone(), cg, pool, dmp)
    qu, du_ = gptq(Wgu[:, layer.I:].contiguous(), Hgu, cu, pool, dmp)
    return qg, qu, torch.cat([dg_, du_], 1), xs


def round_experts(layer: Layer, experts, codecs, pool, prior=16384.0, damp=0.1, sel=None, dshrink=0.0):
    """GPTQ of the given experts, down included (the test): {e: (gate, up, down bytes, (gate, up, down) dequantized)}.
    dshrink: the down Hessian is pulled toward its diagonal by this fraction (1: imatrix rounding, no feedback).
    Down by GPTQ measured worse than down by imatrix rounding at every dshrink, so the quants round only gate/up."""
    cg, cu, cd = codecs
    res = {}
    Ws = [layer.weights(e) for e in experts]
    C = len(experts)
    qg, qu, dgu, xs = round_gate_up(layer, experts, cg, cu, pool, prior, damp, sel, Ws)
    # down: its inputs through the rounded gate/up
    Hd = torch.empty(C, layer.I, layer.I, device=layer.dev)
    dmp = torch.empty(C, device=layer.dev)
    for i, (x, w) in enumerate(xs):
        h = layer.swiglu(x @ dgu[i, :layer.I].t(), x @ dgu[i, layer.I:].t()) * w[:, None]
        Hd[i] = h.t() @ h
        if dshrink > 0:
            dgd = Hd[i].diagonal().clone()
            Hd[i] *= 1.0 - dshrink
            Hd[i].diagonal().copy_(dgd)
        dmp[i] = damp
    Wd = torch.stack([d for _, _, d in Ws])
    qd, dd = gptq(Wd, Hd, cd, pool, dmp)
    for i, e in enumerate(experts):
        res[e] = (qg[i], qu[i], qd[i], (dgu[i, :layer.I], dgu[i, layer.I:], dd[i]))
    return res


def rtn_experts(layer: Layer, experts, codecs, pool):
    """The baseline: each expert's tensors quantized whole with the plain imatrix (mean w^0 x^2), as llama.cpp does."""
    out = {}
    for e in experts:
        g, u, d = layer.weights(e)
        x, w = layer.tokens(e)
        img = (x.square().mean(0) if len(w) else torch.ones(layer.H, device=layer.dev)).cpu().numpy()
        h = layer.swiglu(x @ g.t(), x @ u.t())
        imd = (h.square().mean(0) if len(w) else torch.ones(layer.I, device=layer.dev)).cpu().numpy()
        deqs = []
        for W, im, c in ((g, img, codecs[0]), (u, img, codecs[1]), (d, imd, codecs[2])):
            Wn = W.cpu().numpy()
            R, n = Wn.shape
            blocks = Wn.reshape(R, n // BLOCK, BLOCK).transpose(1, 0, 2)
            ims = im.reshape(n // BLOCK, BLOCK).astype(np.float32)
            parts = list(pool.map(lambda j: c.dequantize(c.quantize(np.ascontiguousarray(blocks[j]),
                                                                      np.ascontiguousarray(ims[j]))), range(n // BLOCK)))
            deqs.append(torch.from_numpy(np.stack(parts, 1).reshape(R, n)).to(layer.dev))
        out[e] = deqs
    return out


def expert_err(layer, e, deq, sel):
    """relative output error of expert e on the token rows in sel: ||w (y_q - y)||^2 / ||w y||^2"""
    x, w = layer.tokens(e, sel)
    if len(w) == 0:
        return float("nan")
    g, u, d = layer.weights(e)
    y = layer.swiglu(x @ g.t(), x @ u.t()) @ d.t()
    yq = layer.swiglu(x @ deq[0].t(), x @ deq[1].t()) @ deq[2].t()
    return float(((yq - y) * w[:, None]).square().sum() / ((y * w[:, None]).square().sum() + 1e-30))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["test"])
    ap.add_argument("--stats", required=True)
    ap.add_argument("--fp8", required=True)
    ap.add_argument("--layer", type=int, default=3)
    ap.add_argument("--types", default="IQ2_XXS,IQ2_XXS,IQ2_S")
    ap.add_argument("--experts", type=int, default=24)
    ap.add_argument("--prior", default="64", help="tokens' worth of the layer-wide Hessian (a comma list to sweep)")
    ap.add_argument("--damp", default="0.1", help="relative diagonal damping (a comma list to sweep)")
    ap.add_argument("--dshrink", default="0", help="down Hessian pulled toward its diagonal (a comma list to sweep)")
    ap.add_argument("--chunk", type=int, default=4, help="experts rounded together (GPU memory)")
    ap.add_argument("--ggml", default="/mnt/nvme/maya/ggml-so/bin/libggml-base.so")
    ap.add_argument("--threads", type=int, default=12)
    a = ap.parse_args()
    import json
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "build/_deps/strata_llamacpp-src/gguf-py"))
    import gguf
    lib = ctypes.CDLL(a.ggml)
    lib.ggml_quantize_chunk.restype = ctypes.c_size_t
    lib.ggml_quantize_chunk.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64,
                                        ctypes.c_int64, ctypes.c_void_p]
    lib.ggml_row_size.restype = ctypes.c_size_t
    lib.ggml_row_size.argtypes = [ctypes.c_int, ctypes.c_int64]
    lib.ggml_quantize_init.argtypes = [ctypes.c_int]
    codecs = [Codec(lib, int(gguf.GGMLQuantizationType[t])) for t in a.types.split(",")]
    cfg = json.load(open(pathlib.Path(a.fp8) / "config.json"))
    cfg = cfg.get("text_config", cfg)
    dev = torch.device("cuda")
    ck = Checkpoint(a.fp8)
    t0 = time.time()
    layer = Layer(ck, cfg, pathlib.Path(a.stats), a.layer, dev)
    N = layer.X.shape[0]
    print(f"layer {a.layer}: {N} tokens, routing in {time.time() - t0:.1f} s", flush=True)
    # held-out: the last 20% of the calibration sequences (whole sequences, so no position overlap)
    sel_tr = torch.zeros(N, dtype=torch.bool, device=dev)
    sel_tr[: int(N * 0.8) // 2048 * 2048] = True
    sel_ho = ~sel_tr
    cnt = np.array(layer.counts)
    hot = list(np.argsort(-cnt)[: a.experts // 3])
    cold = list(np.argsort(cnt)[: a.experts // 3])
    rng = np.random.default_rng(0)
    mid = list(rng.choice([e for e in range(layer.E) if e not in hot + cold], a.experts - len(hot) - len(cold),
                          replace=False))
    experts = [int(e) for e in hot + mid + cold]
    pool = cf.ThreadPoolExecutor(a.threads)
    t0 = time.time()
    rt = rtn_experts(layer, experts, codecs, pool)
    t_rtn = time.time() - t0
    print(f"rtn {t_rtn:.1f} s for {len(experts)} experts", flush=True)
    r_err = {e: expert_err(layer, e, rt[e], sel_ho) for e in experts}
    rt = {e: [t.cpu() for t in v] for e, v in rt.items()}
    torch.cuda.empty_cache()
    rmean = np.mean(list(r_err.values()))
    for prior, damp, dshrink in ((float(p), float(d), float(s)) for p in str(a.prior).split(",")
                                 for d in str(a.damp).split(",") for s in str(a.dshrink).split(",")):
        t0 = time.time()
        g_err, gu_err, d_err = {}, {}, {}
        for c0 in range(0, len(experts), a.chunk):
            part = round_experts(layer, experts[c0:c0 + a.chunk], codecs, pool, prior, damp, sel_tr, dshrink)
            for e, v in part.items():
                r = [t.to(dev) for t in rt[e]]
                g_err[e] = expert_err(layer, e, v[3], sel_ho)
                gu_err[e] = expert_err(layer, e, (v[3][0], v[3][1], r[2]), sel_ho)   # gptq gate/up, rtn down
                d_err[e] = expert_err(layer, e, (r[0], r[1], v[3][2]), sel_ho)       # rtn gate/up, gptq down
            del part
            torch.cuda.empty_cache()
        rel = np.array([g_err[e] / r_err[e] for e in experts])
        worst = experts[int(np.argmax(rel))]
        print(f"prior {prior:6.0f} damp {damp:.3f} dshrink {dshrink:.2f}: mean rel err rtn {rmean:.5f} "
              f"gptq {np.mean(list(g_err.values())):.5f}"
              f" (gate/up only {np.mean(list(gu_err.values())):.5f}, down only {np.mean(list(d_err.values())):.5f})"
              f" | gptq/rtn median {np.median(rel):.3f} best {rel.min():.3f} worst {rel.max():.3f}"
              f" (expert {worst}, {cnt[worst]} tok) | {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
