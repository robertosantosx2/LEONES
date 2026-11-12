#!/usr/bin/env bash
# Sweep llama.cpp --n-cpu-moe on the target file; print llama-bench markdown rows.
set -uo pipefail
M=${STRATA_MODEL:-/mnt/ollama/hub/models--unsloth--Qwen3.6-35B-A3B-MTP-GGUF/snapshots/5bc3e238d916f48a861bac2f8a1990a0e9b7e98d/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf}
B=${LLAMA_BIN:-$HOME/Clones/llama.cpp/build-cuda/bin}
for n in ${SWEEP:-4 6 8 10 12 16 20}; do
  echo "== n-cpu-moe $n"
  "$B/llama-bench" -m "$M" -ngl 99 -ncmoe "$n" -fa 1 -p 4096 -n 128 -r 2 -o md 2>&1 | grep -E "^\| *qwen|error:" || echo "failed"
done
