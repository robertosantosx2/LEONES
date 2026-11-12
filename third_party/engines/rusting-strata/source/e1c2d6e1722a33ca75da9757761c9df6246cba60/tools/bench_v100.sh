#!/bin/sh
# Benchmark on the Tesla V100 (32 GB). Usage: tools/bench_v100.sh <model.gguf> [backend] [out.md]
# Appends one timestamped block to docs/V100-results.md (or $3) so the numbers of every run stay together, plus the
# machine-readable `strata.bench.v1` record as a fenced json block.
# The same record is appended (one line per run) to $STRATA_BENCH_JSONL, default target/v100-bench.jsonl.
# `jq` validates the record when installed; without it the script warns on stderr and keeps going.
set -e
M=${1:?usage: tools/bench_v100.sh <model.gguf> [cuda|vulkan] [out.md]}
B=${2:-vulkan}
O=${3:-docs/V100-results.md}
BIN=${STRATA_BIN:-target/release/rustingstrata}
CTX=${STRATA_CTX:-32896}
JSONL=${STRATA_BENCH_JSONL:-target/v100-bench.jsonl}

test -x "$BIN" || { echo "build it first: cargo build --release" >&2; exit 1; }
test -f "$M" || { echo "no such model: $M" >&2; exit 1; }

tmp=$(mktemp "${TMPDIR:-/tmp}/strata-bench.XXXXXX.json")
trap 'rm -f "$tmp"' EXIT INT TERM

{
    echo "## $(date -u '+%Y-%m-%d %H:%M UTC') — $(basename "$M")"
    echo
    echo '```'
    echo "\$ strata bench --backend $B --pp 512,4096,32768 --tg 128 --reps 3 --ctx $CTX --json-out $tmp"
    "$BIN" bench --model "$M" --gpu --backend "$B" --pp 512,4096,32768 --tg 128 --reps 3 --ctx "$CTX" --json-out "$tmp" 2>&1
    echo '```'
    echo
} | tee -a "$O"

test -s "$tmp" || { echo "bench: no JSON record in $tmp; is the build up to date?" >&2; exit 1; }
if command -v jq >/dev/null 2>&1; then
    jq -e . "$tmp" >/dev/null || { echo "bench: $tmp is not valid JSON; not recording it" >&2; exit 1; }
else
    echo "bench: jq not found; skipping the validation of the JSON record" >&2
fi

mkdir -p "$(dirname "$JSONL")"
cat "$tmp" >> "$JSONL"
{
    echo '```json'
    cat "$tmp"
    echo '```'
    echo
} >> "$O"
