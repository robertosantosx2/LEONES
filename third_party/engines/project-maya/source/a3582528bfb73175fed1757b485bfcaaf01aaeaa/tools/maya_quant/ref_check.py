"""tools/maya_quant/ref_check.py - is calib.py's FP8 reference a sane language model?  Per eval sequence: the NLL of the
actual next tokens under the reference's top-k (a token outside the top-k is counted at the k-th log-prob, a lower
bound on its loss), how often the next token is the reference's top token, and how much probability the top-k holds.
A broken head (wrong norm, wrong stream mix) shows as perplexity in the hundreds and top-1 near zero.

    python ref_check.py --eval eval.npy --ref ref_topk.npz
"""
import argparse

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    ev = np.load(a.eval)
    r = np.load(a.ref)
    lp, ids = r["logprob"], r["ids"]
    tot_nll, tot_n, tot_top1, tot_in = 0.0, 0, 0, 0
    for s in range(ev.shape[0]):
        nxt = ev[s, 1:]
        rows_lp, rows_id = lp[s, :-1], ids[s, :-1]
        hit = rows_id == nxt[:, None]
        inside = hit.any(1)
        nll = np.where(inside, -(rows_lp * hit).sum(1), -rows_lp[:, -1])
        mass = np.exp(rows_lp).sum(1)
        top1 = (rows_id[:, 0] == nxt).mean()
        print(f"seq {s:2d}: ppl <= {np.exp(nll.mean()):8.2f}  top1 {100 * top1:5.1f}%  next in top-k {100 * inside.mean():5.1f}%"
              f"  top-k mass {mass.mean():.3f}")
        tot_nll += nll.sum()
        tot_n += len(nll)
        tot_top1 += (rows_id[:, 0] == nxt).sum()
        tot_in += inside.sum()
    print(f"ALL: ppl <= {np.exp(tot_nll / tot_n):.2f}  top1 {100 * tot_top1 / tot_n:.1f}%  next in top-k {100 * tot_in / tot_n:.1f}%")


if __name__ == "__main__":
    main()
