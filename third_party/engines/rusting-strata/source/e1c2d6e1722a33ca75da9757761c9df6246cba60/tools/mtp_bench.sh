#!/usr/bin/env bash
# llama.cpp decode speed with MTP speculative decoding, via llama-server timings.
# Usage: NCMOE=10 DRAFT="0 1 2 3 4" STRATA_MODEL=... tools/mtp_bench.sh
# DRAFT=0 runs without speculative decoding.
set -u
M=${STRATA_MODEL:?set STRATA_MODEL}
BIN=${LLAMA_BIN:-$HOME/Clones/llama.cpp/build-cuda/bin}
NCMOE=${NCMOE:-10}
PORT=${PORT:-8198}
PROMPT=${PROMPT:-"Write a detailed explanation of how a hash map works, including collision handling."}

for d in ${DRAFT:-0 1 2 3 4}; do
  spec=()
  [ "$d" -gt 0 ] && spec=(--spec-type draft-mtp --spec-draft-n-max "$d")
  "$BIN/llama-server" -m "$M" -ngl 99 --n-cpu-moe "$NCMOE" -fa on -c 8192 --port "$PORT" "${spec[@]}" >/dev/null 2>&1 &
  pid=$!
  for _ in $(seq 120); do curl -sf "localhost:$PORT/health" >/dev/null && break; sleep 1; done
  body=$(jq -n --arg p "$PROMPT" '{prompt:$p, n_predict:256, temperature:0, cache_prompt:false}')
  curl -s "localhost:$PORT/completion" -d "$body" >/dev/null  # warmup
  r=$(curl -s "localhost:$PORT/completion" -d "$body")
  echo "draft=$d $(echo "$r" | jq -c '.timings | {predicted_per_second, predicted_n, draft_n, draft_n_accepted}')"
  kill "$pid"; wait "$pid" 2>/dev/null
done
