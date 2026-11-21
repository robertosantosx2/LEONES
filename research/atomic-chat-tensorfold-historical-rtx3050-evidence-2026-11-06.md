# Historical TensorFold CUDA inference on the RTX 3050 — evidence reconciliation

**Date:** 2026-11-06  
**Purpose:** correct the Atomic Chat TensorFold spike's candidate assessment using earlier physical RTX 3050 experiments already recorded in LEONES.  
**Host:** Ubuntu x86_64, Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB (SM 8.6), driver 580.178.04, CUDA 13.0.

## Executive correction

The statement that no TensorFold model had ever completed inference on the reference RTX 3050 was incorrect. LEONES contains multiple successful physical CUDA runs:

1. TensorFold Native **1.1.1** served Qwen3.5-2B and Qwen3.5-4B on this exact RTX 3050 in October.
2. TensorFold Native **1.1.2** also has a documented Qwen3.5-4B execution.
3. The user's experimental TensorFold **PR #1879** build (b880e52707780032c3bad1b3086657c41df89ffb) loaded the same Qwen3.5-4B checkpoint on the RTX 3050 where the matched baseline failed with CUDA_ERROR_OUT_OF_MEMORY, then completed three real chat requests.

These results do not prove that the currently installed TensorFold 1.2.3 binary has the same memory behavior, nor that a new Atomic Core gateway has been tested. They do prove that the GPU and model family are not inherently unsuitable, and they give Atomic Chat a known model/checkpoint and context to target.

## 1. TensorFold 1.1.1 — Qwen3.5-2B and Qwen3.5-4B

Source report: [TensorFold local: Qwen3.5 tests on Ubuntu — 2026-10-19](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/tensorfold-qwen35-local-results-2026-10-19.md).

| Model | Context | Decode speed | TTFT | TensorFold process VRAM | Result |
|---|---:|---:|---:|---:|---|
| Qwen3.5-2B MLX 4-bit, group 64 | 1024 | 95.08 tok/s (32-token sample); 105.71 tok/s (128-token sample) | 88.2 ms; 94.1 ms | ~2,388 MiB | Real Spanish inference |
| Qwen3.5-4B MLX 4-bit, group 64 | 512 | 53.64 tok/s (64 tokens); 53.42 tok/s (128 tokens) | 193 ms; 212 ms | ~3,120 MiB | Real Spanish inference |

For the 2B run, total GPU use after inference was 2,411 / 4,096 MiB. For the 4B run, total GPU use was 3,143 / 4,096 MiB. The 4B model load was recorded at 6.4 seconds in the original report.

The exact 2B checkpoint revision was 93760be4f1f69842a46bc13dbdc0f19e291392a3. The exact 4B revision used by the October run was 32f3e8ecf65426fc3306969496342d504bfa13f3.

These are short measured samples, not sustained throughput guarantees. The 2B/4B report and inventory distinguish per-process VRAM from total GPU use.

## 2. Four-runtime benchmark — 2026-10-21

Sources:
- [Four-runtime sequential Qwen3.5-4B benchmark](https://github.com/robertosantosx2/LEONES/blob/docs/qwen35-4b-cuda-2026-10-21/docs/benchmarks/qwen35-4b-four-runtimes-2026-10-21.md)
- [CUDA model verification report](https://github.com/robertosantosx2/LEONES/blob/docs/qwen35-4b-cuda-2026-10-21/docs/reports/informe-verificacion-modelo-cuda-2026-10-21.md)

The sequential benchmark ran TensorFold, llama.cpp CUDA, RustingStrata and Mistral.rs on the same Ubuntu/RTX 3050. It used context 256, a 30-token prompt, temperature 0, a 32-token output cap, three measured requests per runtime plus separate warm-up. All twelve measured API requests returned HTTP 200.

| Runtime | Median request latency | Median generation | Median TTFT | Model load |
|---|---:|---:|---:|---:|
| TensorFold MLX-4bit | 0.7068 s | 54.743 tok/s | 0.1306 s | 8.6 s |
| llama.cpp CUDA GGUF Q4_K_M | 0.8337 s | 47.500 tok/s | n/d | Not isolated |
| RustingStrata GGUF Q4_K_M | 0.8392 s | n/d | n/d | n/d |
| Mistral.rs GGUF Q4_K_M | 6.1753 s | 6.194 tok/s | n/d | 2.682 s for weight-load phase only |

The report correctly warns that TensorFold used MLX-4bit while the other runtimes used GGUF Q4_K_M; this is a practical deployment comparison, not an identical-artifact engine benchmark.

## 3. TensorFold PR #1879 — physical RTX 3050 run and baseline A/B

Upstream PR: [ashhart/TensorFold#1879 — fix(cuda): allocate Qwen3.5 scratch lazily](https://github.com/ashhart/TensorFold/pull/1879).

Detailed LEONES record: [Qwen3.5-4B CUDA memory admission and scratch geometry](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/qwen35-4b-tensorfold-memory-admission-pr1879-2026-11-02.md).

### Experimental build receipt

- Tested commit: b880e52707780032c3bad1b3086657c41df89ffb.
- Binary: isolated Linux x86_64 CUDA SM 86 ReleaseFast build.
- Model: mlx-community/Qwen3.5-4B-MLX-4bit, revision 32f3e8ecf65426fc3306969496342d504bfa13f3.
- GPU: RTX 3050 Laptop, 4,096 MiB.
- Context 512, parallel 1, max-inflight 1.
- TENSORFOLD_MEMORY_RESERVE_GIB=0.5; HF offline.
- Backend server on 127.0.0.1:18083; separate isolated baseline port 18084.
- Weights 2.81 GiB; scratch reported 0.21 GiB for the 512-row window; model loaded in 10.4 seconds.

Three real chat requests returned HTTP 200:

| Request | Output tokens | Decode | TTFT | Prefill | Finish |
|---|---:|---:|---:|---:|---|
| Thinking ON | 128 | 56.05 tok/s | 194.1 ms | 188.1 ms | length |
| Thinking OFF | 192 | 54.32 tok/s | 187.6 ms | 184.1 ms | length |
| Thinking OFF | 133 | 55.92 tok/s | 187.2 ms | 183.5 ms | stop |

Global nvidia-smi monitoring observed 3,211–3,215 MiB after load and a maximum of 3,227 MiB used / 542 MiB free during the third inference. This is a one-second global monitor, not per-buffer scratch profiling.

### Matched baseline comparison

The baseline and PR build used the same GPU, exact checkpoint revision, CUDA backend, context 512, parallel/max-inflight 1 and 0.5 GiB reserve.

- Baseline commit 089a18dff289d4c58043c1957ad0d7fe73d814b3: failed before server readiness with cuMemAlloc: CUDA_ERROR_OUT_OF_MEMORY; no inference request could connect.
- PR #1879 commit b880e52707780032c3bad1b3086657c41df89ffb: loaded in 10.4 seconds and completed three HTTP 200 inference requests.

This confirms a **functional load/admission advantage on the tested 4 GiB RTX 3050**. It is not a decode-speedup comparison because the baseline never served a request. The baseline monitor captured idle GPU state but did not capture the failed allocation peak, so the exact scratch bytes saved were not measured.

The experimental branch also passed the isolated host scratch/admission tests and the reported CUDA SM86 build targets. The full test-cuda-host suite was not green and must not be described as passing.

### Important model-output caveat

One generated response incorrectly explained lazy scratch as moving model weights into host RAM. That explanation is false. PR #1879 lazily allocates CUDA scratch buffers; it does not offload the language-model weights to RAM or increase physical VRAM.

## 4. Why TensorFold info is not a hard VRAM fit verdict

The Atomic Chat PoC initially treated the memory floor line as a hard comparison against free VRAM. That is too strict for this known checkpoint.

On the currently installed 1.2.3 binary, the exact dense Qwen3.5-4B MLX checkpoint reports:
- weights: 2.85 GiB;
- memory floor: 4.85 GiB (weights plus a generic 2.00 GiB runtime margin).

Yet the same model/checkpoint family has completed real inference on this 4 GiB GPU with TensorFold 1.1.1 and the PR #1879 experimental build. Therefore the 4.85 GiB figure is a conservative information/admission estimate, not a measurement of the actual peak VRAM of those earlier runs and not a universal physical impossibility proof.

It remains useful as a warning and for comparing candidate checkpoints. It must not be silently interpreted as a measured peak or used to erase contrary measured receipts. Conversely, the old receipts do not prove the current 1.2.3 baseline will load: the matched PR #1879 experiment demonstrates that a later baseline had a real CUDA allocation regression.

## 5. Implications for Atomic Chat

1. **Use Qwen3.5-4B MLX-4bit at revision 32f3e8ecf65426fc3306969496342d504bfa13f3 as the first reference checkpoint**, with context 512, parallel 1 and max-inflight 1. It is already cached and physically proven on this machine.
2. Keep Qwen3.5-2B as a second historical reference (revision 93760be4f1f69842a46bc13dbdc0f19e291392a3, context 1024). It has completed real CUDA inference on this same RTX 3050.
3. Do not use the generic 4.85 GiB info floor as a measured peak. Keep it as a warning; require the separate 3072 MiB free-VRAM safety guard and use a known-good model/version profile for any explicit override.
4. For the current 1.2.3 line, prefer a build containing the user's rebased PR #1879 work once its code checks and review requirements are satisfied. The old b880e527 GPU receipt is not a receipt for the newer rebase head.
5. First prove the exact binary/checkpoint through /health, /v1/models, JSON chat and SSE on loopback. Then test the Atomic Core managed gateway, bearer authentication, Host validation, key stripping, lifecycle and cancellation.
6. Keep the Atomic Chat implementation PR a draft until that current binary/gateway acceptance is complete.

## 6. Evidence and source links

- [October 19 Qwen3.5 local results](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/tensorfold-qwen35-local-results-2026-10-19.md)
- [October 20 Qwen3.5/TensorFold/llama.cpp inventory](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md)
- [October 21 four-runtime benchmark](https://github.com/robertosantosx2/LEONES/blob/docs/qwen35-4b-cuda-2026-10-21/docs/benchmarks/qwen35-4b-four-runtimes-2026-10-21.md)
- [October 21 CUDA verification report](https://github.com/robertosantosx2/LEONES/blob/docs/qwen35-4b-cuda-2026-10-21/docs/reports/informe-verificacion-modelo-cuda-2026-10-21.md)
- [November 2–3 PR #1879 memory/scratch report](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/qwen35-4b-tensorfold-memory-admission-pr1879-2026-11-02.md)
- [TensorFold upstream PR #1879](https://github.com/ashhart/TensorFold/pull/1879)
