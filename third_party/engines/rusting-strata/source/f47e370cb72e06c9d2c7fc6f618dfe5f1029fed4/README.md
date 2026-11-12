# RustingStrata

A pure-Rust inference engine for Qwen GGUF models: Qwen3.5/3.6 (`qwen35moe`, `qwen35`), Qwen3-Next (`qwen3next`),
Qwen3.8-Flash-Next (`qwen4exp`), Qwen3 (`qwen3`, `qwen3moe`), DeepSeek-V4.1-Flash (`deepseek41`) and GLM-5.3-Flash (`glm5-next`). CUDA kernels are
compiled at run time with NVRTC through cudarc, and the same kernels also run on Vulkan (`--backend vulkan`): no C++
build step, no ggml. Experts that do not fit in VRAM run on the CPU at the same time as the GPU work, and the expert
placement adapts to the routing it sees.

Version 1.2.1. Docs: [usage and server API](docs/USAGE.md), [hosting for other people](docs/HOSTING.md),
[supported GPUs](docs/SUPPORTED_GPUS.md), [AMD notes](docs/AMD.md), [LoRA](docs/LORA.md),
[all benchmarks](docs/BENCHMARKS.md), [benchmark history](docs/README.md).

## Numbers

Reference machine: RTX 3060 12 GB, Ryzen 5 7600X, 32 GB RAM. Model: `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf` (11.7 GiB,
does not fit in VRAM). llama.cpp is the 2026-10-28 build 11876, tuned for the same file (`-ncmoe 12 -ub 2048
-b 2048`, flash attention; with its default ubatch its 4K prefill is ~1550).

| | CUDA | Vulkan | llama.cpp |
|---|---|---|---|
| Prefill, 4K prompt | **2216 tok/s** (2169-2252) | 2154 (2140-2162) | ~2236 (2183-2310) |
| Decode after 4K prompt | **113.4 tok/s** (110.9-114.8) | 113.6 | 66.5 |
| Decode, short prompt (like tg128) | **118.2 tok/s** (117.0-118.8) | 117.3 | 68.4 |
| Decode with MTP drafts (`--mtp 1`, greedy), short / after 4K | **up to 160 / 152 tok/s** | 158 / 154 | (its MTP is slower) |
| 32K: prefill / decode | **1800 / 91.9 tok/s** | 1582 / 90.7 | |
| Greedy top-1 agreement with llama.cpp (20 prompts x 32 tokens), either llama.cpp mode | 98-99% | 98-99% | 98.3% (its batch vs token-by-token modes) |

Measured with `rustingstrata bench --gpu --mtp 0 --pp 512,4096,32768 --tg 128 --reps 3 --ctx 32896`, mean of 3 rounds
(range in brackets); llama.cpp from `llama-server` timings, 4047-token prompt + 128 tokens, 3 runs.
MTP gains depend on the text.
Agreement counts a token when it matches llama.cpp run token by token or with the context as one batch;
llama.cpp's own two modes agree on only 98.3%. The remaining misses are near-ties where
float rounding order picks a different token. The expert placement adapts between runs and the CPU and
GPU expert kernels round differently, so greedy output can change at such near-ties from one run to the next. MTP
on and off give identical greedy tokens.

With less VRAM, simulated on the 3060 with `--vram-margin` (not measured on real 8 GB or 6 GB cards): ~8 GB
keeps 116 / 110 tok/s decode (short / after 4K) and 2128 tok/s 4K prefill, ~6 GB 105 / 97 and 2056.

Other models, greedy "The capital of France is" with `--gpu` (CUDA / Vulkan, second run):

| Model | Types | Decode |
|---|---|---|
| Qwen3.5-2B (fine-tune) Q4_K_M | Q4_K, Q6_K, ... | 208 / 208 tok/s |
| Qwen3-4B-Instruct-2507 Q4_K_M (dense) | Q4_K, Q6_K | 104 / 110 tok/s |
| Qwen3.5-9B Q5_K_S | Q5_K, Q6_K, Q8_0 | 51 / 53 tok/s |
| Qwen3-30B-A3B-Instruct-2507 UD-Q2_K_XL | Q2_K to Q6_K | 114 / 123 tok/s |
| Qwen3.8-27B UD-IQ3_XXS (dense, 10.8 GB on GPU) | IQ1_S to IQ4_XS, Q2_K to Q8_0 | 20.6 / 20.5 tok/s |
| Qwen3.6-35B-A3B UD-IQ4_XS (57% of experts fit in VRAM) | IQ3_S, IQ4_XS, Q6_K, Q8_0 | 94 / 96 tok/s |
| Qwen3-Next-80B-A3B-Instruct UD-IQ1_S (most experts on the CPU) | IQ1_S to IQ4_NL, Q4_K to Q8_0, BF16 | 92 / 90 tok/s |
| Qwen3.8-Flash-Next GSQ-RCO IQ2_XS (64 GB in two files, pass the `-00001-of-00002` one; 18% of experts fit in VRAM, and with 32 GB RAM the rest are partly read from disk) | Q2_0, IQ1_M to IQ4_XS, Q6_K, Q8_0, F16, BF16 | 22 / 20 tok/s |

Supported GGUF types: F32, F16, BF16, Q8_0, Q4_0, Q4_1, Q5_0, Q5_1, Q2_0, Q2_K-Q6_K, IQ1_S, IQ1_M, IQ2_XXS, IQ2_XS, IQ2_S,
IQ3_XXS, IQ3_S, IQ4_XS, IQ4_NL.

## Build

Needs Rust (2024 edition) and one of:

- an NVIDIA driver with the CUDA NVRTC library (loaded at run time). Volta (sm_70), Turing (sm_75) and Ampere or newer
  (sm_80+) work; CUDA 13 dropped Volta, so a V100 needs the 12.x toolkit. Pascal and older use Vulkan.
- a Vulkan 1.3 driver with shaderFloat64, int8/16/64 and subgroup size 32 or a fixed 64 (tested on RTX 3060, Radeon VII
  and V100; Intel Arc lacks shaderFloat64).

`--gpu` picks CUDA when it loads, else Vulkan; `--backend` chooses. The first CUDA run compiles the kernels (~15 s) and
caches them. Every GPU tried so far is in [docs/SUPPORTED_GPUS.md](docs/SUPPORTED_GPUS.md); AMD notes are in
[docs/AMD.md](docs/AMD.md).

```sh
cargo build --release
```

On Windows, install the Visual Studio C++ Build Tools first (one dependency compiles C code).

## Quick start

Run `rustingstrata` with no arguments (double-click `rustingstrata.exe` on Windows; release binaries are on the GitHub releases page).
It starts a server on http://127.0.0.1:8080 and opens a chat page that downloads models from Hugging Face and switches
between the ones in your models folder. Any app that takes an OpenAI-compatible address (Open WebUI, Jan, SillyTavern,
code editors) can use `http://127.0.0.1:8080/v1`.

From a terminal:

```sh
M=path/to/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf

target/release/rustingstrata calibrate --model $M     # once per model and machine: best chunk size, MTP drafts
target/release/rustingstrata generate --model $M --gpu --prompt "Write a haiku about rivers." -n 128
target/release/rustingstrata chat --model $M --gpu    # --think for thinking mode, --temp 0.7 to sample
target/release/rustingstrata bench --model $M --gpu --pp 512,4096 --tg 128
STRATA_API_KEY=secret target/release/rustingstrata serve --model $M --gpu --addr 127.0.0.1:8080
```

Without `--gpu` everything runs on the CPU reference, which is slow and meant for checking. Flags, the OpenAI and
Anthropic APIs, tool calls, caching and multi-GPU are in [docs/USAGE.md](docs/USAGE.md).

## DeepSeek-V4.1-Flash (IQ2_XXS, 249 GB)

`chat`, `generate` and `serve` detect the `deepseek41` architecture and run it on the CPU reference forward, with the
matvecs and a 9 GB expert cache on the CUDA card (no `--gpu` flag needed). Pass the first shard; the others are found
next to it.

```sh
M=DeepSeek-V4.1-Flash-1017-GSQ-RCO-IQ2_XXS-00001-of-00006.gguf
rustingstrata chat     --model $M [--think]
rustingstrata generate --model $M --prompt "The capital of France is" -n 64
rustingstrata serve    --model $M --addr 127.0.0.1:8080 [--api-key K]
```

| DeepSeek-V4.1-Flash IQ2_XXS (249 GB), RTX 3060 12 GB, 30 GB RAM | RustingStrata | llama.cpp b12116 (`--cpu-moe`) |
|---|---|---|
| Decode | 1.8 tok/s at first, 2-3.6 tok/s now (VRAM expert cache with LRU) | 0.3-1.5 tok/s (cold) |
| Prefill | ~2 tok/s on short prompts (0.5 s/token), ~0.5 tok/s at 1400 tokens | 0.5-0.9 tok/s (cold) |
| Teacher-forced top-1 vs llama.cpp | 189/192 short, 21/23 on 1425 tokens (misses are near-ties) | - |
| Sampling, tool calls | no sampling; tool calls in `serve` | supported |

The llama.cpp numbers are from the first cold runs on this box and the RustingStrata numbers from the last runs
before the model was deleted; they were not re-measured side by side, and both move with the page cache.
Decode varies run to run with the page cache, because the experts that miss VRAM are read from the GGUF.
`STRATA_DS_GPU_EXPERTS=<GB>` changes the VRAM expert budget (10 worked on a 12 GB card). Prefill is one token at a
time. Prompt plus reply is limited only by the model's trained context from the GGUF (1,048,576; `STRATA_DS_CTX` lowers it; checked against llama.cpp only up to a 1425-token prompt), decoding is greedy only, and sampling is not supported. Tool calls work in `serve`: the prompt matches the model template (jinja2 render, three cases byte for byte) and the reply's `<｜DSML｜ calls>` block is parsed, but this path has not been run against the model itself.

## GLM-5.3-Flash (UD-Q2_K_XL, 119 GB)

`chat`, `generate` and `serve` detect the `glm5-next` architecture (Kimi-delta attention, sparse MLA attention, four-stream
hyper-connections, sigmoid MoE) and run the CPU reference forward, with the dense matvecs and an 11 GB expert cache on the
CUDA card (`STRATA_DS_GPU_EXPERTS=<GB>` changes the budget; it also counts the non-expert weights). Pass the first shard.

```sh
M=GLM-5.3-Flash-UD-Q2_K_XL-00001-of-00004.gguf
rustingstrata chat     --model $M
rustingstrata generate --model $M --prompt "The capital of France is" -n 64
rustingstrata serve    --model $M --addr 127.0.0.1:8080 [--api-key K]
```

Greedy output equals llama.cpp b12119 (`--cpu-moe`) for 32 tokens on 3 fixed prompts on the CPU path; with the GPU matvecs
prompts 1 and 2 still match for 32 tokens and prompt 3 flips at the first token, a near-tie (logprob -2.65 against -2.73). Fed llama.cpp's own 64 tokens per prompt (teacher-forced), the GPU path picks the same top-1 on 188 of 192 steps; the four misses are llama.cpp near-ties (margins 0.03-0.53 logprob). Tokenizer ids
match llama.cpp on 29 test strings and the chat template matches `/apply-template` on 2 conversations.
On an RTX 3060 12 GB with 30 GB RAM decode took about 0.4-0.7 s per token with warm page cache (about 55% VRAM expert-cache
hits on a short text); llama.cpp (`--cpu-moe`, server, 64 greedy tokens per prompt) took 2.3-2.9 s per token (0.34-0.44 tok/s) on the same box in the same session, started right before our runs on the same page cache; a later paired run (64 greedy tokens through `serve`, llama.cpp, ours, ours, llama.cpp) gave 1.25-1.40 tok/s against 0.47-0.56, a first token after 17-19 s against 40-41 s on a short prompt, load until ready in 4-6 s against 58 s, and, on a 550-token prompt, a first token after 206-209 s against 107-229 s (llama.cpp's second run had the page cache warm); both timings move with the page cache and the pairs were run twice, not as a full benchmark.
Caveats: prefill runs 512-token chunks layer by layer so each routed expert is read once per chunk (a 380-word, about 550-token prompt prefilled in 209 s with 512-token chunks against 325 s with 128, identical logprobs; short prompts cost more per token because the experts stream from SSD once per chunk, `STRATA_GLM_CHUNK` sets the size); prompt plus reply is limited only by the model's trained context from the GGUF (1,048,576; `STRATA_GLM_CTX` lowers it, and the KV cache grows with the text, so RAM is the real bound; the k-pool sparse-attention indexer takes over past 2048 rows and was checked against llama.cpp up to 3.6k tokens: same top-5 sets, same first token); the NextN/MTP layer is unused; decoding is greedy only; tool calls work in `serve` (the prompt matches llama.cpp's template byte for byte, checked on one tool call and one tool-result round trip); the reasoning
text comes back in `content` before `</think>`.

## Development

```sh
cargo test --release                      # GPU tests need the model: STRATA_MODEL=path/to/model.gguf
python -I tools/parity.py $M --extra "--gpu" --tag gpu   # agreement with llama.cpp (needs llama-server once)
```

Source map: `src/gguf.rs` (file reader), `src/quant/` (dequantization), `src/model.rs` (CPU reference forward),
`src/cuda/` and `src/vulkan/` (GPU kernels, behind `src/backend.rs`), `src/gpu_model.rs` and
`src/gpu_model/prefill.rs` (GPU forward and chunked prefill), `src/expert_cache.rs` (expert placement),
`src/cpu_moe.rs` and `src/cpu_worker.rs` (CPU experts), `src/deepseek/` (DeepSeek-V4.1), `src/glm/` (GLM-5.3), `src/serve.rs` (HTTP),
`src/chat.rs` (chat templates and tool calls), `src/main.rs` (CLI).

## License

RustingStrata is released under the [RustingStrata License 1.0](LICENSE.md). You may use, modify and distribute it,
including for commercial services, as long as you keep the license and credit Vasyl Trefilov as the original author.
You may not sell RustingStrata itself.
