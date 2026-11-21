# TensorFold Native 1.2.3 installation and capability evidence

**Captured:** 2026-11-05  
**Host:** Ubuntu, MSI Thin 15 B12UC  
**Scope:** installation integrity, executable version, capability declaration and host GPU snapshot.  
**Not covered:** model startup, inference, streaming, throughput or TensorFold VRAM consumption.

## Installation

- Release archive: `tensorfold-1.2.3-linux-x86_64.tar.gz` (45.76 MB).
- SHA-256 sidecar: `tensorfold-1.2.3-linux-x86_64.tar.gz.sha256`.
- Verification: `sha256sum -c tensorfold-1.2.3-linux-x86_64.tar.gz.sha256` → `OK`.
- Installed side-by-side at `~/.local/opt/tensorfold-1.2.3-linux-x86_64`.
- The older 1.1.x and 1.2.0 directories were not removed or overwritten.
- `bin/tensorfold-native --version` → `tensorfold-native 1.2.3`.

## Capability declaration

The captured `capabilities --json` returned:

| Field | Value |
|---|---|
| schema | 1 |
| engine | zig |
| version | 1.2.3 |
| chip | `nvidia-sm86` |
| backends | `cuda` |

Declared model families include:

| Family | Formats declared by this binary |
|---|---|
| `qwen3_5` | `mlx-q4g64`, `exl3` |
| `qwen3_5_moe` | `mlx-q4g64`, `modelopt-mixed`, `modelopt-nvfp4` |
| `qwen4` | `bf16`, `mlx-q4g32/q4g64/q4g128`, `mlx-q8g32/q8g64/q8g128`, `modelopt-fp8`, `modelopt-nvfp4` |
| `qwen4_text` | Same declared formats as `qwen4` |
| `gemma4`, `gemma4_unified` | MLX q2/q3/q4/q5/q6/q8 g64 |
| `spark2_5` | MLX q2/q3/q4/q5/q6/q8 g64 |
| `nemotron_h`, `nemotron_h_omni` | `mlx-q4g64`, `modelopt-nvfp4`, `modelopt-ggml` |
| `glm5_next` | `modelopt-nvfp4`, `modelopt-mixed`, `exl3` |
| `minimax_m3_vl` | `exl3` |
| `kolibri1` | `fp8-block` |
| `dory` | `modelopt-nvfp4` |
| `lfm2_vl` | `bf16` |
| `fish_omni` | `fp8-block128` |

A capability declaration is not proof that a specific checkpoint loads or fits the reference GPU.

## Optional runtime libraries

- Found: CUDA 13 `libcublas.so.13`, `libcublasLt.so.13`, `libibverbs.so.1`, `libtfgrammar.so`.
- Not found: ROCm libraries, NCCL, TensorFold video library, PDFium, libwebp, RCCL and MCDMA helpers.
- `libturbojpeg.so.0` was found but reported unusable for the optional vision path.
- These optional vision/video/distributed components are outside the first text-only integration scope.

## GPU snapshot at verification time

| Item | Captured value |
|---|---|
| GPU | NVIDIA GeForce RTX 3050 Laptop |
| Architecture | sm86 |
| VRAM | 4096 MiB total |
| Used VRAM | 2714 MiB |
| Free VRAM | 1382 MiB |
| Driver | 580.178.04 |
| CUDA shown by driver | 13.0 |
| Temperature | 42 °C |
| Existing process | pre-existing `llama-server` using 2685 MiB |

The existing `llama-server` was not stopped, modified or signalled. No TensorFold server or model was started. The remaining 1382 MiB free was below the PoC's new default 3072 MiB safety floor, so a model-load attempt would be refused before spawning TensorFold. This guard is a conservative preflight, not a guarantee that a checkpoint fits.

## Executable discovery

At capture time:

- `command -v tensorfold-native` returned no path.
- `~/.local/bin/tensorfold-native` did not exist.
- The verified executable is addressed by its absolute path:
  `~/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native`.

The PoC default was updated to this exact path. The eventual Atomic Core settings should support an explicit executable path and must not assume a global PATH alias exists.

## Result

**PASS** Archive integrity, side-by-side extraction, version and capability discovery passed.

**NOT RUN** Model loading, `/health`, `/v1/models`, chat, SSE, latency, tokens/s and TensorFold VRAM usage remain untested on this host.

## References

- [TensorFold README and Linux CUDA quick start](https://github.com/ashhart/TensorFold/blob/main/README.md)
- [TensorFold compatible API](https://github.com/ashhart/TensorFold/blob/main/docs/api.md)
- [LEONES integration PR #139](https://github.com/robertosantosx2/LEONES/pull/139)
