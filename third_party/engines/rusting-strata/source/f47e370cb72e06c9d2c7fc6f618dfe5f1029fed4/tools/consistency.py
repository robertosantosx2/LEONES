# Cross-backend numerical consistency report (M2-T7, issue #36).
# Turns two `target/parity-result-<tag>.json` files (CUDA sm_70 and Vulkan sm_70) into the
# committed summary `docs/parity/cross-backend.json` plus the markdown rows of the report in
# `docs/V100-results.md`, with every divergent position attributed to a named, legitimate
# architectural/arithmetic difference (the registry below) or listed as an open follow-up.
# Optionally aggregates the `--nocapture` logs of `tests/kernels.rs`, `tests/llama_numerics.rs`
# and `tests/kv_q8.rs` into the per-op table, and compares two `perplexity --kld-base` files.
#
# Usage (CPU, phase A — reproduces the documented 9/640):
#   python3 -I tools/consistency.py \
#     --cuda   target/parity-result-cuda-sm70.json \
#     --vulkan target/parity-result-vk-sm70.json \
#     --out    docs/parity/cross-backend.json
#
# Usage (GPU window, phase B — same command shape, current build, plus evidence):
#   python3 -I tools/consistency.py --cuda target/parity-result-m2-cuda-sm70.json \
#     --vulkan target/parity-result-m2-vk-sm70.json \
#     --kernels /tmp/m2t7-kernels.txt --kernels /tmp/m2t7-llama.txt \
#     --arm f16=target/parity-result-m2-vk-sm70-f16.json \
#     --kld target/kld-cuda.bin target/kld-vk.bin \
#     --date 2026-11-XX --out docs/parity/cross-backend.json --markdown /tmp/m2t7-rows.md
#
# No GPU, no model, no network. The committed summary has no full-vocabulary arrays: no 640-position
# `argmax` and no per-position logprobs. The only arrays are the five (token, logprob) pairs at each of
# the divergent positions, for both backends, which the report needs to show the top-5 gap.
import argparse
import datetime
import json
import math
import pathlib
import re
import struct
import sys

VERSION = 1

# The legitimate-difference registry: every named mechanism that may move a bit, a per-op
# figure or an argmax between the three engine configurations. `measured` quotes the recorded
# magnitude and where it was measured; the M2-T7 window refreshes it on the M2 build.
REGISTRY = [
    {
        "id": "gemm-int8-vs-f16",
        "title": "int8-quantized GEMM (Vulkan) vs f16 tensor-core GEMM (CUDA)",
        "applies_to": "vulkan vs cuda, prefill GEMM on quantized weight types",
        "mechanism": "Vulkan takes the int8 MMQ path for types its policy allows (src/vulkan/mod.rs:819); "
                     "sm_70 CUDA always takes the f16 path because `i8_gemm` is false on Volta "
                     "(src/cuda/mod.rs:558). X is quantized to int8 per 32 elements on one side and "
                     "rounded to f16 on the other, so the two GEMMs multiply different numbers.",
        "measured": "3.17e-3 .. 4.08e-3 relative L2 per-op (docs/V100-results.md:303-310)",
        "arm": "STRATA_MMQ= forces the f16 GEMM on Vulkan and isolates this entry",
        "follow_up": "M3-T5 (Vulkan parity gap, docs/ROADMAP.md:351)",
    },
    {
        "id": "f16-round-vs-trunc",
        "title": "f16 conversion rounding vs truncation",
        "applies_to": "cuda vs vulkan, f16 GEMM operands",
        "mechanism": "CUDA converts operands with `__float2half` (round to nearest even); this driver's "
                     "SPIR-V `OpFConvert` truncates toward zero, so the two f16 GEMMs see different operands.",
        "measured": "5.41e-4 (IQ2_XS), 4.79e-5 (F32) relative L2 per-op (docs/V100-results.md:303-310); "
                    "recorded, not asserted, by tests/kernels.rs:409",
        "arm": None,
        "follow_up": "M3-T5",
    },
    {
        "id": "summation-order",
        "title": "summation order (mma.sync tile order vs cooperative matrices vs FMA)",
        "applies_to": "cuda vs vulkan and tensor-core vs FMA, same f16 products",
        "mechanism": "sm_70 CUDA sums the f16 products through `mma.sync.m8n8k4` (src/cuda/kernels.cu:mma884); "
                     "Vulkan has no VK_KHR_cooperative_matrix on this driver and sums through its own "
                     "workgroup reduction (src/vulkan/shaders/gemmi.glsl), the FMA arms sum serially. "
                     "The products are the same, the accumulation tree is not.",
        "measured": "2.6e-7 .. 8.2e-7 relative L2 per backend against its own reference; "
                    "1e-6 .. 1e-4 cross-backend on the same math (docs/V100-results.md:303-310)",
        "arm": "STRATA_VK_NO_COOP= forces Vulkan off cooperative matrices; STRATA_GEMM_FMA=1 the CUDA FMA path",
        "follow_up": None,
    },
    {
        "id": "no-coop-matrices",
        "title": "no cooperative matrices on Vulkan (V100 driver)",
        "applies_to": "vulkan",
        "mechanism": "Vulkan 1.4.312 on this host exposes no VK_KHR_cooperative_matrix, so Vulkan cannot "
                     "use the same MMA instruction shape as CUDA; its prefill GEMM and attention use "
                     "explicit workgroup reductions. This is the Vulkan side of `summation-order`.",
        "measured": "1e-6 .. 5e-4 relative L2 where only the reduction tree differs "
                    "(docs/V100-results.md:529-551)",
        "arm": "STRATA_VK_NO_COOP=",
        "follow_up": "M3-T5",
    },
    {
        "id": "q8-kv",
        "title": "q8 KV cache quantization",
        "applies_to": "`--kv q8` arms only (not used by --llama-numerics parity)",
        "mechanism": "`--kv q8` stores K/V as int8 with per-32 scales, the default path stores f16; the "
                     "attention scores read quantized K and the output quantized V. `--kv q8` does not "
                     "combine with `--llama-numerics` by design (src/main.rs), so parity keeps f16 KV.",
        "measured": "1.55e-3 .. 2.06e-3 relative L2 q8 vs f16 decode/prefill (docs/V100-results.md:556-558); "
                    "KV bytes 341/642 = 53.1 % (M2-T6)",
        "arm": "--kv q8",
        "follow_up": None,
    },
    {
        "id": "expert-slot-layout",
        "title": "expert-slot layout and MoE routing order",
        "applies_to": "cuda vs vulkan, MoE GEMV/combine",
        "mechanism": "The router's top-k expert ids are the same, but the per-slot gather order and the "
                     "combine reduction order differ between the CUDA and Vulkan MoE kernels; parity runs "
                     "also pass `--fixed-experts` so routing is identical on both sides.",
        "measured": "not measured above the summation-order floor in the M1/M0 per-op runs; "
                    "re-recorded in the M2-T7 window",
        "arm": "--fixed-experts (parity only)",
        "follow_up": None,
    },
    {
        "id": "either-mode-ambiguity",
        "title": "llama.cpp's own two modes disagree at this position",
        "applies_to": "end-to-end argmax only",
        "mechanism": "llama.cpp run as one batch and llama.cpp run token-by-token disagree at this "
                     "position (target/llama-batch-argmax.json, tools/selfparity.py); the two engines "
                     "sit on either side of a near-tie whose winner depends on summation order. The v1 "
                     "gate counts a token that matches either llama.cpp mode.",
        "measured": "llama.cpp self-agreement 630/640 (docs/m6-results.md: 98.28 %)",
        "arm": None,
        "follow_up": None,
    },
]
REGISTRY_BY_ID = {e["id"]: e for e in REGISTRY}


def fnum(v):
    """Format a float for markdown/JSON without losing the exponent."""
    if v is None:
        return None
    return float(f"{v:.3e}")


def load_parity(path):
    d = json.load(open(path))
    rows = d["rows"]
    return {
        "file": str(path),
        "total": d["total"],
        "agree": d.get("agree"),
        "either": d.get("either"),
        "rows": rows,
    }


def same_layout(c, v):
    if len(c["rows"]) != len(v["rows"]):
        sys.exit(f"prompt count differs: {len(c['rows'])} cuda vs {len(v['rows'])} vulkan")
    for a, b in zip(c["rows"], v["rows"]):
        if a["prompt"] != b["prompt"]:
            sys.exit(f"prompt order differs: {a['prompt']!r} vs {b['prompt']!r}")
        if len(a["argmax"]) != len(b["argmax"]):
            sys.exit(f"{a['prompt']!r}: {len(a['argmax'])} vs {len(b['argmax'])} positions")


def divergences(c, v, ref, alt, prompts, f16=None):
    """Every position where the two backends' greedy argmax differs, with its attribution.

    `f16` is the Vulkan `STRATA_MMQ=` (f16 GEMM) arm's rows. When it is available it decides between
    the two named GEMM mechanisms: a position the f16 arm still gets wrong is *not* explained by the
    int8 quantization (the arm would have fixed it) and falls to the same-math reduction order.
    Without the arm the attribution is a registry hypothesis and says so in `confidence`.
    """
    out = []
    for pi, (cr, vr) in enumerate(zip(c["rows"], v["rows"])):
        for pos, (a, b) in enumerate(zip(cr["argmax"], vr["argmax"])):
            if a == b:
                continue
            prompt = prompts[pi] if prompts and pi < len(prompts) else None
            ref_tok = alt_tok = None
            if ref is not None and prompt is not None and prompt in ref:
                cont = ref[prompt]["cont"]
                ref_tok = cont[pos] if pos < len(cont) else None
            if alt is not None and pi < len(alt) and pos < len(alt[pi]):
                alt_tok = alt[pi][pos]
            cuda_ok = None if ref_tok is None else a == ref_tok
            vk_ok = None if ref_tok is None else b == ref_tok
            cuda_alt = None if alt_tok is None else a == alt_tok
            # Attribution: which named difference explains this position.
            explained_by, confidence, follow_up = None, None, None
            if cuda_ok is False and vk_ok is True:
                if cuda_alt:
                    explained_by, confidence = "either-mode-ambiguity", "evidence"
                else:
                    follow_up = "CUDA misses a position Vulkan matches: open CUDA follow-up"
            elif cuda_ok is True and vk_ok is False:
                follow_up = "M3-T5"
                if f16 is not None:
                    arm_tok = f16[pi]["argmax"][pos]
                    if arm_tok == b:
                        # The f16 GEMM picks the same token as the int8 one: quantization is not the cause.
                        explained_by, confidence = "no-coop-matrices", "arm (STRATA_MMQ= does not move it)"
                    else:
                        explained_by, confidence = "gemm-int8-vs-f16", "arm (STRATA_MMQ= moves it)"
                else:
                    explained_by, confidence = "gemm-int8-vs-f16", "registry (no arm evidence)"
            elif ref_tok is not None:
                follow_up = "both backends miss the reference here: open follow-up"
            d = {
                "prompt": pi + 1,  # 1-based, as the parity table in docs/V100-results.md numbers prompts
                "prompt_text": cr["prompt"],
                "position": pos,
                "cuda_token": a,
                "vulkan_token": b,
                "reference_token": ref_tok,
                "alt_token": alt_tok,
                "cuda_matches_reference": cuda_ok,
                "vulkan_matches_reference": vk_ok,
                "cuda_matches_alt": cuda_alt,
                "explained_by": explained_by,
                "confidence": confidence,
                "follow_up": follow_up,
            }
            for name, row in (("cuda", cr), ("vulkan", vr)):
                top5 = row.get("top5")
                if top5 is not None and pos < len(top5):
                    d[f"{name}_top5"] = [[t, fnum(lp)] for t, lp in top5[pos]]
                    d[f"{name}_top5_gap"] = fnum(top5[pos][0][1] - top5[pos][1][1])
                else:
                    d[f"{name}_top5"] = None
                    d[f"{name}_top5_gap"] = None
            out.append(d)
    return out


# ---------------------------------------------------------------- per-op log aggregation

RE_RUN = re.compile(r"^(?:running \d+ tests?|test .* \.\.\.|test result:|$)")
RE_BACKEND = re.compile(r"(?:^|\s)backend (cuda|vulkan)\b")
NUM = r"(-?[\d.]+(?:e[-+]?\d+)?)"

# Each entry: (compiled regex, builder(match) -> (op, case, column, metric, value, explained_by))
# `column` is one of cuda_vs_cpu, vulkan_vs_cpu, cuda_vs_vulkan. `{bk}` in the line resolves to the
# section's backend; a cross line names both backends explicitly.
# Ops whose cross-backend figure is a known same-math reduction-order difference rather than a fault.
REGISTRY_HINT = {"conv": "summation-order", "conv_state": "summation-order", "conv_seq": "summation-order",
                 "conv_l2_norm": "summation-order", "moe_gemv": "expert-slot-layout",
                 "moe_combine": "expert-slot-layout", "ssm_gates": "summation-order",
                 "ssm_gates_g": "summation-order", "router_topk": None, "swiglu": None, "add": None,
                 "rms_norm": None, "l2_norm": None, "rope_neox": None, "norm_gate": None}

PATTERNS = [
    # tests/kernels.rs:56 / :66 — dequant + GEMV per type
    (re.compile(r"^\s*(\w+)\s+(\S+): dequant max diff " + NUM + r", gemv rel err " + NUM),
     lambda m, bk: [("dequant+gemv", f"{m[1]} {m[2]}", f"{bk}_vs_cpu", "max_abs", float(m[3]), None),
                    ("dequant+gemv", f"{m[1]} {m[2]}", f"{bk}_vs_cpu", "rel_l2", float(m[4]), None)]),
    # tests/kernels.rs:56 — GEMV not implemented on this backend
    (re.compile(r"^\s*(\w+)\s+(\S+): dequant max diff " + NUM + r", (.*not implemented.*)$"),
     lambda m, bk: [("dequant+gemv", f"{m[1]} {m[2]}", f"{bk}_vs_cpu", "max_abs", float(m[3]), None)]),
    # tests/kernels.rs:393 — GEMM vs the CPU reference for one backend
    (re.compile(r"^\s*(\w+)\s+(\S+): gemm rel err " + NUM),
     lambda m, bk: [("gemm", f"{m[1]} {m[2]}", f"{bk}_vs_cpu", "rel_l2", float(m[3]), None)]),
    # tests/kernels.rs:409/:422 — cross-backend GEMM, named mechanism
    (re.compile(r"^\s*(\w+)\s+(\S+): (cuda|vulkan) vs (cuda|vulkan) \((.*?)(?:, recorded)?\): rel err " + NUM),
     lambda m, bk: [("gemm", f"{m[1]} {m[2]} [{m[5]}]", cross_col(m[3], m[4], bk), "rel_l2", float(m[6]),
                     {"different f16 input conversion": "f16-round-vs-trunc",
                      "different GEMM math": "gemm-int8-vs-f16"}.get(m[5], "summation-order"))]),
    # tests/kernels.rs:413 — cross-backend GEMM on the same math (tolerance only because sm_70)
    (re.compile(r"^\s*(\w+)\s+(\S+): gemm on (cuda|vulkan) vs (cuda|vulkan) \(same math\): rel err " + NUM),
     lambda m, bk: [("gemm", f"{m[1]} {m[2]} [same math]", cross_col(m[3], m[4], bk), "rel_l2", float(m[5]),
                     "summation-order")]),
    # tests/kernels.rs:545 — cross-backend prefill attention
    (re.compile(r"^attn_prefill (cuda|vulkan) vs (cuda|vulkan) pos (\d+) nh (\d+) nkv (\d+) hd (\d+): rel err " + NUM),
     lambda m, bk: [("attn_prefill", f"pos {m[3]} nh {m[4]} nkv {m[5]} hd {m[6]}",
                     cross_col(m[1], m[2], bk), "rel_l2", float(m[7]), "summation-order")]),
    # tests/kernels.rs:585 — decode attention vs CPU, plus differing bits from the first backend
    (re.compile(r"^attn_decode pos (\d+) nh (\d+) nkv (\d+) hd (\d+) gq_min (-?\d+): rel err vs CPU " + NUM
                + r", (\d+) of (\d+) differ from the first backend"),
     lambda m, bk: [("attn_decode", f"pos {m[1]} nh {m[2]} nkv {m[3]} hd {m[4]} gq_min {m[5]}",
                     f"{bk}_vs_cpu", "rel_l2", float(m[6]), None),
                    ("attn_decode", f"pos {m[1]} nh {m[2]} nkv {m[3]} hd {m[4]} gq_min {m[5]}",
                     "cuda_vs_vulkan", "differing_bits", int(m[7]), "same-kernel (bit-exact)")]),
    # tests/kernels.rs:614 — prefill vs decode, same backend
    (re.compile(r"^attn_prefill_(\d+) nh (\d+) nkv (\d+) gq_min (-?\d+): rel err vs decode " + NUM),
     lambda m, bk: [("attn_prefill_vs_decode", f"hd {m[1]} nh {m[2]} nkv {m[3]} gq_min {m[4]}",
                     f"{bk}_vs_cpu", "rel_l2", float(m[5]), "summation-order")]),
    # tests/kernels.rs:677 — DeltaNet vs CPU, plus differing bits from the first backend
    (re.compile(r"^deltanet ilv (\w+) vs CPU: out " + NUM + r", state " + NUM
                + r"; differ from the first backend: out (\d+) of (\d+), state (\d+) of (\d+); steps: out (\d+), state (\d+)"),
     lambda m, bk: [("deltanet", f"ilv {m[1]}", f"{bk}_vs_cpu", "rel_l2", float(m[2]), None),
                    ("deltanet", f"ilv {m[1]}", "cuda_vs_vulkan", "differing_bits", int(m[4]), "same-kernel (bit-exact)")]),
    # tests/kernels.rs:1640 — dense GEMM per backend
    (re.compile(r"^(cuda|vulkan): gemm_dense rel err " + NUM),
     lambda m, bk: [("gemm_dense", "dense 4096", f"{m[1]}_vs_cpu", "rel_l2", float(m[2]), None)]),
    # tests/llama_numerics.rs:99 — llama-mode decode vs the CPU model, default kernel for contrast
    (re.compile(r"^n_pos (\d+) gq_min (-?\d+): llama mode vs CPU model " + NUM + r", default kernel vs CPU model " + NUM),
     lambda m, bk: [("attn_decode_llama", f"n_pos {m[1]} gq_min {m[2]}", "llama_vs_cpu", "rel_l2", float(m[3]), None),
                    ("attn_decode_llama", f"n_pos {m[1]} gq_min {m[2]}", "default_vs_cpu", "rel_l2", float(m[4]), None)]),
    # tests/llama_numerics.rs:147 — llama-mode prefill is f32 vs f64 reference
    (re.compile(r"^prefill hd (\d+): llama mode vs f64 " + NUM + r", tensor-core kernel vs f64 " + NUM),
     lambda m, bk: [("attn_prefill_llama", f"hd {m[1]}", "llama_vs_cpu", "rel_l2", float(m[2]), None),
                    ("attn_prefill_llama", f"hd {m[1]}", "default_vs_cpu", "rel_l2", float(m[3]), None)]),
    # tests/kernels.rs — measurement-only lines added by M2-T7 ("op <name> <bk> [<case>]: ...")
    (re.compile(r"^op (\w+) (cuda|vulkan) \[(.*)\]: rel err vs CPU " + NUM + r", (\d+) of (\d+) differ from the first backend"),
     lambda m, bk: [(m[1], m[3], f"{m[2]}_vs_cpu", "rel_l2", float(m[4]), REGISTRY_HINT.get(m[1])),
                    (m[1], m[3], "cuda_vs_vulkan", "differing_bits", int(m[5]), REGISTRY_HINT.get(m[1]))]),
    (re.compile(r"^op (\w+) (cuda|vulkan) \[(.*)\]: max abs " + NUM + r", (\d+) of (\d+) differ from the first backend"),
     lambda m, bk: [(m[1], m[3], f"{m[2]}_vs_cpu", "max_abs", float(m[4]), REGISTRY_HINT.get(m[1])),
                    (m[1], m[3], "cuda_vs_vulkan", "differing_bits", int(m[5]), REGISTRY_HINT.get(m[1]))]),
    (re.compile(r"^op (\w+) (cuda|vulkan) \[(.*)\]: (\d+) of (\d+) differ from the first backend"),
     lambda m, bk: [(m[1], m[3], "cuda_vs_vulkan", "differing_bits", int(m[4]), REGISTRY_HINT.get(m[1]))]),
    # tests/kv_q8.rs:79 — q8 KV vs f16 KV
    (re.compile(r"^nh (\d+) nkv (\d+) hd (\d+) kernel (\d+): q8 vs f16 decode " + NUM
                + r", q8 prefill vs decode " + NUM),
     lambda m, bk: [("kv_q8", f"nh {m[1]} nkv {m[2]} hd {m[3]} kernel {m[4]}", "q8_vs_f16", "rel_l2", float(m[5]), "q8-kv"),
                    ("kv_q8", f"nh {m[1]} nkv {m[2]} hd {m[3]} kernel {m[4]}", "q8_prefill_vs_decode", "rel_l2", float(m[6]), "q8-kv")]),
]


def cross_col(a, b, bk):
    pair = {a, b}
    if pair == {"cuda", "vulkan"}:
        return "cuda_vs_vulkan"
    return f"{a}_vs_{b}"


def parse_kernels(paths):
    """Flat per-op records from the `--nocapture` logs.

    Lines that carry a measurement (`rel err`, `max diff`, `differ`, ...) but match no pattern are
    returned as `unparsed` instead of being guessed: a silent parser miss would drop a per-op row
    from the report, so the caller stores them and the report shows the count.
    """
    records, unparsed, skipped, backend = [], [], [], None
    for path in paths:
        for line in open(path, errors="replace"):
            line = line.rstrip("\n")
            m = RE_BACKEND.search(line)
            if m:
                backend = m.group(1)
                continue
            if line.startswith("SKIP:"):
                skipped.append(line)
                continue
            if not line.strip() or RE_RUN.match(line):
                continue
            hit = False
            for rx, build in PATTERNS:
                m = rx.match(line)
                if not m:
                    continue
                hit = True
                for op, case, col, metric, value, expl in build(m, backend or "unknown"):
                    if col == "cuda_vs_vulkan" and backend == "cuda" and metric == "differing_bits":
                        continue  # the first backend is the baseline: its count is 0 by construction
                    records.append({
                        "op": op, "case": case, "comparison": col, "metric": metric,
                        "value": value, "explained_by": expl,
                    })
                break
            if not hit and re.search(r"rel err|max diff|differ|\bof\b", line):
                unparsed.append(line.strip())
    if backend is None:
        sys.exit(f"no `backend cuda|vulkan` header in {paths}: is this a --nocapture test log?")
    return records, unparsed, skipped


def pivot(records):
    """Split the flat records into the three-column per-op table and the other measurements.

    `rows`: one entry per (op, case) with the CUDA-vs-CPU, Vulkan-vs-CPU and CUDA-vs-Vulkan
    figures; `other`: the comparisons that do not fit those three columns (`llama_vs_cpu`,
    `q8_vs_f16`, ...), kept as their own rows instead of being dropped.
    """
    rows = {}
    for r in records:
        key = (r["op"], r["case"])
        row = rows.setdefault(key, {"op": r["op"], "case": r["case"], "cells": {}, "explained_by": None})
        col = r["comparison"]
        if col.startswith("unknown_"):
            sys.exit(f"per-op log line outside a `backend cuda|vulkan` section: {r}")
        row["cells"].setdefault(col, {})[r["metric"]] = r["value"]
        if r["explained_by"] and col == "cuda_vs_vulkan":
            row["explained_by"] = r["explained_by"]
    three = ("cuda_vs_cpu", "vulkan_vs_cpu", "cuda_vs_vulkan")
    main, other = [], []
    for (op, case), row in sorted(rows.items()):
        three_cells = {k: row["cells"][k] for k in three if k in row["cells"]}
        if three_cells:
            main.append({"op": op, "case": case, "cells": three_cells,
                         "explained_by": row["explained_by"]})
        for col, cell in row["cells"].items():
            if col not in three:
                other.append({"op": op, "case": case, "comparison": col, "values": cell,
                              "explained_by": row["explained_by"] if col.endswith("_vs_cpu") else None})
    return main, other


def cell_text(cell):
    """`L2 1.2e-07 / max 7.6e-06 / 0 bits` for one per-op cell."""
    if not cell:
        return "n/a"
    parts = []
    for k in ("rel_l2", "max_abs", "differing_bits"):
        if k in cell:
            label = {"rel_l2": "L2", "max_abs": "max", "differing_bits": "bits"}[k]
            v = cell[k]
            parts.append(f"{v} bits" if k == "differing_bits" else f"{label} {v:.2e}")
    return " / ".join(parts)


# ---------------------------------------------------------------- KLD (perplexity --kld-base)

def read_kld(path):
    """Read a `perplexity --kld-base` file (src/main.rs:530-568) without copying the logits."""
    data = open(path, "rb").read()
    if data[:8] != b"_logits_":
        sys.exit(f"{path}: not a --kld-base file (bad magic)")
    n, nv, n_chunk = struct.unpack_from("<3I", data, 8)
    off = 20
    ids = struct.unpack_from(f"<{n_chunk * n}I", data, off)
    off += 4 * n_chunk * n
    first = n // 2
    count = n_chunk * (n - 1 - first)
    need = off + 4 * count * nv
    if len(data) < need:
        sys.exit(f"{path}: truncated ({len(data)} bytes, expected {need})")
    logp = memoryview(data)[off:need].cast("f")  # zero-copy view over the bytes object
    return {"n": n, "nv": nv, "n_chunk": n_chunk, "ids": ids, "count": count, "logp": logp}


def kld_table(a, b):
    """Mean KLD, RMS Δp and top-1 agreement between two log-probability dumps (pure Python)."""
    if (a["n"], a["nv"], a["n_chunk"], a["ids"]) != (b["n"], b["nv"], b["n_chunk"], b["ids"]):
        sys.exit("KLD files score different tokens (n/nv/n_chunk/ids differ)")
    nv = a["nv"]
    exp = math.exp
    total_kld = max_kld = total_rms = max_rms = 0.0
    sum_pa = sum_pb = 0.0
    top1_same = 0
    # Top-1 is the argmax of the log-probabilities; ties resolve to the lower id on both sides.
    for pos in range(a["count"]):
        va = a["logp"][pos * nv:(pos + 1) * nv]
        vb = b["logp"][pos * nv:(pos + 1) * nv]
        kld = rms = 0.0
        spa = spb = 0.0
        (ma, mb) = (va[0], vb[0])
        (ia, ib) = (0, 0)
        for i in range(nv):
            x, y = va[i], vb[i]
            ex = exp(x)
            ey = exp(y)
            spa += ex
            spb += ey
            kld += ex * (x - y)
            d = ex - ey
            rms += d * d
            if x > ma:
                ma, ia = x, i
            if y > mb:
                mb, ib = y, i
        sum_pa += spa
        sum_pb += spb
        total_kld += kld
        total_rms += rms
        max_kld = max(max_kld, kld)
        max_rms = max(max_rms, rms)
        top1_same += ia == ib
        if pos and pos % 50 == 0:
            print(f"  kld {pos}/{a['count']}", file=sys.stderr, flush=True)
    return {
        "positions": int(a["count"]),
        "n_vocab": int(nv),
        "mean_kld": total_kld / a["count"],
        "max_kld": max_kld,
        "mean_rms_dp": total_rms / a["count"],
        "max_rms_dp": max_rms,
        "top1_agreement": top1_same / a["count"],
        "top1_differing": int(a["count"] - top1_same),
        "mean_sum_p_base": sum_pa / a["count"],
        "mean_sum_p_other": sum_pb / a["count"],
        "note": "KLD per position = sum_v p_a * (log p_a - log p_b); p = exp(log p) of the kld-base dump",
    }


# ---------------------------------------------------------------- output

def pct(a, b):
    return round(100.0 * a / b, 2) if b else None


def summary(c, v, div, arms, per_op, other_measurements, unparsed, skipped, kld, args):
    d = {
        "version": VERSION,
        "kind": "cross-backend numerical consistency",
        "issue": "#36 (M2-T7)",
        "date": args.date,
        "generator": "tools/consistency.py",
        "status": args.status,
        "note": ("Computed on the M2 build in the M2-T7 GPU window (2026-11-08): both backends re-run "
                 "on the same cached reference, plus the STRATA_MMQ= (f16 GEMM) and STRATA_GEMM_FMA=1 "
                 "attribution arms. Per-op rows come from the --nocapture logs of tests/kernels.rs and "
                 "tests/llama_numerics.rs." if args.status == "m2" else
                 "Computed from the pre-M2 artifacts (CUDA from M1 ae95739, Vulkan from M0 d6c2beb): "
                 "a CPU dry run that reproduces the documented 9/640. History only; the M2-T7 GPU "
                 "window replaces this file with the current-build run."),
        "inputs": {
            "cuda": {"tag": args.cuda_tag, "file": c["file"], "total": c["total"],
                     "agree": c["agree"], "either": c["either"],
                     "strict_pct": pct(c["agree"], c["total"]), "either_pct": pct(c["either"], c["total"])},
            "vulkan": {"tag": args.vulkan_tag, "file": v["file"], "total": v["total"],
                       "agree": v["agree"], "either": v["either"],
                       "strict_pct": pct(v["agree"], v["total"]), "either_pct": pct(v["either"], v["total"])},
            "reference": args.ref if args.ref else None,
            "alt": args.alt if args.alt else None,
        },
        "end_to_end": {
            "total": c["total"],
            "divergent": len(div),
            "divergent_pct": pct(len(div), c["total"]),
            "cuda_only_correct": sum(1 for d0 in div if d0["cuda_matches_reference"] and not d0["vulkan_matches_reference"]),
            "vulkan_only_correct": sum(1 for d0 in div if d0["vulkan_matches_reference"] and not d0["cuda_matches_reference"]),
            "both_wrong": sum(1 for d0 in div if d0["cuda_matches_reference"] is False and d0["vulkan_matches_reference"] is False),
            "missing_top5": any(d0["cuda_top5"] is None for d0 in div),
        },
        "divergences": div,
        "arms": arms,
        "per_op": per_op,
        "other_measurements": other_measurements,
        "per_op_unparsed": unparsed,
        "per_op_skipped": skipped,
        "registry": REGISTRY,
        "unexplained": [d0 for d0 in div if not d0["explained_by"]],
        "follow_ups": sorted({d0["follow_up"] for d0 in div if d0["follow_up"]}),
        "kld": kld,
    }
    return d


def md_kld(k):
    return "\n".join([
        "### Full-vocabulary KLD between the backends",
        "",
        f"{k['positions']} positions, vocabulary {k['n_vocab']}: mean KLD {k['mean_kld']:.3e} "
        f"(max {k['max_kld']:.3e}), mean RMS Δp {k['mean_rms_dp']:.3e} (max {k['max_rms_dp']:.3e}), "
        f"top-1 agreement {100 * k['top1_agreement']:.2f} % ({k['top1_differing']} positions differ); "
        f"mean Σp {k['mean_sum_p_base']:.6f} vs {k['mean_sum_p_other']:.6f} (1.0 = normalized dumps).",
        "",
    ])


def md(s):
    if "end_to_end" not in s:  # --kld only
        return md_kld(s["kld"])
    o = []
    o.append(f"### Cross-backend summary ({s['date']}, {s['status']})")
    o.append("")
    i = s["inputs"]
    o.append("| backend | tag | strict | either | divergent vs the other backend |")
    o.append("| --- | --- | ---: | ---: | ---: |")
    o.append(f"| CUDA sm_70 | `{i['cuda']['tag']}` | {i['cuda']['agree']}/{i['cuda']['total']} "
             f"({i['cuda']['strict_pct']} %) | {i['cuda']['either']}/{i['cuda']['total']} "
             f"({i['cuda']['either_pct']} %) | {s['end_to_end']['divergent']} of {s['end_to_end']['total']} "
             f"({s['end_to_end']['divergent_pct']} %) |")
    o.append(f"| Vulkan sm_70 | `{i['vulkan']['tag']}` | {i['vulkan']['agree']}/{i['vulkan']['total']} "
             f"({i['vulkan']['strict_pct']} %) | {i['vulkan']['either']}/{i['vulkan']['total']} "
             f"({i['vulkan']['either_pct']} %) | same positions |")
    o.append("")
    e = s["end_to_end"]
    o.append(f"- CUDA matches the reference and Vulkan does not: {e['cuda_only_correct']}")
    o.append(f"- Vulkan matches the reference and CUDA does not: {e['vulkan_only_correct']}")
    o.append(f"- both miss the reference: {e['both_wrong']}")
    o.append(f"- unexplained: {len(s['unexplained'])}")
    if e["missing_top5"]:
        o.append("- top-5 logprobs: not captured in these artifacts (`tools/parity.py` records them per "
                 "position only from this change on); regenerate the artifacts to fill the gaps")
    o.append("")
    o.append("### Divergent positions")
    o.append("")
    o.append("| # | prompt | pos | CUDA | Vulkan | reference | alt | explained by | CUDA top-5 gap | Vulkan top-5 gap |")
    o.append("| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |")
    for d0 in s["divergences"]:
        def g(x):
            return "n/a" if x is None else f"{x:.4g}"
        o.append(f"| {d0['prompt']} | {d0['prompt_text']} | {d0['position']} | {d0['cuda_token']} | "
                 f"{d0['vulkan_token']} | {d0['reference_token']} | {d0['alt_token']} | "
                 f"`{d0['explained_by']}` | {g(d0['cuda_top5_gap'])} | {g(d0['vulkan_top5_gap'])} |")
    o.append("")
    if s["arms"]:
        o.append("### Attribution arms")
        o.append("")
        o.append("| arm | file | strict | either | divergent vs CUDA | base divergences resolved | still divergent |")
        o.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for a in s["arms"]:
            o.append(f"| `{a['name']}` | `{a['file']}` | {a['agree']}/{a['total']} | {a['either']}/{a['total']} | "
                     f"{a['divergent']} | {a['resolved']} | {a['divergent']} |")
        o.append("")
    if s["per_op"]:
        ops = sorted({r["op"] for r in s["per_op"]})
        o.append("### Per-op table")
        o.append("")
        for op in ops:
            o.append(f"**{op}**")
            o.append("")
            o.append("| case / shape | CUDA vs CPU | Vulkan vs CPU | CUDA vs Vulkan | explained by |")
            o.append("| --- | ---: | ---: | ---: | --- |")
            for r in [x for x in s["per_op"] if x["op"] == op]:
                c = r["cells"]
                o.append(f"| `{r['case']}` | {cell_text(c.get('cuda_vs_cpu'))} | "
                         f"{cell_text(c.get('vulkan_vs_cpu'))} | {cell_text(c.get('cuda_vs_vulkan'))} | "
                         f"{('`' + r['explained_by'] + '`') if r['explained_by'] else '—'} |")
            o.append("")
        if s["other_measurements"]:
            o.append("**Other measurements** (comparisons that are not CUDA/Vulkan vs the CPU reference)")
            o.append("")
            o.append("| op | case / shape | comparison | value |")
            o.append("| --- | --- | --- | --- |")
            for r in s["other_measurements"]:
                o.append(f"| {r['op']} | `{r['case']}` | {r['comparison']} | {cell_text(r['values'])} |")
            o.append("")
        if s["per_op_unparsed"]:
            o.append(f"{len(s['per_op_unparsed'])} measurement line(s) in the logs matched no per-op "
                     "pattern and are listed in the JSON (`per_op_unparsed`), not dropped silently.")
            o.append("")
    else:
        o.append("### Per-op table")
        o.append("")
        o.append("Not generated: run with `--kernels <log>` on the `--nocapture` outputs of "
                 "`tests/kernels.rs` and `tests/llama_numerics.rs`.")
        o.append("")
    o.append("### Legitimate-difference registry")
    o.append("")
    o.append("| id | mechanism | measured | arm that isolates it | follow-up |")
    o.append("| --- | --- | --- | --- | --- |")
    for r in s["registry"]:
        o.append(f"| `{r['id']}` | {r['title']} | {r['measured']} | {r['arm'] or '—'} | {r['follow_up'] or '—'} |")
    o.append("")
    o.append("### Unexplained")
    o.append("")
    if s["unexplained"]:
        for d0 in s["unexplained"]:
            o.append(f"- prompt {d0['prompt']} pos {d0['position']}: CUDA {d0['cuda_token']}, "
                     f"Vulkan {d0['vulkan_token']}, reference {d0['reference_token']}")
    else:
        o.append("None: every divergent position is attributed to a registry entry above.")
    o.append("")
    if s["kld"]:
        o.append(md_kld(s["kld"]))
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser(description="Cross-backend numerical consistency report (M2-T7).")
    ap.add_argument("--cuda", help="target/parity-result-<tag>.json of the CUDA sm_70 run")
    ap.add_argument("--vulkan", help="target/parity-result-<tag>.json of the Vulkan sm_70 run")
    ap.add_argument("--cuda-tag", default="cuda")
    ap.add_argument("--vulkan-tag", default="vulkan")
    ap.add_argument("--ref", default="target/parity-ref.json", help="llama.cpp reference cache")
    ap.add_argument("--alt", default="target/llama-batch-argmax.json", help="llama.cpp one-batch argmax")
    ap.add_argument("--prompts", default="tools/prompts.json", help="prompt list, same order as the runs")
    ap.add_argument("--out", default="docs/parity/cross-backend.json", help="machine-readable summary")
    ap.add_argument("--markdown", default="-", help="write the markdown rows here ('-' = stdout)")
    ap.add_argument("--kernels", action="append", default=[], help="--nocapture test log (repeatable)")
    ap.add_argument("--arm", action="append", default=[], metavar="NAME=FILE",
                    help="attribution arm result file, compared against --cuda (repeatable)")
    ap.add_argument("--f16-arm", metavar="FILE",
                    help="Vulkan STRATA_MMQ= (f16 GEMM) parity result; decides int8-vs-same-math attribution")
    ap.add_argument("--kld", nargs=2, metavar=("BASE", "OTHER"), help="two perplexity --kld-base files")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--status", default="pre-m2", choices=["pre-m2", "m2", "dry-run"],
                    help="what the artifacts are: pre-M2 history, the M2 window, or a local dry run")
    args = ap.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent

    def rel(p):
        """Report a path relative to the repository when it is inside it, else as given."""
        r = pathlib.Path(p).resolve()
        try:
            return str(r.relative_to(root))
        except ValueError:
            return str(r)

    def rp(p):
        """Resolve a default path against the repository root, an explicit one as given."""
        return pathlib.Path(p) if pathlib.Path(p).is_absolute() else root / p

    kld = None
    if args.kld:
        kld = kld_table(read_kld(args.kld[0]), read_kld(args.kld[1]))

    if not (args.cuda and args.vulkan):
        if kld is None:
            sys.exit("need --cuda and --vulkan (parity comparison) or --kld (logit comparison)")
        so = {"version": VERSION, "kind": "cross-backend numerical consistency (KLD only)",
              "issue": "#36 (M2-T7)", "date": args.date, "generator": "tools/consistency.py",
              "status": args.status, "kld": kld}
        if args.out:
            pathlib.Path(args.out).write_text(json.dumps(so, indent=1) + "\n")
        text = md(so)
        if args.markdown == "-":
            print(text)
        elif args.markdown:
            pathlib.Path(args.markdown).write_text(text + "\n")
        return

    c, v = load_parity(args.cuda), load_parity(args.vulkan)
    same_layout(c, v)
    ref = json.load(open(rp(args.ref))) if rp(args.ref).is_file() else None
    alt = json.load(open(rp(args.alt))) if rp(args.alt).is_file() else None
    prompts = json.load(open(rp(args.prompts))) if rp(args.prompts).is_file() else None
    c["file"], v["file"] = rel(args.cuda), rel(args.vulkan)

    f16 = None
    if args.f16_arm:
        if not pathlib.Path(args.f16_arm).is_file():
            sys.exit(f"--f16-arm {args.f16_arm}: no such file")
        f16 = load_parity(args.f16_arm)["rows"]
        same_layout(c, {"rows": f16})
    div = divergences(c, v, ref, alt, prompts, f16)

    arms = []
    for spec in args.arm:
        name, _, path = spec.partition("=")
        if not path or not pathlib.Path(path).is_file():
            sys.exit(f"--arm {spec}: no such file")
        a = load_parity(path)
        same_layout(c, a)
        ad = divergences(c, a, ref, alt, prompts, f16)
        base = {(d0["prompt"], d0["position"]) for d0 in div}
        arm_pos = {(d0["prompt"], d0["position"]) for d0 in ad}
        arms.append({
            "name": name, "file": rel(path), "total": a["total"], "agree": a["agree"], "either": a["either"],
            "divergent": len(ad),
            "resolved": len(base - arm_pos),
            "unexplained": sum(1 for d0 in ad if not d0["explained_by"]),
        })

    per_op, other_measurements, unparsed, skipped = [], [], [], []
    if args.kernels:
        records, unparsed, skipped = parse_kernels(args.kernels)
        per_op, other_measurements = pivot(records)

    s = summary(c, v, div, arms, per_op, other_measurements, unparsed, skipped, kld, args)
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(s, indent=1) + "\n")

    text = md(s)
    if args.markdown == "-":
        print(text)
    elif args.markdown:
        pathlib.Path(args.markdown).write_text(text + "\n")
        print(f"wrote {args.markdown}")

    print(f"\ncross-backend: {len(div)} of {c['total']} positions differ "
          f"({pct(len(div), c['total'])} %); unexplained: {len(s['unexplained'])}", file=sys.stderr)
    for d0 in div:
        print(f"  prompt {d0['prompt']:2} pos {d0['position']:2}: CUDA {d0['cuda_token']:6} "
              f"Vulkan {d0['vulkan_token']:6} reference {d0['reference_token']} "
              f"({d0['explained_by'] or 'UNEXPLAINED'})", file=sys.stderr)
    if s["unexplained"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
