# Inference on an RTX 3050 4 GB — October 2026 Reproducible Report

**Test date:** October 22, 2026  
**Status:** Initial benchmark documented; local evidence bundle attached to this PR branch.  
**System:** Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM), CUDA 13.0, driver 580.178.04, compute capability sm_86.

> **Evidence bundle:** [Download the results collection (tar.gz)](artifacts/inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz). Size reported by GitHub: 25,853 bytes. GitHub blob SHA: `546f6c75bb449489ce6996047701ab08ca72c0a8`. The local archive's SHA-256 is stored in `inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz.sha256` on the machine that created the bundle; a separate checksum sidecar has not been published. Verify the SHA-256 after downloading against the original local value.

## Executive summary

Two distinct configurations were measured on the same machine:

1. **llama.cpp + Qwen3-30B-A3B-Instruct-2507 IQ3_XXS**, using `llama-bench`, varying `--n-gpu-layers` across 0, 1, and 8 with three repetitions per setting.
2. **TensorFold 1.1.1 + Qwen3.5-2B-MLX-4bit**, using five sequential HTTP requests to an OpenAI-compatible API.

These are not equivalent models and do not use the same protocol; their raw speeds should not be interpreted as a direct ranking of inference engines.

## Hardware and environment

- CPU: Intel Core i7-12650H.
- System memory: approximately 14 GiB.
- GPU: NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- NVIDIA driver: 580.178.04; reported CUDA version: 13.0.
- Compute capability: sm_86.
- Operating system: Ubuntu/Linux.
- An Xid 31 was observed with llama-server in earlier tests; as a precaution, critical tests should be repeated while recording kernel/GPU errors.

## Experiment A — llama.cpp

### Configuration

- Model: `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`.
- Model SHA-256: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`.
- Size reported by `llama-bench`: 11.37 GiB.
- Build: `6fa4f6cd3 (11740)`.
- Threads: 8.
- Prefill: `pp128`; generation: `tg32`.
- GPU layers: 0, 1, and 8.
- Repetitions: 3 per configuration; nine runs total, all with exit code 0.

### Results by repetition

| GPU layers | Repetition | pp128 (tok/s) | tg32 (tok/s) |
|---:|---:|---:|---:|
| 0 | 1 | 13.69 | 1.45 |
| 0 | 2 | 24.42 | 1.41 |
| 0 | 3 | 29.55 | 1.60 |
| 1 | 1 | 57.28 | 1.44 |
| 1 | 2 | 76.25 | 1.40 |
| 1 | 3 | 89.89 | 2.14 |
| 8 | 1 | 69.08 | 1.88 |
| 8 | 2 | 26.38 | 1.65 |
| 8 | 3 | 9.41 | 1.95 |

### Statistics

| GPU layers | Test | Mean tok/s | Median tok/s | Standard deviation | Min | Max |
|---:|---|---:|---:|---:|---:|---:|
| 0 | pp128 | 22.553 | 24.420 | 8.093 | 13.69 | 29.55 |
| 0 | tg32 | 1.487 | 1.450 | 0.100 | 1.41 | 1.60 |
| 1 | pp128 | 74.473 | 76.250 | 16.377 | 57.28 | 89.89 |
| 1 | tg32 | 1.660 | 1.440 | 0.416 | 1.40 | 2.14 |
| 8 | pp128 | 34.957 | 26.380 | 30.746 | 9.41 | 69.08 |
| 8 | tg32 | 1.827 | 1.880 | 0.157 | 1.65 | 1.95 |

### Interpretation

- In this sample, `ngl=1` achieved the highest median prefill speed.
- `ngl=8` showed very high prefill variability; no cause should be assigned without repeating under controlled conditions.
- Generation (`tg32`) remained approximately between 1.40 and 2.14 tok/s.
- The `nvidia-smi` snapshot was taken after the run, not during it, so it does not represent peak utilization.
- An exit code of 0 does not replace checks for stability, driver errors, and memory use during the test.

## Experiment B — TensorFold

### Configuration and results

- Engine: TensorFold 1.1.1, CUDA backend.
- Model: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- Context: 2048 tokens; parallelism 1; thinking disabled; temperature 0; maximum output 128 tokens.
- Five sequential HTTP requests; 66 input tokens and 128 output tokens reported per request; all returned HTTP 200.

| Run | HTTP | Reported speed (tok/s) | Client time (s) | TTFT (s) | Prefill (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 200 | 107.068 | 1.249233 | 0.051058 | 0.048931 |
| 2 | 200 | 103.407 | 1.317400 | 0.084446 | 0.080437 |
| 3 | 200 | 106.496 | 1.280382 | 0.084646 | 0.080489 |
| 4 | 200 | 103.677 | 1.312622 | 0.084926 | 0.080445 |
| 5 | 200 | 106.455 | 1.280760 | 0.084702 | 0.080406 |

| Metric | Mean | Median | Minimum | Maximum |
|---|---:|---:|---:|---:|
| Reported speed (tok/s) | 105.421 | 106.455 | 103.407 | 107.068 |
| HTTP client time (s) | 1.288079 | 1.280760 | 1.249233 | 1.317400 |
| Reported TTFT (s) | 0.077956 | 0.084646 | 0.051058 | 0.084926 |
| Reported prefill (s) | 0.074142 | 0.080437 | 0.048931 | 0.080489 |

All five outputs have the same SHA-256: `942ca6d9de584e12bd4f207d8cafddcffb594924f5d781501b267b7a1ca9ddad`.

### Interpretation and limitations

- Every response reached the 128-token limit; outputs may be truncated.
- Client latency measures the complete HTTP request and is not equivalent to internal generation time.
- Reported speculative acceptance was 1 accepted token out of 56 proposed per request (1.7857%).
- An identical hash confirms identical output text only for this prompt and configuration.
- The end-of-test GPU snapshot does not measure peak usage during each request.

## Earlier tests: Qwen3.5-4B across three engines

Results from earlier tests recorded in conversations/terminal output; they have not been revalidated in this update. The initial Strata microbenchmark used context 1024 and output `tg64`; the later API protocol aimed for context 256 and a maximum of 32 output tokens.

| Engine | Model/format | Prefill | Decode | Approx. VRAM | Notes |
|---|---|---:|---:|---:|---|
| TensorFold | Qwen3.5-4B MLX-4bit | Not recorded | 53.42–53.64 tok/s | 3120 MiB | Load ~6.4 s; TTFT 0.193–0.212 s. |
| llama.cpp CUDA | Qwen3.5-4B GGUF Q4_K_M | 141.2 tok/s | 42.4 tok/s | 2808 MiB | `--n-gpu-layers 99`. |
| Rusting Strata 1.0.1 | Qwen3.5-4B GGUF Q4_K_M | 915.3 tok/s pp128; 986.5 pp512 | 46.6/46.1 tok/s tg64 | 2928 MiB | ctx=1024, 3 repetitions. |

Recorded Strata command:

~~~bash
cd "$HOME/rusting-strata-test"
./target/release/strata bench --gpu \
  --model "$HOME/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf" \
  --pp 128,512 --tg 64 --reps 3 --ctx 1024
~~~

Warning: an earlier TensorFold attempt produced 64 and 128 tokens despite a configured maximum of 32. Actual token counts should be verified in each JSON file.

## Qwen3.5-35B-A3B IQ2_XXS and inconclusive errors

- File: `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`, 10,676,139,840 bytes.
- Recorded SHA-256: `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`.
- Strata identified architecture qwen35moe, 40 layers, 256 experts, 8 active experts, embedding size 2048.
- TensorFold MLX was estimated to require around 20.4 GB and was considered infeasible on this system with 14 GiB RAM / 4 GiB VRAM.
- There is no validated TTFT/tok/s measurement for the 35B model; treat this as an incomplete experiment.
- Error observed in earlier Strata tests: `CUDA_ERROR_UNSUPPORTED_PTX_VERSION`. Changing cudarc from `cuda-13010` to `cuda-13000` allowed compilation but did not resolve the runtime failure. GPU sm_86, driver 580.178.04, CUDA 13.0, and NVRTC 13.4.92.

## Engine coverage status

| Engine | Available status | Remaining work |
|---|---|---|
| mistral.rs | CUDA 0.9.5 installation recorded; no consolidated comparable results | Capture load, version, VRAM, TTFT, prefill/decode, and repetitions |
| vLLM | Proposed; no validated measurements | Verify model/quantization support and memory requirements |
| SGLang | Proposed; no validated measurements | Verify support and capture failures |
| KTransformers | Proposed; no validated measurements | Verify model, backend, and memory requirements |
| TensorFold | Measured with Qwen3.5-2B and earlier 4B MLX test | Standardize protocol and validate output limits |
| llama.cpp CUDA | Measured with Qwen3.5-4B and Qwen3-30B-A3B | Repeat with telemetry captured during execution |
| Rusting Strata | Measured with Qwen3.5-4B; 35B inspection and PTX diagnosis | No validated 35B performance result |

Do not treat unmeasured engines as having zero speed. Label them according to the evidence as “not measured,” “unsupported,” or “failed to start.”

## Reproducibility and artifacts

The attached bundle gathers available scripts, logs, CSV/JSON files, system information, and hashes. It does not include model weights or caches. Read the missing-artifacts manifest alongside the inventory: the absence of explicitly missing paths does not prove that collection is exhaustive.

- [Collector script](https://github.com/robertosantosx2/LEONES/blob/docs/report-inferencia-denso-octubre-2026/scripts/benchmarks/collect-inferencia-rtx3050-oct26.sh)
- [Evidence bundle](artifacts/inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz)
- [PR #112](https://github.com/robertosantosx2/LEONES/pull/112)

For future comparisons, keep the model/format, prompt/tokenizer, context, actual output length, temperature, and repetitions fixed. Measure TTFT, prefill/decode, total time, actual token counts, peak VRAM/RAM, swap, GPU temperature/power, exit codes, and errors. Keep native microbenchmarks, API tests, failed attempts, and quality evaluations separate.


## Detailed loading diagnostics — Qwen3-30B-A3B-Instruct-2507 IQ3_XXS (2026-10-21)

**Checkpoint:** `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`  
**SHA-256:** `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`  
**Original Ubuntu log directory:** `~/benchmarks/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/`

### llama.cpp — startup observations in the supplied excerpts

The supplied excerpts from `llama/rep-2.log` through `llama/rep-6.log` confirm that the model loaded onto the RTX 3050 Laptop GPU. They contain the following observations:

- Startup device line: `NVIDIA GeForce RTX 3050 Laptop GPU (3768 MiB, 3675 MiB free)`.
- Layers 35–48 were assigned to `CUDA0`; the memory summary reports a **3290.68 MiB** CUDA model buffer, **26.00 MiB** KV cache, and **86.25 MiB** compute buffer.
- Non-fatal fallback message: `tensor 'token_embd.weight' (iq3_s) (and 420 others) cannot be used with preferred buffer type CUDA_Host, using CPU instead`.
- Repeated context warning: `CUDA_Host compute buffer size of 4.1376 MiB, does not match expectation of 1.0636 MiB`.
- The memory summary reports 3768 MiB CUDA allocation: 239 MiB + (3402 MiB = 3290 + 26 + 86) + 125 MiB.

These messages are not evidence of a fatal startup failure. The previously recorded six-run batch returned exit code `0` for every run. Preserve the `CUDA_Host` message as a diagnostic warning; do not claim it caused a failure without further evidence.

### Reference launch commands

```bash
# llama.cpp 0.7.0-dev, build 11740, commit 6fa4f6cd3
/usr/bin/time -v -o "$d/time-$i.txt" \
  "$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli" \
    --model "$M" --n-gpu-layers 14 --fit off \
    --ctx-size 1024 --batch-size 64 --ubatch-size 32 \
    --threads 8 --predict 128 --temp 0 --seed 42 \
    --prompt "$PROMPT" --single-turn --simple-io --verbose \
    > "$d/rep-$i.log" 2>&1

# RustingStrata 1.0.1
XDG_CACHE_HOME="$OUT/strata/cache" /usr/bin/time -v \
  -o "$d/time-$i.txt" "$HOME/rusting-strata-test/target/release/strata" generate \
    --model "$M" --gpu --ctx 1024 --threads 8 \
    --prompt "$PROMPT" -n 128 --temp 0 \
    > "$d/rep-$i.log" 2>&1
```

### Evidence-file status

The excerpts shared in chat are `grep` output, not the complete original logs. The original files to include in the repository are `llama/rep-{1..6}.log`, `llama/time-{1..6}.txt`, `llama/rc-{1..6}.txt`, `strata/rep-{1..6}.log`, `strata/time-{1..6}.txt`, and `strata/rc-{1..6}.txt`, plus a SHA-256 manifest. This update documents the verifiable messages supplied; it does not misrepresent excerpts as complete log files.
