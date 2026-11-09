#!/usr/bin/env bash
# Pithos 0.6.1 — LFM2.5-8B-A1B Q4_K_M short-generation reproduction
# Run from the extracted official Pithos 0.6.1 Linux x64 directory.
set -euo pipefail

MODEL="${HOME}/Pithos/models/LFM2.5-8B-A1B-Q4_K_M.gguf"
PROMPT='Explain briefly what a mixture-of-experts language model is.'

./pithos --model "$MODEL" --gpu off --ctx 512 --threads 8 --batch 32 \
  --reasoning off --seed 42 --n-predict 64 --stats --prompt "$PROMPT"

./pithos --model "$MODEL" --gpu opencl --gpu-device 1 --gpu-mem 2500 \
  --ctx 512 --threads 8 --batch 32 --reasoning off --seed 42 \
  --n-predict 64 --stats --prompt "$PROMPT"

./pithos --model "$MODEL" --gpu vulkan --gpu-device 1 \
  --ctx 512 --threads 8 --batch 32 --reasoning off --seed 42 \
  --n-predict 64 --stats --prompt "$PROMPT"
