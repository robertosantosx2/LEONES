# TensorFold upstream and CUDA checkpoint audit — 2026-11-06

**Scope:** public upstream state after TensorFold Native 1.2.3, with the Atomic Chat PoC target being Linux x86_64 + NVIDIA RTX 3050 Laptop (sm_86, 4 GiB VRAM). Documentation-only audit; no host installation, download, launch or modification.

## Executive result

No newly documented native TensorFold checkpoint currently qualifies as a safe general-text-chat smoke test for the reference RTX 3050.

The latest public engine release remains **1.2.3**. The upstream native CUDA registry is broad, but upstream explicitly distinguishes a family registry/build target from a checkpoint-, format-, rank- and GPU-qualified serving receipt. The release's sm_86 fatbin means kernels are present for the architecture; it does not establish that a small checkpoint has a complete native CUDA serving path on this particular card.

The Atomic Chat PoC must remain research-only and refuse model startup until a real checkpoint passes tensorfold-native info, free-VRAM admission, native CUDA serve, /health, /v1/models, non-streaming chat and SSE on the reference host.

## Upstream state

- The release page lists **TensorFold 1.2.3** as Latest (released 2026-11-05). No later tagged engine release is listed at this audit.
- The current upstream recipe index states that native CUDA release images include sm_80, sm_86, sm_120 and sm_121, but calls this a build-target list rather than per-card model qualification.
- The native CUDA runbook states that a registry entry does not qualify every checkpoint, format, GPU or rank count.
- The current README lists Qwen3.5-2B as a native Metal and CUDA model, with CUDA release checks and a documented machine scope of one GB10. The recipe page itself is titled a native Metal preview, so it is not the full CUDA runbook. The changelog records native CUDA serving for Qwen3.5-2B (#836) and says the 2B geometry admits only `mlx-q4g64` (#2139). No RTX 3050/sm_86 serving receipt is listed for this checkpoint.

Sources:
- https://github.com/ashhart/TensorFold/releases
- https://github.com/ashhart/TensorFold/blob/main/README.md
- https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/README.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/cuda.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/qwen3.5-2b-native.md

## Candidate disposition

| Candidate / path | Upstream evidence | Decision for 4 GiB RTX 3050 |
|---|---|---|
| Qwen3.5-2B MLX 4-bit | Native CUDA serving exists (#836); current README's documented CUDA machine scope is one GB10. Geometry admits only `mlx-q4g64` (#2139). No RTX 3050/sm_86 receipt is documented. | **Not yet qualified** — legitimate CUDA-path candidate, but not a verified RTX 3050 model. Exact local `info` floor is still unknown. |
| Qwen3.5-4B MLX 4-bit | Reference host ran tensorfold-native info mlx-community/Qwen3.5-4B-MLX-4bit: weights 2.85 GiB; reported memory floor 4.85 GiB. | **Reject** — reported floor exceeds the card's entire 4 GiB VRAM. |
| Nemotron 3.5 Lightning 30B-A3B MLX 4-bit | Native CUDA receipts include GB10, RTX 3090 (sm_86) and RTX PRO 6000. | **Reject** — model class/checkpoint is far beyond this laptop's VRAM budget; RTX 3090 receipt is not a 4 GiB qualification. |
| Spark-X2.6-4B | Native CUDA recipe exists, but public CUDA measurement cited in the earlier candidate audit reports 9.47 GiB for its 8-bit checkpoint on RTX 5090. | **Reject** — published configuration is already much larger than 4 GiB; no 4 GiB-compatible native checkpoint/receipt found. |
| LFM3-1.7B | 1.2.3 release note records LFM3-1.7B on Intel Iris Xe; this is not an NVIDIA CUDA text-chat qualification. Existing family notes describe metadata/layout bring-up, not a completed general chat serving engine. | **Reject** — no native CUDA general-chat serving receipt. |
| Liquid AI d1-3B | Native CUDA path is a decision API (/v1/systemone, /v1/decisions), not a general chat-completions engine. | **Reject** — wrong API semantics for Atomic Chat's first general-chat provider. |
| Dory 1.0 4B NVFP4 | Native CUDA family exists, but the 4B checkpoint's ~3.2 GB weights plus TensorFold's documented 2 GiB runtime margin imply a rough floor near 5 GiB; estimate only, not a local info measurement. | **Reject pending measured info and qualified serving receipt** — estimated floor already exceeds physical VRAM. |
| Kolibri-1 | Native CUDA recipe describes a 74 GB checkpoint. | **Reject** — far beyond the hardware budget. |
| GLM-5.3-Flash / Qwen3.8 dense / Qwen3.6 MoE / Flash Next / larger Nemotron | Native CUDA support exists for specific checkpoints, formats and hardware configurations; published receipts are for substantially larger multi-GB/GB10-class systems. | **Reject** — no checkpoint or receipt near the laptop's memory envelope. |

A model's parameter count, quantization label, family capability entry, or presence of sm_86 kernels is not enough to establish that serve will load and generate chat on this GPU.

## Host evidence retained

- NVIDIA RTX 3050 Laptop, sm_86, 4096 MiB VRAM.
- TensorFold Native 1.2.3 at ~/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native.
- CUDA 13.0 / driver 580.178.04.
- The Qwen3.5-4B info result reports 2.85 GiB weights and a 4.85 GiB floor.
- Prior GPU snapshot showed only 1382 MiB free while an unrelated existing llama-server used 2685 MiB. That process must not be stopped or signalled.

No local state was read during this audit, and no host process was started.

## Consequences for Atomic Chat work

1. Keep PR #139 a draft. Do not remove the live-inference acceptance gate.
2. Keep the PoC's default 3072 MiB free-VRAM safety floor and per-checkpoint info check. Neither guarantees successful model load; native CUDA serve remains authoritative.
3. Do not implement or merge a production provider assuming Qwen3.5-2B is qualified on RTX 3050: its native CUDA path is real, but the published checkpoint scope is GB10 and no sm_86 laptop receipt is documented.
4. The next valid hardware milestone is either a later upstream native CUDA checkpoint with an exact documented sm_86 serving receipt and measured floor that fits currently free VRAM, or a test on a larger NVIDIA GPU with enough free VRAM for an already-qualified native checkpoint.
5. Once a real model passes, continue with API compatibility, Core managed-gateway authentication/key stripping, lifecycle/cancellation, and only then app extension/UI work.

## Exact point where Ubuntu assistance is required

The independent public-source audit is exhausted for the current 4 GiB reference target. The remaining decisive evidence is local and cannot be inferred from GitHub:
- a fresh nvidia-smi and free -h snapshot, without changing any process;
- tensorfold-native info for any genuinely new candidate;
- a real native CUDA serve attempt only after the memory preflight passes;
- /health, /v1/models, one JSON chat request and one SSE request against that owned process.

Until a candidate is identified and the safe memory preflight passes, do not ask the user to download weights or launch a model. Keep the existing llama-server untouched.

## Pull request

https://github.com/robertosantosx2/LEONES/pull/139


## Qwen3.5-2B CUDA qualification clarification (2026-11-06)

The current upstream `main` documentation was re-read to correct the earlier shorthand that Qwen3.5-2B was Metal-only. It is **not** Metal-only:

- README model table: Qwen3.5-2B MLX 4-bit, one Mac (M5 Max checked) or one GB10; “CUDA release checks”.
- Changelog: Qwen3.5-2B and Qwen3.8-27B serve on CUDA through the native server (#836).
- Changelog: Qwen3.5-2B's exact geometry admits only `mlx-q4g64` (#2139).
- README's documented CUDA machine for this small checkpoint is GB10. No RTX 3050 / sm_86 serving receipt is recorded.

The correct disposition is therefore: **native CUDA path exists; RTX 3050 qualification is unproven**. Its public HF checkpoint is about 1.72 GB, which makes it worth retaining as the first candidate for a careful local `tensorfold info` check if a deliberate download is later authorized. Do not pull or serve it automatically: TensorFold's reported memory floor, the instantaneous free VRAM and a model-specific sm_86 serving gate must all be checked first. With only 4 GiB total VRAM, this may still be too close to the memory boundary.

Sources:
- https://github.com/ashhart/TensorFold/blob/main/README.md#qualified-models
- https://github.com/ashhart/TensorFold/blob/main/CHANGELOG.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/qwen3.5-2b-native.md
- https://huggingface.co/mlx-community/Qwen3.5-2B-MLX-4bit
