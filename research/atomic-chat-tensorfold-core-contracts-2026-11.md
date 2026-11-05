# Atomic Chat Core: TensorFold integration contract map

**Date:** 2026-11-05  
**Status:** LEONES research artifact; no upstream source changes have been made.  
**Core inspected:** `AtomicBot-ai/atomic-chat-core`, default branch `main`, current source snapshot at inspection time.  
**Target:** a native local runtime for Linux x86_64 + NVIDIA CUDA, initially text chat only.

## 1. Confirmed extension points in Atomic Core

The current core already has a native-runtime contract. TensorFold should implement that contract rather than be represented as a managed container engine or as a user-configured remote OpenAI provider.

| Concern | Existing core contract | TensorFold work |
|---|---|---|
| Provider identity | `src/contracts/session.ts`: `LocalProviderId` | Add `tensorfold` to the union and its provider docs |
| Provider enumeration | `src/settings/schema.ts`: `LOCAL_PROVIDER_IDS` | Register it so settings migration/defaults include it |
| Settings | Embedded JSON schemas in `src/settings/schema/*.json`; canonical value types in `schema.ts` | Add a small schema for executable path, context, timeout and conservative serving options |
| Runtime lifecycle | `src/runtime/shared/local-runtime.ts`: `LocalRuntime` | Implement list/find/load/unload/cancel/shutdown/context behavior |
| Process supervision | `src/runtime/shared/process.ts`: `spawnManaged` / `spawnAndAwaitReady` | Use argv (never a shell), health readiness, captured diagnostics and owned-child termination |
| Session table | `src/runtime/shared/sidecar.ts`: `SidecarTable` | Reuse for per-model sessions and safe lifecycle coordination |
| Session API gateway | `src/runtime/managed-text/gateway.ts` | Bind an authenticated gateway on loopback; only expose declared model/chat routes; preserve SSE |
| GPU arbitration | `src/runtime/shared/gpu-occupancy.ts`, `src/core/gpu-residency.ts` | Claim the CUDA device before model startup and report occupancy until confirmed shutdown |
| Core wiring | `src/core/create.ts` | Instantiate runtime, register its model registry and add it to the runtime map |
| Settings API | `src/server/control/routes/settings.ts` consumes `LOCAL_PROVIDER_IDS` | No separate settings route should be invented |
| Module exports | `src/runtime/index.ts` and provider-local `index.ts` | Export the provider through the established module entry |

The inspected `LocalRuntime` contract requires `list`, `findSession`, `getLoadedModels`, `isLoading`, `load`, `unload`, `autoIncreaseCtx`, `recreateSession` and `shutdown`. It optionally exposes `routePolicy` and `gpuOccupancy`. `LocalLoadOptions` already carries executable override, timeout, log path, verbose mode, port, cancellation signal and auto-unload control.

## 2. Native runtime pattern

The closest implementation references are:

- `src/runtime/litert-lm/runtime.ts`
- `src/runtime/foundry-local/runtime.ts`
- `src/runtime/geniex/runtime.ts`
- `src/runtime/shared/process.ts`
- `src/runtime/shared/sidecar.ts`
- `src/runtime/managed-text/gateway.ts`
- `src/core/create.ts`

The native adapters supervise one host process per model. They start the process on a random loopback port, wait for actual readiness, create a session gateway with a fresh API key, and publish the gateway port/key in `SessionInfo`. The engine's raw port is not handed to the caller.

The gateway already supports declared method/path routes, rejects undeclared routes, forwards successful responses without buffering, and relays event streams. TensorFold's initial route policy should be deliberately narrow:

- `GET /v1/models`
- `POST /v1/chat/completions`

Do not advertise embeddings, completions, tools, JSON schema, vision, audio or other endpoints until each has a verified compatibility contract and tests.

## 3. GPU and process ownership requirements

The core's GPU residency policy is global across GPU-capable local runtimes. A TensorFold load must request a GPU claim before starting the server, and the runtime must report a `GpuOccupancy` entry while loading, ready, stopping or not yet confirmed stopped. A failed stop must keep the GPU reserved; it must never kill an unrelated process to make room.

The TensorFold process must be launched with an argument array and an explicit environment. It must bind only to `127.0.0.1`, use a dynamically allocated port, and be terminated only through the process handle owned by that runtime. User cancellation, core shutdown, startup timeout, early exit and failed termination need separate tests.

## 4. Model contract: still to resolve before implementation

The core's current model registry and `model.yml` are shared across providers, but TensorFold consumes native checkpoint directories and format/family combinations rather than assuming GGUF. Before code is written, settle:

1. How a TensorFold checkpoint is represented in the existing registry without falsely treating it as GGUF.
2. Which exact model metadata fields identify TensorFold family, quantization and checkpoint root.
3. Whether the first release accepts only an already-downloaded local checkpoint.
4. How the runtime reads the checkpoint's actual config and checks it against `capabilities --json`.
5. Whether TensorFold CLI accepts a local path and what exact command-line syntax/version floor applies.

The first release should not add model downloading. The core's current contract explicitly keeps model downloads out of the core; the app or another existing client flow owns model files. Do not create a second downloader or duplicate Hugging Face cache.

## 5. Version 1.2.3 reference-machine evidence

The Ubuntu reference machine installed TensorFold Native 1.2.3 side-by-side in:

`~/.local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native`

The archive SHA-256 check passed. `--version` returned `tensorfold-native 1.2.3`. `capabilities --json` reported backend `cuda`, chip `nvidia-sm86`, and detected `libcublas.so.13` plus `libcublasLt.so.13`.

The capability output declares families including `qwen3_5`, `qwen3_5_moe`, `qwen4`, `qwen4_text`, `gemma4`, `spark2_5`, `nemotron_h` and `glm5_next`. This is metadata from the binary, not a successful model-load result.

No TensorFold model was launched during this check. The RTX 3050 has 4 GiB VRAM and the captured `nvidia-smi` sample showed 2714 MiB already occupied, of which 2685 MiB belonged to the existing `llama-server`. That process was left untouched. Model inference, streaming, speed and TensorFold VRAM use remain unverified.

## 6. Implementation sequence and gates

1. Complete the standalone PoC against TensorFold 1.2.3 with an already-downloaded checkpoint, including health, model discovery, non-streaming chat, SSE and owned-child shutdown.
2. Resolve the model registry/metadata contract above.
3. Implement `src/runtime/tensorfold/` with pure argument/capability/model-validation helpers separated from process I/O.
4. Add provider identity, settings schema, registry and `create.ts` wiring.
5. Add unit tests for capability parsing, argument construction, platform/driver refusal, cancellation, readiness, route policy and stop ownership.
6. Add contract/e2e tests for public routing and GPU residency; keep the live TensorFold test opt-in.
7. Run the core's required verification and the live Linux/CUDA test before promoting the PR from draft.

## 7. Repository engineering constraints

The core's `AGENTS.md` requires one module folder with `index.ts` as its public entry, pure policy separated from I/O, injected environment/process seams, `node:*` built-ins only (no Bun-specific runtime APIs), explicit error codes and dedicated tests. New events require matching contract and app relay work; avoid introducing an event unless the existing session/load events are insufficient.

## References

- [Atomic Chat Core](https://github.com/AtomicBot-ai/atomic-chat-core)
- [Core agent instructions](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/AGENTS.md)
- [Local runtime contract](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/local-runtime.ts)
- [LiteRT-LM runtime](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/litert-lm/runtime.ts)
- [Session gateway](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/managed-text/gateway.ts)
- [TensorFold](https://github.com/ashhart/TensorFold)
- [LEONES integration research](https://github.com/robertosantosx2/LEONES/blob/research/atomic-chat-tensorfold-linux-cuda/research/atomic-chat-tensorfold-integration-2026-11.md)
