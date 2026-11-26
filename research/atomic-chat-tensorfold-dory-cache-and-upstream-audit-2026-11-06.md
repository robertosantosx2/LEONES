# TensorFold checkpoint follow-up: Dory cache refusal and upstream HEAD audit

Date: 2026-11-06

## User-side Dory inspection result

The user ran:

```sh
tensorfold-native info nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4
```

TensorFold 1.2.3 returned:

```text
nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4 is not in the Hugging Face cache; run: tensorfold pull nvidia/NVIDIA-Nemotron-Labs-Dory1.0-4B-NVFP4
```

This is a cache miss, not a malformed installation or an inference failure. `info` does not download the checkpoint. We deliberately do **not** run `tensorfold pull`: the published Dory checkpoint is about 3.2 GB on disk, and the estimated weights-plus-runtime floor (~4.98 GiB) already exceeds this machine's 4 GiB VRAM. Downloading it would not produce a viable laptop test.

## Refreshed host preflight

The same user's 2026-11-06 10:41:59 snapshot records:

- TensorFold Native 1.2.3.
- RTX 3050 Laptop GPU, SM 8.6, 4096 MiB total.
- 28 MiB in use, 3741 MiB free.
- 8.9 GiB RAM available.
- GPU processes: Xorg (4 MiB) and Magnitude inference (1 MiB).

The 3072 MiB free-VRAM safety threshold is passed at that moment. This is only an instantaneous preflight; it does not imply any model fits. No server was started and no unrelated process was stopped or signalled.

## Upstream HEAD review

The public TensorFold `main` README and unreleased changelog were reviewed after the v1.2.3 release. They do not establish a newly qualified small general-chat checkpoint for a 4 GiB discrete RTX 3050. The published native CUDA matrix still warns that a family registry entry does not qualify every checkpoint, format, GPU or rank count; the supported hardware receipts for several small-looking entries are GB10-only. The README's Qwen3.5-2B example is qualified on a Mac and GB10, not on this RTX 3050. The changelog's newer work includes CUDA optimizations and additional family paths, but no evidence that a 4 GiB laptop checkpoint now meets the exact model+format+memory gates.

Consequently, do not infer that a newer upstream commit makes the locally installed 1.2.3 binary newer or changes its support. Do not install a development build or swap binaries as part of this research pass.

## Atomic Core implementation preparation

The current Atomic Core `LocalRuntime` interface and `SidecarTable` contracts were rechecked against `main`. The implementation blueprint remains aligned with the real contracts:

- Implement a provider runtime behind `LocalRuntime`; use `SidecarTable` for single-load queueing, journaling, cancellation, process exit tracking and termination.
- Keep TensorFold bound to loopback on a private engine port.
- Expose only an Atomic Core managed gateway with a fresh per-session bearer key.
- Initially allow only `GET /v1/models` and `POST /v1/chat/completions`; do not imply tools, structured output, embeddings, vision or other routes.
- Acquire and report GPU occupancy before spawning; retain the claim until owned child exit is confirmed.
- Use exact executable path, argument array (never shell), explicit `--backend cuda`, one parallel slot and a bounded context.
- Readiness must use `GET /health`, not a guessed stdout marker.
- Add tests for capability/model validation, argv, cancellation, early process exit, failed termination, gateway failure, route refusal and occupancy lifetime.

This is implementation preparation only. We still defer upstream Core/app code changes until a real, memory-qualified TensorFold checkpoint passes chat and SSE on the reference GPU. A provider with no working model would be misleading.

## Decision / next action

No further Ubuntu action is required now. Keep TensorFold 1.2.3 installed; do not pull Dory and do not stop or alter unrelated GPU processes. Continue searching upstream for a smaller checkpoint with a documented native CUDA chat path and exact admission evidence. If none emerges, the next real-inference gate requires a larger-VRAM CUDA machine or a later release/checkpoint with a proven smaller footprint.

## Sources

- TensorFold upstream README: https://github.com/ashhart/TensorFold/blob/main/README.md
- TensorFold upstream unreleased changelog: https://github.com/ashhart/TensorFold/blob/main/CHANGELOG.md
- TensorFold native CUDA implementation notes: https://github.com/ashhart/TensorFold/blob/v1.2.3/docs/recipes/cuda.md
- Dory CUDA loader restriction: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/families/dory/cuda_weights.zig
- Atomic Core LocalRuntime: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/local-runtime.ts
- Atomic Core SidecarTable: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/sidecar.ts
- Atomic Core implementation blueprint in LEONES: https://github.com/robertosantosx2/LEONES/blob/research/atomic-chat-tensorfold-linux-cuda/research/atomic-chat-tensorfold-implementation-blueprint-2026-11.md
