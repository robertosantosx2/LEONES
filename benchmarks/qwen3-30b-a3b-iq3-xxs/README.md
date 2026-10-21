# Qwen3-30B-A3B IQ3_XXS: benchmark preparation

Status: **prepared, not executed on the Ubuntu host** (2026-10-21).

## Decision and scope

Target remains **Qwen3-30B-A3B IQ3_XXS**. Preserve the exact model variant/revision selected for this test; do not silently substitute Qwen3.5, another quantization, or a converted checkpoint. Confirm whether the selected repository is the original Instruct or Instruct-2507 variant before downloading.

## Compatibility gates (evidence-based)

- **llama.cpp — reference candidate.** Upstream source includes Qwen3 model support and the IQ3_XXS GGML/GGUF quantization type. That establishes format/type support in upstream, not that the user's local build or exact file is valid. See [llama.cpp quantization definitions](https://github.com/ggml-org/llama.cpp/blob/master/include/llama.h) and [GGUF quantization implementation](https://github.com/ggml-org/llama.cpp/blob/master/gguf-py/gguf/constants.py).
- **RustingStrata — compatibility unverified.** Must confirm Qwen3 (not only Qwen3.5) architecture, IQ3_XXS tensors, tokenizer/chat template, and execution path from the checked-out source/version. Do not infer support from generic GGUF support.
- **TensorFold — exact path likely not equivalent.** TensorFold releases frequently use MLX checkpoints for Apple silicon. A GGUF IQ3_XXS file is not an MLX checkpoint. Only compare if the actual TensorFold build supports the exact Qwen3-30B-A3B checkpoint and IQ3_XXS representation on this Linux/NVIDIA system; otherwise report **not comparable / unsupported**. Do not convert to another quantization and label it IQ3_XXS.

## Hardware and memory

Target host from earlier checks: Ubuntu, NVIDIA RTX 3050 Laptop (4 GiB VRAM), 14 GiB RAM. This is a tight budget for a ~30B-parameter IQ3_XXS model. The active weights are not determined by the A3B active-parameter count alone: the full model weights must be represented in memory/storage. Check exact file size, free RAM, swap and disk before downloading/loading. No automatic download is authorized by these scripts.

## Controlled protocol

Reuse prior benchmark conventions where applicable:
- sequential runs only; one engine resident at a time;
- context 256; max generated tokens 32; one warm-up + three measured runs;
- identical prompt and sampling settings; fixed seed where supported;
- record exact model source/revision, file name and SHA-256, engine commit/version, command line, chat template, exit status and failure logs;
- record load time, prefill tok/s, generation tok/s, wall time, peak RAM, peak VRAM and GPU offload configuration;
- do not compare TensorFold using a different-format/different-quantization checkpoint as an apples-to-apples IQ3_XXS result;
- label first-token latency/prefill precisely: engines may define or report these differently.

## Preparation now; host run later

1. Review this PR and the preflight script.
2. On Ubuntu, run the read-only preflight and capture engine paths/version/help and model-file candidates.
3. Confirm the exact model repository/revision and license; download only after checking available disk and memory.
4. Validate GGUF metadata and SHA-256; check architecture and tensor types.
5. Run llama.cpp first as the reference. Test RustingStrata only after its compatibility gate passes. Test TensorFold only if exact Linux/NVIDIA + checkpoint/quantization support is proven.
6. Save outputs in a new timestamped directory; update the results CSV and comparison report with measured values, not estimates.

## Isolation / safety

The preflight script does not download models, start servers, install packages, or modify ODS. Benchmark runs must not edit `~/ods/.env`, Docker Compose, or the active ODS llama-server. Use dedicated loopback ports (18084–18086) if server mode is needed and stop only processes started by this benchmark. Do not run engines concurrently on a 4 GiB GPU.
