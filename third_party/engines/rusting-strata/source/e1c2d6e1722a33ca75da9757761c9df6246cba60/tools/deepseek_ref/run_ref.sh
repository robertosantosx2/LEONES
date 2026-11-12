#!/bin/bash
# Greedy reference from llama.cpp: 3 prompts, 64 tokens, top-5 logprobs per token.
set -u
LL=/home/vasylt/Clones/llama.cpp-new/build-cuda/bin
M=/home/vasylt/models/deepseek-v4.1/DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XXS-00001-of-00006.gguf
D=$(cd "$(dirname "$0")" && pwd)
flock /home/vasylt/Code/rusting/.gpu.lock bash -c '
  '$LL'/llama-server -m '$M' -ngl 99 --cpu-moe -c 4096 --port 8199 --temp 0 > '$D'/server.log 2>&1 &
  SP=$!
  echo $SP > '$D'/server.pid
  for i in $(seq 1 300); do curl -s localhost:8199/health | grep -q ok && break; sleep 5; done
  i=0
  while IFS= read -r p; do
    i=$((i+1))
    jq -n --arg p "$p" "{prompt:\$p,n_predict:64,temperature:0,top_k:1,n_probs:5,cache_prompt:false}" \
      | curl -s localhost:8199/completion -d @- > '$D'/ref_$i.json
  done < '$D'/prompts.txt
  kill $SP
  wait $SP
'
echo DONE
