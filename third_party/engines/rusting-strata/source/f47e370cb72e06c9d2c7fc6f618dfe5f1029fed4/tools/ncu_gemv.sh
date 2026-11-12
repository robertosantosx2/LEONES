#!/bin/sh
# M2-T5 (issue #30): per-kernel DRAM attribution of one short CUDA decode run.
# Usage: tools/ncu_gemv.sh <model.gguf> [outdir]     (default outdir: target/ncu_m2t5)
#
# `ncu` is installed with the toolkit but not on PATH (2025.2.1 at /usr/local/cuda/bin/ncu); override with $NCU.
# Kernel replay keeps the wall time down and the per-launch metrics stable. Volta + driver 580 may not expose a
# metric: `ncu_summary.py` names the missing one and falls back to bytes/time, and the harness
# (tests/kernels.rs::gemv_bandwidth) owns the headline bandwidth number.
#
# The run must only happen in a coordinator-scheduled window: llama.router.service is stopped and drained first and
# restarted right after (AGENTS.md safety rules).
set -e
M=${1:?usage: tools/ncu_gemv.sh <model.gguf> [outdir]}
O=${2:-target/ncu_m2t5}
NCU=${NCU:-/usr/local/cuda/bin/ncu}
BIN=${STRATA_BIN:-target/release/rustingstrata}
TG=${TG:-8}

test -x "$NCU" || { echo "no ncu at $NCU (set NCU=/path/to/ncu)" >&2; exit 1; }
test -x "$BIN" || { echo "build it first: cargo build --release" >&2; exit 1; }
test -f "$M" || { echo "no such model: $M" >&2; exit 1; }
mkdir -p "$O"

# The decode GEMV family plus the elementwise/attention neighbours of the same step, so the summary can attribute
# the 8.4 ms/token time budget (issue #30) and not just one kernel.
"$NCU" --target-processes all --replay-mode kernel \
    --kernel-name 'regex:(gemv|gemvn|moe_gemv|moe_route|moe_combine|swiglu|rms_norm|attn_decode)' \
    --metrics dram__bytes_read.sum,dram__bytes.sum,dram__throughput.avg.pct_of_peak_sustained_elapsed,gpu__time_duration.sum \
    --csv --page raw \
    "$BIN" bench --model "$M" --gpu --backend cuda --pp 512 --tg "$TG" --reps 1 --ctx 4200 \
    > "$O/raw.csv" 2> "$O/raw.err" || {
        echo "ncu failed; the tail of $O/raw.err:" >&2
        tail -5 "$O/raw.err" >&2
        exit 1
    }

python3 -I tools/ncu_summary.py "$O/raw.csv" --tokens "$TG"
