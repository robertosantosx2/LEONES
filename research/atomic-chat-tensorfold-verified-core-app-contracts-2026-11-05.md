# Atomic Chat / TensorFold: verified Core and desktop extension contracts

**Date:** 2026-11-05  
**Target repositories:** `AtomicBot-ai/atomic-chat-core` and `AtomicBot-ai/Atomic-Chat`  
**Research branch:** `research/atomic-chat-tensorfold-linux-cuda`

This note records a source-level inspection of the current `main` branches after the initial architecture reconciliation. It is a research artifact, not an implementation patch.

## Source snapshots inspected

The following GitHub `main` file revisions were read directly:

| Repository | Path | Blob SHA |
|---|---|---|
| atomic-chat-core | `src/contracts/session.ts` | `ab7f88c9528ae0459b81f7a70d2f9163173bd7bf` |
| atomic-chat-core | `src/contracts/model-yml.ts` | `2f222cbf525b55c47493ef836d95e969fbb002c9` |
| atomic-chat-core | `src/contracts/settings.ts` | `1c5293d4415b5733ab4e3b200e29f0b9bcb5acce` |
| atomic-chat-core | `src/runtime/shared/local-runtime.ts` | `eff10b200addc422ac99c93edf707bfbe49f1a7c` |
| atomic-chat-core | `src/runtime/shared/sidecar.ts` | `e526bc22049c3dd8639143deb6171ad97a812ede` |
| atomic-chat-core | `src/runtime/litert-lm/runtime.ts` | `2b7e243d392d71bb87033b82033863262f0fd7b9` |
| atomic-chat-core | `src/runtime/litert-lm/model-yml.ts` | `5f6898e70c1a13b08016d3af0b6583822ee3d1c9` |
| atomic-chat-core | `src/runtime/litert-lm/host/server.ts` | `74c28310b10670378c80531caaf704b5ef34fab4` |
| atomic-chat-core | `src/settings/schema.ts` | `8767f869fa789637f7e5692d9f130dbec1ffd14f` |
| atomic-chat-core | `src/config/paths.ts` | `e0ca85dd1698eb510657d9231af8124f1f416b6f` |
| atomic-chat-core | `src/core/create.ts` | read from current main; imports and wires the native LiteRT-LM services |
| Atomic-Chat | `extensions/litert-lm-extension/package.json` | `4145d2401f83375a297475988ed42815c1a7a92d` |
| Atomic-Chat | `extensions/litert-lm-extension/settings.json` | `3ef48ed2df91ae7fcb39618a668528829f0c4856` |
| Atomic-Chat | `extensions/litert-lm-extension/src/index.ts` | `bee3a7a67a82b2d5cf8dc5dad674ac5cb1faff09` |
| Atomic-Chat | `extensions/shared/atomicCoreRuntime.ts` | `26f14cc948b7245065e7a99b8d3be8ea14aa68c5` |
| Atomic-Chat | `extensions/shared/atomicCoreSettingsSync.ts` | `433fce0c0e9350d41a34352292db2a467782c964` |
| Atomic-Chat | `extensions/shared/loadCancel.ts` | `64bd22d51093dff9cfe2cfe06bb06e63a5cd1edd` |

## Confirmed Core contracts

### Native provider registration

- `LocalProviderId` contains the native providers and then `ManagedProviderId`; `MANAGED_PROVIDER_IDS` is exactly `tensorrt-llm`, `vllm`, and `sglang`.
- TensorFold must be added as a native `LocalProviderId`, **not** to `MANAGED_PROVIDER_IDS`.
- Native sessions use `execution: 'native'` (or omit the field); a real host PID is tracked. Container sessions use `execution: 'container'` and do not claim a host PID.
- `LocalRuntime` requires `list`, `findSession`, `getLoadedModels`, `isLoading`, `load`, `unload`, `autoIncreaseCtx`, `recreateSession`, and `shutdown`. Optional hooks include `routePolicy` and `gpuOccupancy`.

### Shared process lifecycle

- `SidecarTable` already supplies serialized provider loads, joining duplicate loads, cancellation/shutdown handling, process journaling, exit watching, session events, stopping-session tracking and used-port reporting.
- `LocalLoadOptions` already carries cancellation signal, readiness timeout, executable override, log path, verbose mode, selected port and auto-unload bypass.
- The existing native LiteRT-LM runtime uses this sidecar table, `spawnAndAwaitReady`, `randomFreePort`, GPU claim hooks, and a managed gateway. This is the closest concrete runtime precedent for TensorFold.
- Reuse these facilities; do not introduce a second process supervisor, shell-based launch, Docker lifecycle, or a process-name based kill mechanism.

### Model metadata and settings

- The common `ModelYml` has provider-specific blocks for `foundry_local`, `litert_lm`, and `geniex`; LiteRT-LM demonstrates strict parsing and explicit source/revision/file metadata.
- TensorFold needs its own typed block and parser. Its model format must be explicit and must not be represented as GGUF merely to fit the existing default `model_path` field.
- A new settings provider requires all of the following to agree: the settings interface in `src/contracts/settings.ts`, an extension-owned `settings.json` descriptor array copied to Core's `src/settings/schema/<provider>.json`, imports and registration in `src/settings/schema.ts`, and a complete entry in `CANONICAL_VALUE_TYPES`.
- `dataLayout`/provider paths in `src/config/paths.ts` are shared contracts with the desktop app. The TensorFold model root must be designed together with the app installer and not invented independently.

### Gateway and HTTP behavior

- LiteRT-LM's host server listens on loopback, unauthenticated; Core's gateway is the only authenticated entry point and allows only `GET /v1/models` and `POST /v1/chat/completions`.
- Its route policy is explicit. TensorFold should publish only routes verified against the actual TensorFold Native server.
- The LiteRT-LM host server implements non-streaming and SSE chat, but that behavior is specific to LiteRT-LM; it is not evidence that TensorFold's server supports the same details.
- The app extension currently chats through the Core-returned session port and Bearer key. The TensorFold extension should follow the shared gateway/session contract and must never expose the private engine port directly to the UI.

## Confirmed desktop extension pattern

The current LiteRT-LM extension establishes these responsibilities:

1. It registers the provider's settings descriptors in `onLoad`.
2. It asks Core `POST /engines/versions` whether the provider is registered on this host; unsupported providers remain hidden.
3. It discovers installed variants under a provider-specific `models/` directory, each with a `model.yml` written by the installer.
4. It imports/mirrors settings through `createCoreSettingsSync` before the first load.
5. It loads/unloads and queries sessions through `createCoreRuntime`; `LoadCancelTracker` preserves cancellation semantics.
6. It streams chat through the session port and Bearer key.
7. It does not import arbitrary models; its comment and implementation say Model Hub owns downloads. Deletion unloads first and only then removes the model folder.

Consequently, an app-side TensorFold extension is not just a chat adapter. It also needs a real model catalogue/install path, provider visibility, settings registration/synchronization, cancellation, session handling, packaging and Core-version compatibility.

## Revised implementation map

### Core work (native provider)

- Add `tensorfold` to `LocalProviderId`, `LOCAL_PROVIDER_IDS`, settings schema registration, canonical setting types, provider config types and model-yml key order.
- Add a strict `tensorfold` model metadata parser with an explicit supported TensorFold family/format/revision contract.
- Add `src/runtime/tensorfold/` with argument planning, capability validation, host process readiness, sidecar lifecycle, gateway and route policy.
- Add provider paths in `src/config/paths.ts` and wire runtime construction, engine/version availability and shutdown in `src/core/create.ts`.
- Gate registration to Linux x86_64 + NVIDIA CUDA for v1. Fail closed when the executable/backend/capability contract is not met.
- Keep process startup loopback-only; route through Core's authenticated gateway; never terminate unrelated inference processes.

### Desktop app work

- Add `extensions/tensorfold-extension/` modeled on the current LiteRT-LM extension's provider boundary, not copied blindly.
- Add its settings descriptor file and package/build/test registration.
- Add TensorFold-specific model Hub variant metadata and installer/download ownership. The installer must write a complete `model.yml` only after verified download and integrity checks.
- Add extension registration and any app-side provider list, model Hub, settings, event relay, compatibility and packaging changes required by the current app tree.

## Remaining source-inspection gates before coding

The following must be inspected against the exact target commits before writing the implementation patch:

- Complete Core construction/wiring around the `LiteRtLmRuntime` instance, host command resolver, engine-build manifest and platform gate.
- Core's model registry lookup and provider path/data-layout construction.
- The app's extension discovery/registration, Model Hub catalogue and download/install pipeline, and core-version compatibility gate.
- The exact TensorFold 1.2.3 `serve` command, model metadata/capability schema, loopback behavior, health/readiness signal and OpenAI/SSE semantics.
- The target TensorFold checkpoint's real load on supported hardware. No successful live TensorFold inference has yet been demonstrated on the user's RTX 3050; current VRAM is constrained by an unrelated running `llama-server`, which must not be stopped to make room.

## Status and implementation decision

**Status: source-level contract inspection, not implementation.** No files in Atomic Core or Atomic Chat have been changed. The research branch is the only place this note is being added.

Do not open an upstream implementation PR until the remaining source-inspection gates are complete and a real TensorFold checkpoint can be loaded and queried end to end. The next safe step is to finish inspecting the Core construction/model-store and app Model Hub/extension registration paths, then write a small, testable Core-native runtime patch before the desktop extension.
