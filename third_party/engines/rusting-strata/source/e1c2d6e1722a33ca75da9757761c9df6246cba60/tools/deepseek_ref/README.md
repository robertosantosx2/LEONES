# DeepSeek-V4.1-Flash-1017 reference outputs

Greedy output from llama.cpp b12116 (CUDA build, `--cpu-moe -ngl 99 -c 4096`, IQ2_XXS GGUF) on an RTX 3060 12 GB,
30 GB RAM. `run_ref.sh` starts `llama-server`, sends the prompts in `prompts.txt` to `/completion` with
`temperature 0, top_k 1, n_predict 64, n_probs 5`, and writes `ref_N.json` (text, token ids, top-5 logprobs, timings).

Prompts are sent raw, with no chat template. Speed on this box is cold-cache and I/O bound: prompt 0.5-0.9 tok/s,
decode 0.3-1.5 tok/s. `server.log` is the llama-server log of the last run.
