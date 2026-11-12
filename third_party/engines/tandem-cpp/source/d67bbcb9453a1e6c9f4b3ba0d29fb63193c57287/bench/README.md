# bench

The workloads behind the README tables. Python 3 standard library only; any OpenAI-compatible llama-server.

- `w1_gsm8k.py`: W1, the first 200 GSM8K test questions, zero-shot chat, max 2048 tokens, one request at a time.
  Reports correct answers and decode tok/s (total tokens / total time from first to last token).
- `w4_longctx.py`: W4, long context. Real text (a llama.cpp checkout's docs and sources) cut to 16k / 32k / 64k tokens
  with two planted code words; asks for both and reports correctness, time to first token and decode tok/s.
- `run_cell.py`: starts a server, runs W1 (and W4), stops it, keeps the log and the cache statistics.
- `common.py`: the streaming client. `LC_SAMPLING` picks the sampling (unset = greedy, temperature 0):
  `default` = Qwen's (T 1.0, top-k 20, top-p 0.95), `gptoss` = T 1.0 / top-p 1.0, `ds4` = T 1.0 / top-p 0.95,
  `server` = the server's own defaults. `LC_SEED` sets the seed (default 1).

Example, tandem.cpp against plain llama.cpp on the same GPU memory:

```
python3 bench/run_cell.py --bin tandem/build/bin/llama-server --model gpt-oss-120b-MXFP4.gguf \
    --tag gptoss-tandem --cache-mib auto
python3 bench/run_cell.py --bin llama.cpp/build/bin/llama-server --model gpt-oss-120b-MXFP4.gguf \
    --tag gptoss-llamacpp --no-ngl --extra "-fit on -fitt 1024"
```

`-fitt` should leave the same free memory as tandem.cpp's auto margin (1024 MiB, plus the draft model's size when one
is loaded; tandem.cpp logs the value as "MoE cache auto size: ... margin" at `-lv 4`, which run_cell.py sets). For W4 use `--ctx 73728 --w4 16384,32768,65536
--corpus path/to/llama.cpp`.

`data/gsm8k_test.jsonl` is the GSM8K test set (Cobbe et al. 2021, github.com/openai/grade-school-math, MIT licence).
