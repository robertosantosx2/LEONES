# Atomic Chat / TensorFold: upstream architecture reconciliation

**Date:** 2026-11-05  
**Repositories inspected:** `AtomicBot-ai/atomic-chat-core` and `AtomicBot-ai/Atomic-Chat`, default branch `main`.

This note supersedes any earlier blueprint assumption that TensorFold should be implemented as a managed container engine. The current upstream tree has since evolved and must be treated as the source of truth before implementation.

## Findings from the current Atomic Core tree

The current Core already distinguishes two relevant runtime families:

1. **Native host-process runtimes** — `litert-lm`, `foundry-local`, and `geniex`. These implement `LocalRuntime`, supervise a host process with the shared sidecar/process helpers, and expose a gateway/session contract. LiteRT-LM is the closest architectural starting point for a TensorFold native executable.
2. **Managed container engines** — `tensorrt-llm`, `vllm`, and `sglang`. These use `ManagedEngineSpec` and the shared managed-text lifecycle, with Docker/container-specific installation, descriptors, checkpoint compatibility checks, and GPU residency rules.

TensorFold Native is a host executable, so it must **not** be registered as a managed container engine merely because it serves an OpenAI-compatible HTTP API. In particular, do not add `tensorfold` to `MANAGED_PROVIDER_IDS` or route it through the Docker lifecycle.

Relevant existing contracts and implementation references:

- `src/contracts/session.ts`: `LocalProviderId`, `SessionInfo`, and `SessionExecutionKind`. A host process should remain a native session (not `execution: 'container'`).
- `src/runtime/shared/local-runtime.ts`, `sidecar.ts`, `process.ts`, `ports.ts`: shared local-runtime, process-supervision, sidecar, and loopback-port primitives.
- `src/runtime/litert-lm/runtime.ts`: native process lifecycle, per-model sidecar tracking, gateway and GPU-claim integration.
- `src/runtime/litert-lm/model-yml.ts`: strict provider-specific model metadata parsing; useful precedent for a non-GGUF checkpoint format.
- `src/runtime/index.ts` and `src/core/create.ts`: runtime exports and composition/wiring.
- `src/contracts/model-yml.ts`, `src/contracts/settings.ts`, `src/settings/schema.ts`, and `src/settings/schema/litert-lm.json`: provider contracts and settings schema.
- `src/config/paths.ts`: provider-specific model/runtime data paths.

## Findings from the current Atomic Chat app tree

The desktop app uses provider extensions, including:

- `extensions/litert-lm-extension/`
- `extensions/foundry-local-extension/`
- `extensions/llamacpp-upstream-extension/`
- shared Core runtime and settings synchronization in `extensions/shared/`.

The likely app-side integration shape is a dedicated `tensorfold-extension` following the current LiteRT-LM extension conventions, plus the required provider registration, model Hub/install handling, settings synchronization, core-version compatibility, and UI/event relay. This is a target to verify against the complete extension source before coding, not a claim that those files already exist.

## Revised implementation direction

- Implement TensorFold as a **native Linux x86_64 + NVIDIA CUDA provider** first.
- Reuse Core's native process, sidecar, port, cancellation, and gateway primitives where their contracts fit; do not duplicate process supervision or introduce Docker.
- Keep TensorFold's engine listener bound to loopback and expose only the authenticated Core gateway.
- Initially allow only the routes the tested TensorFold server actually supports (expected minimum: `GET /v1/models` and `POST /v1/chat/completions`); prove SSE behavior before advertising streaming.
- Define a dedicated typed TensorFold model metadata block. Do not classify native TensorFold checkpoints as GGUF or pass them through GGUF-specific loaders/validators.
- Keep model download/install ownership explicit. Do not assume the Core can download a TensorFold checkpoint until the app/Core model-store contract is implemented.
- Make platform/backend eligibility explicit. Do not advertise macOS, Windows, AMD, CPU, or multi-GPU support in this first scope.
- Preserve the no-interference rule: never terminate an unrelated process or existing inference server to make room for TensorFold.

## Required source inspection before implementation

Before opening the Core implementation PR, inspect the complete current versions of the LiteRT-LM runtime, its host-process and host server modules, Core runtime composition, settings schema registration, model registry/install path, and app extension registration. The initial file map in the blueprint is a guide, not a patch plan; reconcile every proposed change against current `main`.

## Validation gates remain unchanged

No upstream implementation should be described as working until all of the following are demonstrated:

1. A real TensorFold Native checkpoint loads on the target machine.
2. Core owns the process lifecycle and can cancel/unload it without touching unrelated processes.
3. The private engine listener is loopback-only and the Core gateway authenticates requests.
4. `/v1/models`, non-streaming chat, and SSE chat are tested end to end.
5. Model format/revision, context, VRAM, load time, prompt throughput, and decode throughput are recorded.
6. Unit tests and the upstream Core/app CI pass.

**Status:** architecture reconciliation only. No Atomic Core or Atomic Chat upstream files have been changed by this note; no live TensorFold inference has been proven.
