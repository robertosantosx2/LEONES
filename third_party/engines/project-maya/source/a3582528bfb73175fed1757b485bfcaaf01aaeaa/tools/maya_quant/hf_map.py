"""tools/maya_quant/hf_map.py - the official GLM-5.3-Flash checkpoint (zai-org, block-FP8 safetensors) read tensor by
tensor, and its mapping onto the GGUF names, shapes and layouts the engine and llama.cpp use (glm5next).

    ckpt = Checkpoint("/path/to/glm53-fp8")
    t = ckpt.get("model.language_model.layers.3.mlp.experts.17.gate_proj.weight")   # float32, dequantised
    for name, make in gguf_tensors(ckpt): w = make()   # numpy-ordered float32, GGUF's layout ([ne2, ne1, ne0])

`python hf_map.py verify <fp8 dir> <reference gguf shard 1> [layers]` compares every mapped tensor of those layers with
the reference GGUF's (dequantised by gguf-py): a wrong transform shows as a cosine far from 1.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import torch
from safetensors import safe_open

P = "model.language_model."


class Checkpoint:
    def __init__(self, root: str):
        self.root = pathlib.Path(root)
        self.cfg = json.load(open(self.root / "config.json"))
        self.text = self.cfg.get("text_config", self.cfg)
        self.map = json.load(open(self.root / "model.safetensors.index.json"))["weight_map"]
        self._open: dict[str, object] = {}

    def has(self, name: str) -> bool:
        return name in self.map

    def raw(self, name: str) -> torch.Tensor:
        shard = self.map[name]
        f = self._open.get(shard)
        if f is None:
            f = safe_open(str(self.root / shard), framework="pt")
            self._open[shard] = f
        return f.get_tensor(name)

    def get(self, name: str) -> torch.Tensor:
        """The tensor as float32; block-FP8 weights are multiplied by their 128 x 128 block scales."""
        t = self.raw(name)
        if t.dtype == torch.float8_e4m3fn:
            s = self.raw(name + "_scale_inv").float()
            w = t.float()
            rb, cb = 128, 128
            s = s.repeat_interleave(rb, 0)[: w.shape[0]].repeat_interleave(cb, 1)[:, : w.shape[1]]
            return w * s
        return t.float()

    # geometry
    @property
    def n_layers(self) -> int:
        return int(self.text["num_hidden_layers"])

    def layer_type(self, il: int) -> str:
        return self.text["layer_types"][il] if il < self.n_layers else "deepseek_sparse_attention"

    def is_moe(self, il: int) -> bool:
        return il >= int(self.text.get("first_k_dense_replace", 3))


def gguf_tensors(ck: Checkpoint, layers=None, experts: bool = True):
    """(gguf name, thunk -> float32 tensor in GGUF numpy order) for every tensor of the model (or of `layers`)."""
    T = ck.text
    n_head = int(T["num_attention_heads"])
    qk_nope = int(T["qk_nope_head_dim"])
    v_head = int(T["v_head_dim"])
    kv_lora = int(T["kv_lora_rank"])
    n_exp = int(T["n_routed_experts"])
    out = []
    if layers is None:
        out += [("token_embd.weight", lambda: ck.get(P + "embed_tokens.weight")),
                ("output_norm.weight", lambda: ck.get(P + "norm.weight")),
                ("output.weight", lambda: ck.get("lm_head.weight"))]
        layers = range(ck.n_layers + int(T.get("num_nextn_predict_layers", 0)))
    for il in layers:
        L = f"{P}layers.{il}."
        B = f"blk.{il}."

        def g(n, L=L):
            return lambda: ck.get(L + n)
        out += [(B + "attn_norm.weight", g("input_layernorm.weight")),
                (B + "ffn_norm.weight", g("post_attention_layernorm.weight"))]
        if ck.has(L + "hc_attn_fn"):
            for site in ("attn", "ffn"):
                out += [(B + f"hc_{site}_fn.weight", g(f"hc_{site}_fn")),
                        (B + f"hc_{site}_base.weight", g(f"hc_{site}_base")),
                        (B + f"hc_{site}_scale.weight", g(f"hc_{site}_scale"))]
        if ck.layer_type(il) == "linear_attention":
            A = L + "self_attn."
            out += [(B + "attn_q.weight", g("self_attn.q_proj.weight")),
                    (B + "attn_k.weight", g("self_attn.k_proj.weight")),
                    (B + "attn_v.weight", g("self_attn.v_proj.weight")),
                    (B + "attn_output.weight", g("self_attn.o_proj.weight")),
                    (B + "ssm_conv1d_q.weight", g("self_attn.q_conv1d.weight")),
                    (B + "ssm_conv1d_k.weight", g("self_attn.k_conv1d.weight")),
                    (B + "ssm_conv1d_v.weight", g("self_attn.v_conv1d.weight")),
                    (B + "ssm_a", lambda A=A: -torch.exp(ck.get(A + "A_log")).reshape(-1)),
                    (B + "ssm_dt.bias", g("self_attn.dt_bias")),
                    (B + "ssm_beta.weight", g("self_attn.b_proj.weight")),
                    (B + "ssm_f_a.weight", g("self_attn.f_a_proj.weight")),
                    (B + "ssm_f_b.weight", g("self_attn.f_b_proj.weight")),
                    (B + "ssm_g_a.weight", g("self_attn.g_a_proj.weight")),
                    (B + "ssm_g_b.weight", g("self_attn.g_b_proj.weight")),
                    (B + "ssm_norm.weight", g("self_attn.o_norm.weight"))]
        else:
            A = L + "self_attn."

            def kv_b(part, A=A):
                def f():
                    w = ck.get(A + "kv_b_proj.weight").view(n_head, qk_nope + v_head, kv_lora)
                    if part == "k":   # [n_head, kv_lora, qk_nope]
                        return w[:, :qk_nope, :].transpose(1, 2).contiguous()
                    return w[:, qk_nope:, :].contiguous()   # [n_head, v_head, kv_lora]
                return f
            out += [(B + "attn_q_a.weight", g("self_attn.q_a_proj.weight")),
                    (B + "attn_q_a_norm.weight", g("self_attn.q_a_layernorm.weight")),
                    (B + "attn_q_b.weight", g("self_attn.q_b_proj.weight")),
                    (B + "attn_kv_a_mqa.weight", g("self_attn.kv_a_proj_with_mqa.weight")),
                    (B + "attn_kv_a_norm.weight", g("self_attn.kv_a_layernorm.weight")),
                    (B + "attn_k_b.weight", kv_b("k")),
                    (B + "attn_v_b.weight", kv_b("v")),
                    (B + "attn_output.weight", g("self_attn.o_proj.weight")),
                    (B + "indexer.attn_q_b.weight", g("self_attn.indexer.wq_b.weight")),
                    (B + "indexer.attn_k.weight", g("self_attn.indexer.wk.weight")),
                    (B + "indexer.proj.weight", g("self_attn.indexer.weights_proj.weight")),
                    (B + "indexer.k_norm.weight", g("self_attn.indexer.k_norm.weight")),
                    (B + "indexer.k_norm.bias", g("self_attn.indexer.k_norm.bias")),
                    (B + "indexer_compressor_ape.weight", g("self_attn.indexer.index_kpool_compress_ape")),
                    (B + "indexer_compressor_gate.weight", g("self_attn.indexer.index_kpool_compress_gate"))]
        if ck.is_moe(il):
            out += [(B + "ffn_gate_inp.weight", g("mlp.gate.weight")),
                    (B + "exp_probs_b.bias", g("mlp.gate.e_score_correction_bias")),
                    (B + "ffn_gate_shexp.weight", g("mlp.shared_experts.gate_proj.weight")),
                    (B + "ffn_up_shexp.weight", g("mlp.shared_experts.up_proj.weight")),
                    (B + "ffn_down_shexp.weight", g("mlp.shared_experts.down_proj.weight"))]
            if experts:
                for role in ("gate", "up", "down"):
                    out.append((B + f"ffn_{role}_exps.weight",
                                lambda L=L, role=role: torch.stack(
                                    [ck.get(f"{L}mlp.experts.{e}.{role}_proj.weight") for e in range(n_exp)])))
        else:
            out += [(B + "ffn_gate.weight", g("mlp.gate_proj.weight")),
                    (B + "ffn_up.weight", g("mlp.up_proj.weight")),
                    (B + "ffn_down.weight", g("mlp.down_proj.weight"))]
        if ck.has(L + "eh_proj.weight"):   # the NextN (MTP) block
            out += [(B + "nextn.eh_proj.weight", g("eh_proj.weight")),
                    (B + "nextn.enorm.weight", g("enorm.weight")),
                    (B + "nextn.hnorm.weight", g("hnorm.weight")),
                    (B + "nextn.shared_head_norm.weight", g("shared_head.norm.weight"))]
    return out


def _verify(fp8: str, ref: str, layers):
    import numpy as np
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "build/_deps/strata_llamacpp-src/gguf-py"))
    import gguf
    ck = Checkpoint(fp8)
    shards = sorted(pathlib.Path(ref).parent.glob(re.sub(r"-00001-of-", "-*-of-", pathlib.Path(ref).name)))
    readers = [gguf.GGUFReader(str(s)) for s in shards]
    by = {t.name: t for r in readers for t in r.tensors}
    worst = 1.0
    for name, make in gguf_tensors(ck, layers, experts=True):
        t = by.get(name)
        if t is None:
            print(f"{name}: NOT IN THE REFERENCE")
            continue
        mine = make()
        if name.endswith("_exps.weight"):   # one expert is enough to check the layout (data is [expert][row][bytes])
            mine = mine[:1]
            ref_t = gguf.quants.dequantize(np.asarray(t.data)[:1], t.tensor_type)
        else:
            ref_t = gguf.quants.dequantize(np.asarray(t.data), t.tensor_type)
        a = mine.reshape(-1).double()
        b = torch.from_numpy(np.ascontiguousarray(ref_t)).reshape(-1).double()
        if a.numel() != b.numel():
            print(f"{name}: SIZE {tuple(mine.shape)} vs ref {tuple(ref_t.shape)}")
            continue
        cos = float((a @ b) / (a.norm() * b.norm() + 1e-30))
        worst = min(worst, cos)
        flag = "" if cos > 0.99 else "   <-- CHECK"
        print(f"{name:45s} {str(tuple(mine.shape)):24s} ref {t.tensor_type.name:8s} cos {cos:.6f}{flag}")
    print(f"worst cosine {worst:.6f}")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "verify":
        ls = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else [0, 3]
        _verify(sys.argv[2], sys.argv[3], ls)
    else:
        print(__doc__)
