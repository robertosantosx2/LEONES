#!/usr/bin/env python3
"""Compare raw f32 dumps: llama-debug (DEBUG_DUMP_DIR, local patch in common/debug.cpp) vs ds_run (STRATA_DS_DUMP).
usage: cmp_dump.py ref_dir mine_dir [tokens]
Per tensor: relative L2 error and worst abs diff. Tensors are ordered by layer so the first bad one is the culprit."""
import array, math, os, re, sys
ref, mine = sys.argv[1], sys.argv[2]
def load(p):
    a = array.array("f"); a.frombytes(open(p, "rb").read()); return a
def key(n):
    m = re.match(r"(.*?)(?:-(\d+))?\.f32$", n)
    return (int(m.group(2)) if m.group(2) else -1, n)
for n in sorted(os.listdir(mine), key=key):
    if not os.path.exists(f"{ref}/{n}"):
        continue
    a, b = load(f"{ref}/{n}"), load(f"{mine}/{n}")
    if len(a) != len(b):
        # result_output etc.: llama keeps only the last token
        k = min(len(a), len(b))
        # comp_latent: llama appends an extra trailing row, keep the head; others keep only the last token
        a, b = (a[:k], b[:k]) if n.startswith('comp_latent') else (a[-k:], b[-k:])
    num = sum((x - y) ** 2 for x, y in zip(a, b)); den = sum(x * x for x in a) + 1e-30
    mx = max(abs(x - y) for x, y in zip(a, b))
    print(f"{n[:-4]:22s} n={len(a):7d} rel_l2={math.sqrt(num/den):.2e} max_abs={mx:.3e} ref_rms={math.sqrt(den/len(a)):.3e}")
