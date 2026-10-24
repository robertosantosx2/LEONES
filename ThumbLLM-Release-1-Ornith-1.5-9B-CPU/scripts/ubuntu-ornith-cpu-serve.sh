#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${THUMBLLM_LINUX_ROOT:-$HOME/leones-work/thumbllm-ornith-linux}"
SERVER="$ROOT/llama.cpp/build/bin/llama-server"
MODEL="$ROOT/models/Ornith-1.5-9B-OBLITERATED-Q4_K_M.gguf"
CTX="${CTX_SIZE:-16384}"
PORT="${PORT:-18088}"

[[ -x "$SERVER" ]] || { echo "Server not found; run ubuntu-ornith-cpu-setup.sh first." >&2; exit 2; }
[[ -f "$MODEL" ]] || { echo "Model not found; run ubuntu-ornith-cpu-setup.sh first." >&2; exit 2; }

# Match the recipe's topology-aware intent: physical cores for decode and
# logical CPUs for prompt/batch processing. This is adapted to the current host.
PHYSICAL="$(lscpu -p=CORE,SOCKET | awk -F, '!/^#/ {print $1 \", \" $2}' | sort -u | wc -l)"
LOGICAL="$(nproc)"
PHYSICAL="${PHYSICAL// /}"
if [[ ! "$PHYSICAL" =~ ^[0-9]+$ ]] || (( PHYSICAL < 1 )); then PHYSICAL="$LOGICAL"; fi

echo "CPU decode threads: $PHYSICAL; prompt/batch threads: $LOGICAL"
echo "Context: $CTX; API: http://127.0.0.1:$PORT/v1"
echo "For exact recipe context use CTX_SIZE=65536; start at 16384 to validate memory first."

exec "$SERVER" \
  --model "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --ctx-size "$CTX" \
  --threads "$PHYSICAL" \
  --threads-batch "$LOGICAL" \
  --cpu-strict 0 \
  --cpu-strict-batch 0 \
  --prio 2 \
  --prio-batch 1 \
  --poll 50 \
  --poll-batch 1 \
  --batch-size 2048 \
  --ubatch-size 512 \
  --gpu-layers 0 \
  --device none \
  --flash-attn on \
  --cache-type-k q4_0 \
  --cache-type-v q4_0 \
  --parallel 1 \
  --cache-reuse 0 \
  --no-kv-offload \
  --no-op-offload \
  --repack \
  --mmap \
  --cache-prompt \
  --jinja
