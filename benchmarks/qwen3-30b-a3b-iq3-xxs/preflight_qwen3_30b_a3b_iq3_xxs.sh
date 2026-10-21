#!/usr/bin/env bash
set -Eeuo pipefail
# Read-only preflight. Does not download models, start servers, or modify ODS.
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-$HOME/qwen3-30b-a3b-iq3-xxs-preflight-$STAMP}"
MODEL="${QWEN3_30B_IQ3XXS_MODEL:-$HOME/llama.cpp-cuda/models/Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf}"
mkdir -p "$OUT"
exec > >(tee "$OUT/preflight.txt") 2>&1

echo "Qwen3-30B-A3B IQ3_XXS preflight — $STAMP"
echo "Output: $OUT"
echo "Model candidate: $MODEL"
echo
echo "===== HOST ====="
date --iso-8601=seconds
uname -a
printf '\n'; lscpu | grep -E 'Model name|CPU\(s\)|Thread|Core|Socket' || true
printf '\n'; free -h
printf '\n'; df -h "$HOME"
printf '\n'; swapon --show || true
printf '\n'; nvidia-smi || true
printf '\n'; docker --version 2>/dev/null || true
printf '\n'; git --version
echo
echo "===== MODEL FILE ====="
if [[ -f "$MODEL" ]]; then
  ls -lh "$MODEL"
  stat -c 'bytes=%s modified=%y' "$MODEL"
  sha256sum "$MODEL"
else
  echo "NOT FOUND: $MODEL"
  echo "No download attempted. Set QWEN3_30B_IQ3XXS_MODEL to the verified GGUF path."
fi
echo
echo "===== ENGINE CHECKS ====="
for p in \
  "$HOME/llama.cpp-cuda/build-cuda/bin/llama-server" \
  "$HOME/rusting-strata-test/target/release/strata" \
  "$HOME/tensorfold-test"; do
  if [[ -e "$p" ]]; then
    ls -ld "$p"
  else
    echo "NOT FOUND: $p"
  fi
done
echo
if [[ -x "$HOME/llama.cpp-cuda/build-cuda/bin/llama-server" ]]; then
  echo "--- llama.cpp version ---"
  "$HOME/llama.cpp-cuda/build-cuda/bin/llama-server" --version 2>&1 || true
  echo "--- llama.cpp help quant/offload flags ---"
  "$HOME/llama.cpp-cuda/build-cuda/bin/llama-server" --help 2>&1 | grep -E -- '-m |--model|-ngl|--n-gpu-layers|--ctx-size|--flash-attn|--jinja' | head -35 || true
fi
if [[ -x "$HOME/rusting-strata-test/target/release/strata" ]]; then
  echo "--- RustingStrata help (read-only) ---"
  "$HOME/rusting-strata-test/target/release/strata" --help 2>&1 | head -100 || true
fi
if [[ -d "$HOME/tensorfold-test" ]]; then
  echo "--- TensorFold repository state ---"
  git -C "$HOME/tensorfold-test" rev-parse --show-toplevel 2>/dev/null || true
  git -C "$HOME/tensorfold-test" rev-parse HEAD 2>/dev/null || true
  git -C "$HOME/tensorfold-test" status --short 2>/dev/null || true
fi
echo
echo "===== MEMORY FEASIBILITY GATE ====="
if [[ -f "$MODEL" ]]; then
  SIZE="$(stat -c %s "$MODEL")"
  AVAIL_KB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  AVAIL_BYTES="$((AVAIL_KB * 1024))"
  echo "model_bytes=$SIZE"
  echo "memavailable_bytes=$AVAIL_BYTES"
  if (( SIZE > AVAIL_BYTES )); then
    echo "WARNING: model file is larger than current MemAvailable; mmap does not remove the need for working memory."
  else
    echo "Model file is not larger than current MemAvailable, but runtime overhead still applies."
  fi
fi
echo
echo "PREFLIGHT ONLY: no server started, no model downloaded, no ODS files changed."
echo "Review this report before starting any engine."
echo "Report: $OUT/preflight.txt"
