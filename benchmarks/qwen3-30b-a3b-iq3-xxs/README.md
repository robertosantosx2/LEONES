# Qwen3-30B-A3B IQ3_XXS: benchmark preparation

Status: **prepared, not executed on the Ubuntu host** (2026-10-21).

## Decision and scope

Target remains **Qwen3-30B-A3B IQ3_XXS**, using the Instruct checkpoint selected for this evaluation. Do not silently substitute Qwen3.5, a different quantization, or a converted checkpoint.

Compare TensorFold, llama.cpp and RustingStrata only when each engine can load equivalent weights and tokenizer/template. An engine that cannot load this exact artifact is reported as **unsupported / not comparable**, not assigned a fabricated speed.

Hardware target from previous host checks: Ubuntu, NVIDIA RTX 3050 Laptop (4 GiB VRAM), 14 GiB RAM. This is a tight memory budget for a ~30B-parameter IQ3_XXS model: check the actual GGUF size, free RAM, swap, and available disk before downloading or loading. Do not download the model automatically or alter ODS configuration.

## Why compatibility gates come first

- **llama.cpp:** first candidate for the GGUF IQ3_XXS artifact. Verify the local build supports this Qwen3 architecture and IQ3_XXS tensor types.
- **RustingStrata:** do not assume support merely because it can run other GGUF models. Confirm the Qwen3 (not Qwen3.5) architecture, IQ3_XXS tensor types, chat template and server interface.
- **TensorFold:** previous experiments used an MLX checkpoint/quantization path, which is not equivalent to GGUF IQ3_XXS. Unless the current TensorFold checkout explicitly supports this exact checkpoint/quantization on the NVIDIA/Linux host, record it as unsupported. Do not convert to another quantization and call it IQ3_XXS.

## Controlled protocol

Reuse the prior benchmark conventions where applicable:
- sequential runs only; one engine resident at a time;
- context 256; max generated tokens 32; 1 warm-up + 3 measured runs;
- same prompt, sampling parameters, tokenizer/chat template where supported;
- fixed seed if the engine supports it;
- record model file name, exact source/revision, SHA-256, engine commit/version, launch arguments and all failures;
- record load time, prefill tok/s, generation tok/s, wall time, peak RAM, peak VRAM, GPU layer/offload settings and exit status;
- do not compare a TensorFold different-format checkpoint against GGUF IQ3_XXS as an apples-to-apples result.

## Before running on Ubuntu

1. Run `preflight_qwen3_30b_a3b_iq3_xxs.sh` from this directory.
2. Confirm the exact model source and license, download only if disk/RAM feasibility is acceptable, and calculate SHA-256.
3. Capture the actual CLI help/version for all three engines. Fill the engine-specific launch adapters only after verifying their syntax.
4. Run llama.cpp first as the reference. Then attempt RustingStrata and TensorFold only after their compatibility gates pass.
5. Copy `results-template.csv` and the generated preflight report into the results directory; update the comparison report with measured values, not estimates.

## Safety / isolation

The scripts must not edit `~/ods/.env`, Docker Compose, the active ODS llama-server, or existing benchmark outputs. Use dedicated loopback ports (18084–18086) and stop only processes started by this benchmark. Do not run engines concurrently on a 4 GiB GPU.
