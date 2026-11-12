# Benchmarks

Speed claims are only useful if you can check them on your own machine. This
page describes how Kinetic is measured against llama.cpp, how to repeat it,
and the results on our reference machines.

## Method

- **Same file, same threads.** Both engines run the same GGUF file. On the
  CPU both get the same thread count; on the GPU both run the whole model on
  the device.
- **The llama-bench tests.** `pp512` processes a 512-token prompt and
  `tg128` generates 128 tokens. `kinetic bench` runs the same two tests as
  `llama-bench`, with speculative decoding off, so every generated token
  costs one pass over the weights on both sides. Each number is the best of
  the repetitions.
- **An editing request.** Real use often repeats text: an assistant
  rewriting code, quoting a document, filling a template. The edit test sends
  one greedy chat request that renames a variable in a short Python file and
  asks for the whole file back, to `kinetic serve` and to `llama-server` with
  llama.cpp's own speculative decoding on (`--spec-type ngram-mod`, or
  `draft-mtp` for models with a prediction block). Speed is generated tokens
  over the time from the first to the last token, measured on the client the
  same way for both. Both answers are greedy, so they should be identical;
  the script reports whether they are.
- **Exactness is checked, not assumed.** `kinetic bench` also runs its own
  edit test and fails if drafted output differs from plain decoding.
- **A quiet machine.** No other programs using the CPU or the GPU, laptops
  on mains power with the performance power plan, best of three runs.

## Reproduce it

You need a llama.cpp build with `llama-bench` and `llama-server` and a
model file. On the CPU, one script runs everything and prints a markdown
table:

```sh
python scripts/bench_vs_llamacpp.py model.gguf --llama-dir path/to/llama.cpp/bin -t 6
```

| Option | Meaning |
|---|---|
| `--llama-dir` | folder with `llama-bench` and `llama-server` |
| `--kinetic` | the `kinetic` binary [default: `kinetic` on `PATH`] |
| `-t`, `--threads` | CPU threads for both [default: half the logical CPUs] |
| `-r`, `--repetitions` | runs of each plain test [default: 3] |
| `--max-tokens` | limit for the edit answer [default: 512] |
| `--llama-spec` | `llama-server --spec-type` [default: `ngram-mod`]; use `draft-mtp` for models with an MTP block |
| `--skip-edit` | only the two plain tests |

The script hides the GPUs from llama.cpp and passes `--device cpu` to
Kinetic, starts one server at a time on 127.0.0.1 and stops it afterwards.

On the GPU, run the two tools by hand:

```sh
kinetic bench model.gguf --device cuda -r 3
llama-bench -m model.gguf -p 512 -n 128 -r 3 -ngl 99 -fa on
```

## Results

Kinetic 0.1.0 against llama.cpp build b12001, tokens per second, higher is
better. Measured on a laptop with a Ryzen 5 6600H (6 cores, DDR5) and an RTX
3060 Laptop GPU (6 GB).

| Model | Device | Test | llama.cpp | Kinetic |
|---|---|---|---:|---:|
| Qwen3.5 4B Q4_K_M | RTX 3060 Laptop | pp512 | TBD | TBD |
| Qwen3.5 4B Q4_K_M | RTX 3060 Laptop | tg128 | TBD | TBD |
| Qwen3.5 4B Q4_K_M | RTX 3060 Laptop | edit | TBD | TBD |
| Qwen3.5 4B Q4_K_M | Ryzen 5 6600H, 6 threads | pp512 | TBD | TBD |
| Qwen3.5 4B Q4_K_M | Ryzen 5 6600H, 6 threads | tg128 | TBD | TBD |
| Qwen3.5 4B Q4_K_M | Ryzen 5 6600H, 6 threads | edit | TBD | TBD |
| LFM3 1.7B Q4_K_M | RTX 3060 Laptop | pp512 | TBD | TBD |
| LFM3 1.7B Q4_K_M | RTX 3060 Laptop | tg128 | TBD | TBD |
| LFM3 1.7B Q4_K_M | RTX 3060 Laptop | edit | TBD | TBD |
| LFM3 1.7B Q4_K_M | Ryzen 5 6600H, 6 threads | pp512 | TBD | TBD |
| LFM3 1.7B Q4_K_M | Ryzen 5 6600H, 6 threads | tg128 | TBD | TBD |
| LFM3 1.7B Q4_K_M | Ryzen 5 6600H, 6 threads | edit | TBD | TBD |
| Qwen3.5 35B-A3B UD-Q2_K_XL (12.2 GB) | RTX 3060 Laptop + system RAM | tg128 | TBD | TBD |

Prompt processing on the GPU (`pp512`) is an area where llama.cpp is ahead
today; it is on the [roadmap](roadmap.md).

## Share your numbers

Results from other hardware are welcome. Open a
[performance issue](https://github.com/Veloresearch/kinetic/issues/new?template=performance.yml)
with the script's output, or the two commands above and their output, your
CPU, GPU, RAM and driver version, and the llama.cpp build you compared with.
