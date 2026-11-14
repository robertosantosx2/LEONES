# TensorFold Native 1.2.3: refreshed RTX 3050 preflight

Date: 2026-11-06 10:42 Europe/Madrid  
Host: MSI Thin 15 B12UC, Ubuntu, RTX 3050 Laptop GPU (SM 8.6, 4 GiB)

## Observed local state

The user ran a read-only diagnostic block. The output reported:

- TensorFold Native: `1.2.3`.
- NVIDIA driver: `580.178.04`; CUDA driver compatibility: `13.0`.
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, compute capability 8.6.
- VRAM: 28 MiB used / 4096 MiB total; 3741 MiB free.
- GPU processes shown: Xorg (4 MiB) and Magnitude inference (1 MiB).
- RAM: 14 GiB total, 8.9 GiB available.
- No TensorFold process was started by this diagnostic. No existing process was stopped or signalled.

The PoC's 3072 MiB free-VRAM threshold is therefore passed at this instant, with 669 MiB above that threshold. This is a **preflight snapshot only**. It does not establish that a model's weights, KV/cache allocations, kernels or runtime will fit, nor does it qualify a checkpoint.

## Re-evaluation of native CUDA candidates

The v1.2.3 native CUDA recipe index confirms these relevant distinctions:

- `XHToken/Spark-X2.6-4B` is a genuine native CUDA text-generation recipe, but its documented 8-bit model footprint is 9.47 GiB on an RTX 5090. The 4-bit conversion is explicitly a lower-fidelity conversion and has no small-GPU qualification. It is not a safe candidate for a 4 GiB card.
- Dory is a genuine native CUDA family, and the official `nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4` checkpoint is a 4B NVFP4 model. However, its published checkpoint file is approximately 3.2 GB (about 2.98 GiB). Adding TensorFold's documented 2.00 GiB runtime margin gives a rough floor of about 4.98 GiB, before considering any additional runtime/KV needs. This is above both the card's 4 GiB physical capacity and the current 3741 MiB free snapshot. Do not attempt to load it on this host.
- Dory's native CUDA loader explicitly admits ModelOpt W4A16 NVFP4 and rejects BF16/MXFP8 maps. Its family registry entry is not universal checkpoint support.
- Qwen3.5-2B MLX 4-bit has a native CUDA path in current upstream, and LEONES records successful TensorFold 1.1.1 inference on this exact RTX 3050 (context 1024; 95.08–105.71 tok/s). The currently installed 1.2.3 binary has not been live-tested with it.
- Qwen3.5-4B MLX 4-bit is not disqualified as a model for this GPU: LEONES records successful TensorFold 1.1.1 inference (context 512; 53.42–53.64 tok/s) and a successful experimental PR #1879 build (three requests, 54.32–56.05 tok/s). The 1.2.3 info floor of 4.85 GiB is weights plus a generic 2 GiB margin, not a measured peak; a later baseline did OOM while the PR #1879 build succeeded.
- LFM3 1.7B remains metadata/layout bring-up only and does not register a serving engine.
- Kolibri-1's documented tested checkpoint is 74 GB.

## Decision

No current TensorFold 1.2.3 binary/checkpoint receipt has yet been captured on this Ubuntu RTX 3050. This does not mean there is no historical working model: Qwen3.5-2B and Qwen3.5-4B have already completed real inference here with earlier TensorFold builds, and the experimental PR #1879 build overcame a matched baseline CUDA OOM. The current installed 1.2.3 binary still needs its own live receipt. The earlier candidate statement was therefore too broad.

1. An explicitly documented native CUDA text-generation path in TensorFold 1.2.3.
2. A checkpoint format and architecture explicitly admitted by that path.
3. A checkpoint memory floor that fits the 4 GiB GPU and the current available VRAM with the PoC's safety margin.

The current host is idle enough to run a properly qualified smoke test if a smaller candidate is found, but the current candidate list does not provide one. Do not spend the available headroom by attempting Dory, Spark-X2.6, Kolibri-1 or the Qwen3.5-4B checkpoint.

## Next gate

Do not search for a new model before reusing the existing Qwen3.5-4B receipt. The next meaningful test is the exact cached revision 32f3e8ecf65426fc3306969496342d504bfa13f3, context 512, parallel 1, using the user's current rebased PR #1879 build once its host/CUDA tests and review fixes are ready. Treat the 4.85 GiB info floor as advisory; keep the 3072 MiB free-VRAM guard mandatory. Prove /health, /v1/models, JSON chat and SSE on loopback, then exercise the Atomic Core gateway. Do not stop or signal unrelated GPU processes.

## Source references

- TensorFold v1.2.3 release: https://github.com/ashhart/TensorFold/releases/tag/v1.2.3
- Native CUDA recipe index and explicit registry caveats: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/cuda.md
- Spark-X2.6-4B native CUDA recipe and measured 9.47 GiB 8-bit footprint: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/spark-x2.6-4b-cuda.md
- Qwen3.5-2B native Metal-only recipe: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/qwen3.5-2b-native.md
- LFM3 metadata-only native bring-up: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/lfm3-native.md
- Kolibri-1 native CUDA recipe and 74 GB checkpoint: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/kolibri-1.md
- Dory CUDA loader's ModelOpt NVFP4 restriction: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/families/dory/cuda_weights.zig
- Dory CUDA family implementation: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/families/dory/cuda_native.zig
- Official Dory 1.0 4B NVFP4 checkpoint: https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4


## Correction using historical LEONES receipts (2026-11-06)

The candidate review above originally overlooked prior measured TensorFold CUDA runs on this exact RTX 3050. See [historical RTX 3050 inference evidence](atomic-chat-tensorfold-historical-rtx3050-evidence-2026-11-06.md).

- TensorFold 1.1.1 + Qwen3.5-2B: 95.08–105.71 tok/s, context 1024.
- TensorFold 1.1.1 + Qwen3.5-4B: 53.42–53.64 tok/s, context 512.
- Experimental PR #1879 build + Qwen3.5-4B: three HTTP 200 requests, 54.32–56.05 tok/s, TTFT 187.2–194.1 ms; matched baseline failed with CUDA OOM.

The current 1.2.3 binary is still not live-qualified. The generic 4.85 GiB info floor is not an observed peak and must not be used to invalidate those earlier runs. The next test should use the known Qwen3.5-4B checkpoint and the current rebased lazy-scratch build, not download a new candidate.
