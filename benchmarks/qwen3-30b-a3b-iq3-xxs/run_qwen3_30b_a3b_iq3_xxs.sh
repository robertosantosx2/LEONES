#!/usr/bin/env bash
set -Eeuo pipefail
# Safe, sequential benchmark runner. No downloads, installs, server startup, or ODS edits.
# Default is dry-run/preflight. Actual execution requires --run and an explicit existing GGUF path.
MODEL=""
DO_RUN=0
for arg in "$@"; do
  case "$arg" in
    --run) DO_RUN=1 ;;
    --model) : ;; # value handled below
    *) ;;
  esac
done
while (($#)); do
  case "$1" in
    --model) [[ $# -ge 2 ]] || { echo "--model requires a path" >&2; exit 2; }; MODEL="$2"; shift 2 ;;
    --run) DO_RUN=1; shift ;;
    -h|--help)
      cat <<'HELP'
Usage:
  run_qwen3_30b_a3b_iq3_xxs.sh [--model /absolute/path/model.gguf] [--run]

Without --run, this only reports candidate executables and CLI support.
With --run, requires --model pointing to the exact Qwen3-30B-A3B IQ3_XXS GGUF.
Runs llama.cpp then RustingStrata sequentially, one engine at a time.
Does not download models, install software, launch persistent servers, or modify ODS.
TensorFold is capability-audited separately; current documented support does not
establish support for this exact Qwen3-30B-A3B IQ3_XXS target.
HELP
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${QWEN3_30B_BENCH_OUT:-$HOME/benchmarks/qwen3-30b-a3b-iq3-xxs-$STAMP}"
mkdir -p "$OUT"
exec > >(tee "$OUT/runner.log") 2>&1
echo "Output directory: $OUT"
echo "Mode: $([[ $DO_RUN -eq 1 ]] && echo EXECUTION || echo PREFLIGHT ONLY)"
echo "Date: $(date --iso-8601=seconds)"
echo "Host: $(hostname)"
echo

find_bin() {
  local candidate
  for candidate in "$@"; do
    if [[ -x "$candidate" ]]; then printf '%s\n' "$candidate"; return 0; fi
  done
  return 1
}
LLAMA_BENCH="$(find_bin "$HOME/llama.cpp-cuda/build-cuda/bin/llama-bench" "$HOME/llama.cpp-cuda/build/bin/llama-bench" "$HOME/llama.cpp/build/bin/llama-bench" || true)"
STRATA="$(find_bin "$HOME/rusting-strata/target/release/strata" "$HOME/rusting-strata-test/target/release/strata" "$HOME/RustingStrata/target/release/strata" "$HOME/rustingstrata/target/release/strata" || true)"

echo "===== EXECUTABLE DISCOVERY ====="
echo "llama-bench=${LLAMA_BENCH:-NOT FOUND}"
echo "strata=${STRATA:-NOT FOUND}"
echo "TensorFold: capability audit only; no equivalent exact-target run is enabled."
[[ -n "$LLAMA_BENCH" ]] && "$LLAMA_BENCH" --version 2>&1 || true
[[ -n "$STRATA" ]] && "$STRATA" --help 2>&1 | head -100 || true
[[ -n "$LLAMA_BENCH" ]] && "$LLAMA_BENCH" --help 2>&1 | grep -E -- '-m |--model|-p |--n-prompt|-n |--n-gen|-r |--repetitions|-ngl|--n-gpu-layers' | head -60 || true
[[ -n "$STRATA" ]] && "$STRATA" bench --help 2>&1 | head -100 || true

if [[ $DO_RUN -eq 0 ]]; then
  echo
  echo "PREFLIGHT ONLY: no model was loaded and no benchmark was run."
  echo "Next: verify exact model provenance and memory/disk, then rerun with --model PATH --run."
  echo "Report: $OUT/runner.log"
  exit 0
fi

[[ -n "$MODEL" ]] || { echo "ERROR: --run requires --model /absolute/path/to/exact-IQ3_XXS.gguf" >&2; exit 2; }
[[ "$MODEL" = /* ]] || { echo "ERROR: use an absolute model path" >&2; exit 2; }
[[ -f "$MODEL" ]] || { echo "ERROR: model file does not exist: $MODEL" >&2; exit 2; }
[[ -n "$LLAMA_BENCH" ]] || { echo "ERROR: llama-bench not found; refusing partial benchmark." >&2; exit 2; }
[[ -n "$STRATA" ]] || { echo "ERROR: RustingStrata binary not found; build/inspect it first, then rerun." >&2; exit 2; }

echo
echo "===== MODEL IDENTITY ====="
ls -lh "$MODEL"
stat -c 'bytes=%s modified=%y' "$MODEL"
sha256sum "$MODEL"
free -h
df -h "$HOME"
nvidia-smi || true
echo
echo "Verify model metadata / repository / revision manually before accepting results."
read -r -p "Type RUN to confirm this is the selected Qwen3-30B-A3B IQ3_XXS GGUF and continue: " CONFIRM
[[ "$CONFIRM" == RUN ]] || { echo "Cancelled by user."; exit 1; }

echo
echo "===== LLAMA.CPP BENCH ====="
echo "Raw log: $OUT/llama-bench.log"
# -p 256 prompt tokens; -n 32 generation tokens; -r 3 repetitions; -ngl 99 requests maximum GPU offload.
# llama.cpp will decide what fits; if this fails, preserve the log and do not tune silently.
set +e
/usr/bin/time -v "$LLAMA_BENCH" -m "$MODEL" -p 256 -n 32 -r 3 -ngl 99 2>&1 | tee "$OUT/llama-bench.log"
LLAMA_RC=${PIPESTATUS[0]}
set -e
echo "llama_bench_exit=$LLAMA_RC"

echo
echo "===== RUSTINGSTRATA BENCH ====="
echo "Raw log: $OUT/strata-bench.log"
# RustingStrata supports --model, --gpu, --pp, --tg, --reps per its CLI docs.
# Run after llama.cpp has exited; no engine is intentionally kept resident.
set +e
/usr/bin/time -v "$STRATA" bench --model "$MODEL" --gpu --pp 256 --tg 32 --reps 3 2>&1 | tee "$OUT/strata-bench.log"
STRATA_RC=${PIPESTATUS[0]}
set -e
echo "strata_bench_exit=$STRATA_RC"

cat > "$OUT/status.txt" <<STATUS
model=$MODEL
sha256=$(sha256sum "$MODEL" | awk '{print $1}')
llama_bench_exit=$LLAMA_RC
strata_bench_exit=$STRATA_RC
tensorfold=not_run_exact_target_support_not_established
raw_logs=llama-bench.log,strata-bench.log,runner.log
STATUS
echo
echo "===== RESULT SUMMARY ====="
cat "$OUT/status.txt"
echo "Review raw logs before interpreting metrics. A nonzero exit or unsupported type is a result, not a reason to silently change model."
echo "Output: $OUT"
