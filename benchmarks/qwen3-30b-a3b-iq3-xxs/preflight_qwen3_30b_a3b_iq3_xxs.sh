#!/usr/bin/env bash
set -Eeuo pipefail
# Read-only preflight. No downloads, servers, installs, or ODS changes.
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-$HOME/qwen3-30b-a3b-iq3-xxs-preflight-$STAMP}"
mkdir -p "$OUT"
exec > >(tee "$OUT/preflight.txt") 2>&1

echo "Qwen3-30B-A3B IQ3_XXS preflight — $STAMP"
echo "Output: $OUT"
echo "User: $(id -un)"
echo
echo "===== HOST / MEMORY / DISK ====="
date --iso-8601=seconds
uname -a
lscpu | grep -E 'Model name|CPU\(s\)|Thread|Core|Socket' || true
free -h
df -h "$HOME"
swapon --show || true
nvidia-smi || true
echo
echo "===== MODEL FILE CANDIDATES (NO DOWNLOAD) ====="
find "$HOME" -maxdepth 5 -type f \( -iname '*Qwen3*30B*A3B*IQ3*XXS*.gguf' -o -iname '*Qwen3*30B*A3B*.gguf' \) -printf '%s bytes\t%p\n' 2>/dev/null | sort -n | head -50 || true
MODEL="${QWEN3_30B_IQ3XXS_MODEL:-}"
if [[ -n "$MODEL" ]]; then
  echo "Configured QWEN3_30B_IQ3XXS_MODEL=$MODEL"
  if [[ -f "$MODEL" ]]; then
    ls -lh "$MODEL"
    stat -c 'bytes=%s modified=%y' "$MODEL"
    sha256sum "$MODEL"
  else
    echo "Configured model path does not exist."
  fi
else
  echo "No model path supplied. Set QWEN3_30B_IQ3XXS_MODEL to the verified file to hash it."
fi
echo
echo "===== ENGINE DISCOVERY ====="
for bin in \
  "$HOME/llama.cpp-cuda/build-cuda/bin/llama-server" \
  "$HOME/llama.cpp-cuda/build/bin/llama-server" \
  "$HOME/llama.cpp/build/bin/llama-server" \
  "$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli" \
  "$HOME/llama.cpp-cuda/build/bin/llama-cli"; do
  if [[ -x "$bin" ]]; then
    echo "--- $bin --version ---"
    "$bin" --version 2>&1 || true
    if [[ "$bin" == *llama-server ]]; then
      echo "--- relevant server options ---"
      "$bin" --help 2>&1 | grep -E -- '-m |--model|-ngl|--n-gpu-layers|--ctx-size|--flash-attn|--jinja|--parallel|--threads' | head -50 || true
    fi
  fi
done
echo
echo "===== LIKELY CHECKOUTS (PATHS ONLY) ====="
for dir in "$HOME/rusting-strata" "$HOME/rusting-strata-test" "$HOME/RustingStrata" "$HOME/tensorfold" "$HOME/TensorFold" "$HOME/tensorfold-test"; do
  if [[ -d "$dir/.git" ]]; then
    echo "--- $dir ---"
    git -C "$dir" rev-parse --show-toplevel
    git -C "$dir" rev-parse HEAD
    git -C "$dir" status --short
    git -C "$dir" remote -v | head -4 || true
  elif [[ -d "$dir" ]]; then
    echo "Directory exists, not a git checkout: $dir"
  fi
done
echo
echo "===== RUNNING MODEL SERVERS (OBSERVE ONLY) ====="
pgrep -af 'llama-server|rusting.?strata|tensorfold' || true
echo
echo "PREFLIGHT ONLY: no server started, no model downloaded, no ODS files changed."
echo "Review preflight.txt before choosing a model source or running an engine."
echo "Report: $OUT/preflight.txt"
