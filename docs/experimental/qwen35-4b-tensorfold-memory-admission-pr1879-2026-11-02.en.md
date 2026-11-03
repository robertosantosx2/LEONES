# Qwen3.5-4B on TensorFold CUDA: scratch geometry, memory admission, and physical A/B validation

**Date:** 2026-11-02 to 2026-11-03  
**Status:** Physical baseline-versus-PR comparison completed on Ubuntu. TensorFold PR #1879 remains open and unmerged.  
**Hardware:** MSI Thin 15 B12UC; NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM, compute capability SM 86; Intel Core i7-12650H.  
**Test isolation:** Separate worktrees and binaries were used. The user's stable TensorFold installation and the usual llama.cpp server on port 8080 were not changed.

## Executive result

Under the same GPU, checkpoint, checkpoint revision, CUDA backend, 512-token context, single-stream settings and explicit 0.5 GiB memory reserve:

- The baseline commit `089a18dff289d4c58043c1957ad0d7fe73d814b3` failed during model loading with `CUDA_ERROR_OUT_OF_MEMORY` from `cuMemAlloc`.
- PR commit `b880e52707780032c3bad1b3086657c41df89ffb` loaded Qwen3.5-4B in 10.4 seconds and completed three real HTTP inference requests.
- The PR build reported 54.32–56.05 tokens/s, TTFT 187.2–194.1 ms, and a maximum observed global GPU memory use of 3,227 MiB (542 MiB free).

**Interpretation:** this is direct evidence of a functional model-loading/admission advantage for the tested RTX 3050 4 GiB configuration. It is not a percentage speedup measurement, because the baseline never reached inference. It does not quantify the exact number of scratch bytes saved.

## 1. Historical reference: TensorFold 1.1.1

LEONES previously recorded a successful physical run:

- Engine: TensorFold native 1.1.1, CUDA.
- Model: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- Hugging Face revision: `32f3e8ecf65426fc3306969496342d504bfa13f3`.
- GPU: NVIDIA RTX 3050 Laptop, 4 GiB.
- Context: 512.
- Model load: 6.4 s.
- Decode: 53.64 tokens/s (64 generated tokens) and 53.42 tokens/s (128 generated tokens).
- TTFT: 193 ms and 212 ms.
- VRAM: 3,120 MiB attributed to the process; 3,143 / 4,096 MiB in the global capture.
- Output: real Spanish inference.

Original record: [TensorFold local Qwen3.5 Ubuntu results — 2026-10-19](https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/tensorfold-qwen35-local-results-2026-10-19.md). Related inventory: [Qwen3.5 TensorFold and llama.cpp comparison](./inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md).

An earlier rejection with `TENSORFOLD_CUDA_MEMORY_LIMIT_GB=3.4` and a 0.5 GiB reserve reported 1.3 GiB free and only 0.8 GiB available against approximately 2.8 GiB of weights. That specific rejection was caused by the configured limit and memory available at that moment; it is not, by itself, proof of a scratch estimator defect. The later successful 512-context run is a separate historical result and must not be conflated with the PR experiment below.

## 2. Model geometry used for the scratch calculation

Checkpoint configuration:

| Parameter | Value |
|---|---:|
| hidden_size | 2,560 |
| intermediate_size | 9,216 |
| num_hidden_layers | 32 |
| vocab_size | 248,320 |
| num_attention_heads | 16 |
| num_key_value_heads | 4 |
| linear_num_key_heads | 16 |
| linear_num_value_heads | 32 |
| head_dim | 256 |
| MLX quantization | 4-bit, group size 64 |
| Architecture | Dense, not MoE |

Source: [Qwen3.5-4B checkpoint config.json](https://huggingface.co/mlx-community/Qwen3.5-4B-MLX-4bit/blob/32f3e8ecf65426fc3306969496342d504bfa13f3/config.json).

Derived widths used by `cuda_geometry.zig`:

- `valueWidth = 32 × 128 = 4,096`.
- `attnWidth = 16 × 256 = 4,096`.
- `convWidth = (2 × 16 + 32) × 128 = 8,192`.
- `wide = max(valueWidth, attnWidth, hidden) = 4,096`.
- `max(intermediate, wide) = 9,216`.
- `g.moe() = false`; routed-expert scratch is not allocated.

### Scratch formula

The scratch calculation was reconstructed from the engine's individual allocations, including TensorFold's 256-byte per-buffer alignment.

Fixed verification buffers:

| Buffer | Bytes |
|---|---:|
| `pm` | 524,288 |
| `pl` | 524,288 |
| `po` | 134,217,728 |
| `logits` | 63,569,920 |
| `amax` | 62,464 |
| `picks` | 1,048,576 |
| **Fixed total** | **199,947,264 bytes = 190.68457 MiB** |

Row-dependent buffers total **159,616 bytes = 155.875 KiB per row**:

| Group | Bytes per row before alignment |
|---|---:|
| `h/x/r` | 15,360 |
| `y/mix/z/v` | 32,768 |
| `q/k` | 8,192 |
| `qkv` | 16,384 |
| `gate/up/act` | 55,296 |
| `xs` | 576 |
| `a/b/beta` | 192 |
| `g_` | 128 |
| `qraw` | 16,384 |
| `qn` | 8,192 |
| `kraw/vraw/kn` | 6,144 |
| **Total** | **159,616** |

For these row sizes, each allocation's 256-byte alignment is already satisfied. Therefore:

`S(R) = 199,947,264 + 159,616 × R bytes`

This describes the dense Qwen3.5 forward scratch only. It excludes model weights, loading buffers, CUDA modules, KV caches, driver allocations and other processes.

| Rows | Scratch total | Savings vs 4,096 rows |
|---:|---:|---:|
| 32 | 195.55566 MiB | 618.62891 MiB |
| 64 | 200.42676 MiB | 613.75781 MiB |
| 128 | 210.16895 MiB | 604.01562 MiB |
| 256 | 229.65332 MiB | 584.53125 MiB |
| 512 | 268.62207 MiB | 545.56250 MiB |
| 4,096 | 814.18457 MiB | 0 MiB |

**Important context distinction:** the physical server experiment used a 512-token context. If scratch is correctly capped to the configured context, 512 rows—not 4,096—is the relevant upper bound for that run:

| Effective rows | Scratch | Savings vs 512 rows |
|---:|---:|---:|
| 32 | 195.55566 MiB | 73.06641 MiB |
| 64 | 200.42676 MiB | 68.19531 MiB |
| 128 | 210.16895 MiB | 58.45312 MiB |
| 256 | 229.65332 MiB | 38.96875 MiB |
| 512 | 268.62207 MiB | 0 MiB |

Do not mix the global kernel maximum with the configured-context comparison.

### Optional prompt INT8 workspace

With `K = max(9,216, 4,096, 4,096, 2,560) = 9,216`, the `cuda.w4a8.Kernels.scratch` workspace is:

`I(R) = R × K + 2 × R × (K / 64) × 4 = 10,368 × R bytes`

| Rows | INT8 workspace |
|---:|---:|
| 32 | 0.31641 MiB |
| 64 | 0.63281 MiB |
| 128 | 1.26563 MiB |
| 256 | 2.53125 MiB |
| 512 | 5.06250 MiB |

This workspace is present only when `--prompt-precision int8` is enabled. The INT8 exception flag adds another 4 bytes.

## 3. PR #1879: implementation and admission issue

PR: [fix(cuda): allocate Qwen3.5 scratch lazily](https://github.com/ashhart/TensorFold/pull/1879)  
Branch: `fix/qwen35-cuda-lazy-scratch`  
Tested head: `b880e52707780032c3bad1b3086657c41df89ffb`  
Base commit: `089a18dff289d4c58043c1957ad0d7fe73d814b3`

The change separates Qwen3.5 forward scratch from the persistent weights arena and allocates/grows scratch on demand. The optional prompt INT8 workspace also grows on demand.

Review identified a critical admission detail: adding `scratch_bytes` to the modeled model size alone is insufficient if `Pool.room()` ignores held/pending bytes when `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` is unset. Streams and prompt caches could otherwise be admitted into memory that a later scratch growth still needs.

Growth also has a temporary peak: the new allocation is reserved before the old allocation is released, so both buffers coexist during replacement. The admission calculation must account for this peak rather than only the final capacity.

The tested branch contains the following approach:

1. Pass the serving context into the engine and cap `scratch_rows` at `min(context, 4096)`.
2. Reserve the full replacement allocation when growth is required. The old buffer is already part of live CUDA usage; do not double-subtract it or reserve only the final size difference.
3. Subtract pending scratch from available room even when `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` is not set.
4. Apply the same accounting to the optional INT8 workspace, respecting the actual growth order and avoiding double-counting replacement buffers.
5. Move scratch sizing/growth code into `cuda_scratch.zig` to keep source files within project line-count constraints.

Relevant branch files: [cuda_scratch.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/families/qwen3_5/cuda_scratch.zig), [cuda_engine.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/families/qwen3_5/cuda_engine.zig), [cuda_native.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/families/qwen3_5/cuda_native.zig), [native/cuda.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/native/cuda.zig), [native/cuda_memory.zig](https://github.com/robertosantosx2/TensorFold/blob/fix/qwen35-cuda-lazy-scratch/zig/src/native/cuda_memory.zig).

## 4. Host tests and CUDA build

In the isolated PR worktree `~/tensorfold-pr1879-validation-20261102`, the user ran:

```sh
zig build test-qwen35-scratch-host -Dtarget=x86_64-linux-gnu
zig build test-cuda-memory-admission-host -Dtarget=x86_64-linux-gnu
PATH=/usr/local/cuda-13.4/bin:$PATH zig build check-native-cuda-host compile-cuda-tests -Dtarget=x86_64-linux-gnu
```

All four named targets returned to the shell prompt without visible errors. Record these as successful according to the reported terminal output. The output did not include explicit test counts.

The global `zig build test-cuda-host` run had failed commands and must **not** be described as a green full suite. Some output included a deliberately negative `FAIL no-op projection` test case; other CPU reference comparison failures came from existing quantized tests. These do not erase the successful isolated runs, but neither should they be hidden.

The native CUDA binary was built for Linux x86-64, CUDA SM 86, ReleaseFast, using `/usr/local/cuda-13.4/bin/nvcc`.

## 5. Physical PR execution on the RTX 3050 — 2026-11-03

### Exact setup

- Worktree: `~/tensorfold-pr1879-validation-20261102`.
- Binary: `zig-out-pr1879/native/bin/tensorfold-native`.
- Model: `mlx-community/Qwen3.5-4B-MLX-4bit`.
- HF revision: `32f3e8ecf65426fc3306969496342d504bfa13f3`.
- GPU: RTX 3050 Laptop, 4,096 MiB.
- Server: `127.0.0.1:18083`; context 512; parallel 1; max-inflight 1.
- Environment: `TENSORFOLD_MEMORY_RESERVE_GIB=0.5`, `HF_HUB_OFFLINE=1`.

The first attempt with the default 1 GiB reserve was rejected: approximately 3.6 GiB was free, leaving a 2.6 GiB budget against approximately 2.8 GiB of weights. With the explicit 0.5 GiB reserve, the model loaded.

Startup reported 2.81 GiB of weights, one stream, approximately 0.21 GiB of scratch for a 512-row window, and 10.4 seconds to load.

### Three real inference requests

All three requests returned HTTP 200.

| Metric | Thinking ON | Thinking OFF | Thinking OFF |
|---|---:|---:|---:|
| Evidence file | `pr1879-inference-128.json` | `pr1879-inference-no-thinking-192.json` | `pr1879-inference-no-thinking-256.json` |
| Prompt tokens | 51 | 56 | 59 |
| Generated tokens | 128 | 192 | 133 |
| Decode speed | 56.05 tok/s | 54.32 tok/s | 55.92 tok/s |
| TTFT | 194.1 ms | 187.6 ms | 187.2 ms |
| Prefill | 188.1 ms | 184.1 ms | 183.5 ms |
| Engine generation time | 2.266 s | 3.516 s | 2.360 s |
| Finish reason | `length` | `length` | `stop` |
| Speculative acceptance | 0/15 (0%) | 1/99 (1.01%) | 3/63 (4.76%) |

The third request set a 256-token maximum but generated 133 tokens and ended with `stop`; it was not truncated by the token limit. Speeds are server-reported values, not derived from total curl wall time.

Speculative acceptance was low in all three requests. There is no evidence that speculative decoding materially explains the observed throughput.

### GPU memory monitor

The one-second `nvidia-smi` capture `evidence/pr1879-gpu-monitor.csv` recorded:

- Idle before loading: 15 MiB used, 3,754 MiB free.
- During load: 3,055 MiB used.
- Stable after load: 3,211–3,215 MiB used.
- Maximum observed during the third inference: **3,227 MiB used**, with **542 MiB free**.
- GPU utilization reached 100% for several seconds; maximum observed temperature was 56 °C.

These are global GPU readings, not per-allocation profiling. They do not isolate the scratch buffer or prove how many bytes were materialized lazily. They do show that the PR server remained resident and completed all three inferences on the 4 GiB GPU without OOM.

### Output-quality caveat

One response incorrectly claimed that lazy CUDA allocation lets the model be stored in host RAM when VRAM is full. That is technically wrong and must not be repeated as an explanation of the patch.

The patch defers allocation of CUDA scratch buffers and accounts for pending growth when admitting streams and caches. It does not move model weights to host RAM, turn system RAM into VRAM, or permit allocations to exceed physical GPU memory. Any scratch needed by the active inference must still fit in available CUDA memory. The observed HTTP success is functional evidence, not a semantic-quality pass.

## 6. Controlled baseline-versus-PR comparison — 2026-11-03

### Identical conditions

| Parameter | Baseline | PR #1879 |
|---|---|---|
| Commit | `089a18dff289d4c58043c1957ad0d7fe73d814b3` | `b880e52707780032c3bad1b3086657c41df89ffb` |
| Binary | `zig-out-baseline/native/bin/tensorfold-native` | `zig-out-pr1879/native/bin/tensorfold-native` |
| Model | `mlx-community/Qwen3.5-4B-MLX-4bit` | Same |
| HF revision | `32f3e8ecf65426fc3306969496342d504bfa13f3` | Same |
| GPU | RTX 3050 Laptop, 4,096 MiB | Same |
| Backend/context | CUDA / 512 | Same |
| Concurrency | parallel 1, max-inflight 1 | Same |
| Reserve | `TENSORFOLD_MEMORY_RESERVE_GIB=0.5` | Same |
| HF mode | `HF_HUB_OFFLINE=1` | Same |
| Isolated port | 18084 | 18083 |

Both binaries were built locally on Ubuntu for x86-64, CUDA SM 86 and ReleaseFast, in separate worktrees. The stable installation and the user's usual port 8080 were not touched.

### Baseline outcome

The baseline failed during startup:

```text
error: cuMemAlloc: CUDA_ERROR_OUT_OF_MEMORY (2) out of memory
tensorfold: the native CUDA engine cannot load
/home/ssantos/.cache/huggingface/hub/models--mlx-community--Qwen3.5-4B-MLX-4bit/snapshots/32f3e8ecf65426fc3306969496342d504bfa13f3
with its own glue kernels (OutOfDeviceMemory)
```

The server never opened port 18084. The subsequent curl returned HTTP 000 / connection refused; no inference JSON was created. This is a consequence of the server failing to start, not a separate inference failure.

The baseline monitor file contains **142 lines: one header and 141 samples**, from `2026/11/03 00:54:04.339` through `2026/11/03 00:56:24.418`. All samples showed 15 MiB used and 3,754 MiB free; temperature ranged from 41 to 43 °C. GPU utilization was 0% in practically all samples, with 9% in the first sample.

**Capture limitation:** the monitor was running before the failed startup attempt and did not capture the failed allocation. Therefore, no baseline VRAM peak or allocation profile is available. The idle samples must not be presented as the memory footprint at the moment of OOM.

### Side-by-side outcome

| Result | Baseline | PR #1879 |
|---|---|---|
| Model load | **OOM in `cuMemAlloc`** | Loaded in 10.4 s |
| HTTP server | Did not start | Started on 127.0.0.1:18083 |
| HTTP 200 inferences | 0 | 3 |
| Decode speed | Not measurable | 54.32–56.05 tok/s |
| TTFT | Not measurable | 187.2–194.1 ms |
| Peak global GPU memory | Not captured during attempt | 3,227 MiB used; 542 MiB free |

There is no valid speedup percentage: the baseline did not reach the inference stage. There is also no directly comparable baseline peak-memory sample.

### Experimental verdict and limitations

**Functional advantage confirmed on the tested RTX 3050 4 GiB system:** the base commit failed to allocate CUDA memory while loading Qwen3.5-4B, whereas the PR commit loaded the same checkpoint and completed three real inferences under the same context, concurrency and reserve settings.

This supports the intended memory-admission/scratch-allocation correction. It does **not** quantify exact scratch savings, isolate the peak of each buffer, prove behavior at every context or concurrency level, or establish a throughput improvement over baseline. Further causal memory quantification would require profiling both versions at the exact allocation attempt with equivalent instrumentation; the baseline currently has no such peak capture because its startup failed before the monitor was started.

## 7. Evidence files and reproducibility

PR worktree: `~/tensorfold-pr1879-validation-20261102/evidence/`

- `pr1879-server-startup-reserve-05.log`
- `pr1879-gpu-monitor.csv`
- `pr1879-inference-128.json`
- `pr1879-inference-no-thinking-192.json`
- `pr1879-inference-no-thinking-256.json`

Baseline worktree: `~/tensorfold-pr1879-baseline-20261103/evidence/`

- `baseline-server-startup.log` — contains the CUDA OOM.
- `baseline-gpu-monitor.csv` — 142 lines, idle monitoring before the failed startup attempt.
- `baseline-inference-no-thinking-256.json` — **not created**, because curl could not connect to a server that never started.

The baseline worktree's `git status --short` showed `?? evidence/` and `?? zig-out-baseline/`. These are local untracked artifacts. Do not commit the build output directory `zig-out-baseline/`; retain the binary locally for reproducibility and archive selected logs/CSV/JSON evidence instead.

## 8. Validation status summary

| Validation | Result |
|---|---|
| Scratch geometry from model config and source | Calculated |
| Dedicated host scratch test | Passed according to reported terminal exit |
| Dedicated host memory-admission test | Passed according to reported terminal exit |
| `check-native-cuda-host` | Completed without visible error |
| `compile-cuda-tests` | Completed without visible error |
| Full `test-cuda-host` suite | **Not green; failed commands remain** |
| PR native CUDA build for SM 86 / ReleaseFast | Built |
| PR model load on physical RTX 3050 4 GiB | Passed with 0.5 GiB reserve |
| PR inference | 3 HTTP 200 requests |
| Baseline model load | Failed with CUDA OOM |
| Baseline inference | Not reached |
| Exact scratch bytes saved in physical execution | Not measured |
| Baseline-versus-PR speed comparison | Not possible |

## 9. Final conclusion

PR #1879 has demonstrated a **real functional loading and inference advantage** over the tested baseline for Qwen3.5-4B on the RTX 3050 Laptop GPU with 4 GiB VRAM. The baseline fails with `CUDA_ERROR_OUT_OF_MEMORY`; the PR loads and completes three inferences at approximately 54–56 tokens/s.

The claim should remain narrowly stated: this is evidence that the PR makes the model load and run in this controlled configuration. It is not proof of a specific percentage of VRAM saved, a lower measured baseline peak, or faster decoding than baseline. The PR remains open and unmerged.

Related PR: https://github.com/ashhart/TensorFold/pull/1879  
Spanish LEONES report: https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/qwen35-4b-tensorfold-memory-admission-pr1879-2026-11-02.md  
English LEONES report: https://github.com/robertosantosx2/LEONES/blob/main/docs/experimental/qwen35-4b-tensorfold-memory-admission-pr1879-2026-11-02.en.md
