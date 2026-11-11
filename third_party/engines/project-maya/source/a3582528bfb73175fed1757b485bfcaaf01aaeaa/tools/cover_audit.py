"""tools/cover_audit.py - which guarded branches does a fixture's forward actually fire?

The second-opinion review's item 1: a green gate proves nothing about a branch the fixture never
enters.  ref/glm.py counts every guarded branch into the module-level COVER counter; this script
runs the oracle over sequences of increasing length and reports the counts.

    python tools/cover_audit.py [MODEL.gguf]

Without an argument it builds the seed-1234 synthetic.  Run it on EVERY fixture used by parity
tests (seed-1234 AND the big `--big` synthetic): a branch that stays zero across ALL fixtures
cannot be called tested.  `moe_renorm_clamp_hits` is informational everywhere: the clamp fires
only when EVERY selected expert's probability is below 2**-14 at once, which sigmoid gating
essentially cannot produce - it is a numerical safety net, not a reachable branch.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ref"))

import glm_synth_gguf  # noqa: E402
from glm import COVER, Glm5Next  # noqa: E402

REQUIRED = {
    "swiglu_gate_clamp_hits": "the routed/dense SwiGLU gate clamp (min(gate, limit))",
    "swiglu_up_clamp_hits": "the SwiGLU up clamp (clamp(up, +/-limit))",
    "kda_gate_saturated": "KDA decay gates sitting on the structural lower bound",
    "moe_selection_near_ties": "router selections where ranks n_used/n_used+1 differ by < 1e-4",
    "dsa_topk_discard_queries": "queries with more completed pools than top_k/kpool",
    "dsa_pool_boundaries_crossed": "k-pool boundaries crossed by the sequence",
}
INFORMATIONAL = {
    "moe_renorm_clamp_hits": "2**-14 renorm-sum clamp (safety net; needs every selected prob "
                             "below 2**-14 at once - sigmoid gating cannot produce that)",
}


def main() -> int:
    if len(sys.argv) > 1:
        model_path = pathlib.Path(sys.argv[1])
        tmp = None
    else:
        tmp = tempfile.TemporaryDirectory(prefix="strata-cover-")
        model_path = pathlib.Path(tmp.name) / "glm5-synth.gguf"
        md, ts = glm_synth_gguf.build(seed=1234)
        glm_synth_gguf.write_gguf(model_path, md, ts)

    zero: set[str] = set(REQUIRED)
    try:
        model = Glm5Next(model_path)
        n_vocab = model.t("token_embd.weight").shape[0]
        for n in (8, 12, 32, 128, 300, 512):
            if n >= n_vocab:
                break
            COVER.clear()
            model.forward([(i % (n_vocab - 1)) + 1 for i in range(n)])
            print(f"--- {n} tokens")
            for key in sorted(set(REQUIRED) | set(INFORMATIONAL) | set(COVER)):
                print(f"  {key:32s} {COVER[key]:8d}")
            zero -= {k for k, v in COVER.items() if v > 0}
        model.g.close()
    finally:
        if tmp:
            tmp.cleanup()

    for key in sorted(zero):
        print(f"ZERO {key}: {REQUIRED[key]}")
    if zero:
        print("FAIL: branches above never fired on this fixture")
        return 1
    print("pass: every required branch fired at some length")
    return 0


if __name__ == "__main__":
    sys.exit(main())
