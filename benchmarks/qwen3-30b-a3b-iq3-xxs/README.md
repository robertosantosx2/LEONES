# Qwen3-30B-A3B IQ3_XXS: benchmark preparation

Status: prepared for host preflight; no model benchmark has been run on the Ubuntu host.

## Exact target

Keep **Qwen3-30B-A3B-Instruct-2507 IQ3_XXS GGUF** as the intended target unless the user confirms the previously selected source was the original Instruct variant. Never silently switch model family, revision, quantization or format. Verify the repository/revision, license, metadata, file size and SHA-256 before running.

## Updated compatibility findings (source inspected 2026-10-21)

- **llama.cpp — reference engine.** Upstream includes Qwen3 MoE model support and the IQ3_XXS GGML/GGUF type. The installed local build and exact file still need verification. Official sources: [Qwen3 model code](https://github.com/ggml-org/llama.cpp/tree/master/src/models) and [quantization type definitions](https://github.com/ggml-org/llama.cpp/blob/master/gguf-py/gguf/constants.py).
- **RustingStrata — viable candidate, not merely unknown.** Current upstream source explicitly accepts `qwen3moe` architecture in `src/config.rs` and implements GGML type ID 18 as `IQ3_XXS` in `src/quant/mod.rs`. This is a source-level compatibility signal for the exact architecture/type; the host checkout/version must match or exceed that source and the actual model must pass load + generation. Source: [architecture table](https://github.com/RustingStudio/RustingStrata/blob/main/src/config.rs), [quant type reader](https://github.com/RustingStudio/RustingStrata/blob/main/src/quant/mod.rs).
- **TensorFold — not an equivalent third-engine run for this target on current documented support.** Current native support tables cover specific Qwen3.8/3.6/Flash Next/Nemotron/GLM families and specific checkpoint formats, not Qwen3-30B-A3B-Instruct-2507 IQ3_XXS. TensorFold documents GGUF only for selected family paths/formats; it does not mean arbitrary GGUF quant types or Qwen3 MoE are accepted. Record a capability check, but do not download/convert another checkpoint or call a different model an IQ3_XXS result. If TensorFold cannot load this exact model, report **unsupported / not comparable**. Sources: [CUDA support matrix](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/cuda.md), [quantization and backend paths](https://github.com/ashhart/TensorFold/blob/main/docs/quantization.md).
 
## Hardware and memory

Prior host snapshot: Ubuntu, NVIDIA RTX 3050 Laptop (4 GiB VRAM), 14 GiB RAM. A ~30B IQ3_XXS model can require substantially more than VRAM and may stress host RAM even with mmap and CPU offload. Inspect available RAM, swap and free disk before download/load. No script here downloads the model, installs software, or edits ODS.

## Protocol

- Sequential runs only; do not keep multiple model engines resident at once.
- Context/prompt: 256 tokens; generation: 32 tokens; one warm-up plus three measured repetitions where supported.
- Use the same exact GGUF, tokenizer/chat template and prompt. Use greedy decoding / temperature 0 where available.
- Record model repository/revision, filename, file size, SHA-256, architecture metadata, engine commit/version, exact arguments, load time, prefill tok/s, decode tok/s, peak RAM/VRAM, GPU offload and exit status.
- llama.cpp `llama-bench` and RustingStrata `strata bench` have different reporting conventions. Keep raw logs and label prompt-processing vs generation metrics rather than assuming their fields are identical.
- If one engine cannot load or generate from the exact file, record failure evidence; do not substitute a different format or quantization.

## Execution order

1. Run `bash preflight_qwen3_30b_a3b_iq3_xxs.sh` (read-only, no model download).
2. Inspect the output and confirm exact model source/variant plus disk/memory feasibility.
3. Run `bash run_qwen3_30b_a3b_iq3_xxs.sh --model /absolute/path/to/model.gguf --run` only after confirming the target file exists and the host is ready. It runs llama.cpp then RustingStrata sequentially; it does not run TensorFold on an unsupported target.
4. Review raw logs and fill `results-template.csv`; do not enter estimates as measurements.

## Isolation

Scripts do not modify `~/ods/.env`, Compose, ODS model routing or the active llama-server. Benchmark runs are sequential and use local CLI benchmark modes where possible. Only run commands spawned by this benchmark; do not stop unrelated model services.
