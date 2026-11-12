#!/bin/bash
# Greedy reference for the long prompt (exercises compressed-attention blocks / indexer past 128 tokens).
set -u
LL=/home/vasylt/Clones/llama.cpp-new/build-cuda/bin
M=/home/vasylt/models/deepseek-v4.1/DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XXS-00001-of-00006.gguf
D=$(cd "$(dirname "$0")" && pwd)
flock /home/vasylt/Code/rusting/.gpu.lock bash -c '
  '$LL'/llama-server -m '$M' -ngl 99 --cpu-moe -c 4096 --port 8199 --temp 0 > /tmp/claude-1000/ds/long_server.log 2>&1 &
  SP=$!
  for i in $(seq 1 300); do curl -s localhost:8199/health | grep -q ok && break; sleep 5; done
  jq -Rs "{prompt:.,n_predict:32,temperature:0,top_k:1,n_probs:5,cache_prompt:false}" '$D'/long_prompt.txt \
    | curl -s localhost:8199/completion -d @- > '$D'/ref_long.json
  kill $SP
  wait $SP
'
echo DONE
