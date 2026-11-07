# Atomic Chat desktop app: TensorFold integration surface map

**Date:** 2026-11-05  
**Status:** research only; no changes made to `AtomicBot-ai/Atomic-Chat`.  
**Inspected:** Atomic Chat app default branch and its `AGENTS.md`.

## 1. App architecture relevant to a new engine

The app repository describes a Tauri + React desktop application. Its web frontend lives in `web-app/`; the shared inference core and browser contracts are in `core/`; backend extensions live in `extensions/`; Rust/Tauri IPC and event relays live in `src-tauri/`.

The app's contribution rules require repository changes to be in English, non-trivial architecture decisions to have an ADR under `docs/decisions/`, and `make verify` before a change is considered complete. The app also explicitly preserves the OpenAI-compatible public API at `http://localhost:1337/v1`.

The current app tree already contains provider-specific frontend modules for LiteRT-LM and Foundry Local. Their structure is a useful UI/service reference, but TensorFold must not be copied mechanically: TensorFold's model file format, platform support and feature surface differ.

## 2. Confirmed app-side patterns

The existing LiteRT-LM implementation separates concerns across:

- `web-app/src/services/litert-lm/`: core control API calls, model installation, types and download flow.
- `web-app/src/lib/litert-lm/`: Model Hub cards, model matching and default variant selection.
- `web-app/src/lib/engine-settings-defaults.ts`: provider settings copied from the core's schema.
- `web-app/src/services/litert-lm/types.ts`: wire types vendored from core contracts.
- `src-tauri/`: Rust/Tauri commands and event relay when the feature needs new IPC or event surfaces.

Foundry Local has a parallel structure. This establishes that a provider's UI, model catalog, install flow and core runtime are distinct deliverables.

## 3. Core version and schema synchronization

The root app `package.json` pins `atomicCore.version`. `src-tauri/build.rs` stamps that pin into the app binary as `ATOMIC_CORE_VERSION`, and the supervisor refuses to attach to a core with a mismatched version.

The app also vendors core provider setting schemas under `web-app/src/lib/core-settings-schema/`; `engine-settings-defaults.ts` reads those files for the Settings → Model providers reset-to-default behavior. A TensorFold provider therefore needs synchronized changes to:

1. the core's provider settings schema;
2. the vendored app schema copy;
3. the app's settings defaults map;
4. the pinned core version and download/build integration.

Do not update only one side: the running app and downloaded core must agree on the same version and settings contract.

## 4. TensorFold UI scope recommendation

For the first deliverable, do not add a Model Hub catalog or automatic model download before the checkpoint contract is proven. The safest first UI scope is:

- show TensorFold only on the supported platform/hardware combination;
- accept a local checkpoint path already present on disk;
- display the detected TensorFold version and parsed capabilities;
- expose only settings the runtime actually consumes (initially context and startup timeout, plus an optional executable path);
- show load/start errors without claiming unsupported features;
- keep model download/import out of the first release unless the existing app model-import contract can represent TensorFold's native checkpoint directory without loss.

Once a real checkpoint passes the core PoC, decide whether the app needs a dedicated Hub/catalog service and model-install flow. If so, model downloads remain an app responsibility, not a new downloader inside Atomic Core.

## 5. Event and IPC discipline

The core's `AGENTS.md` says a new event requires a contract type/catalog entry and a matching relay mapping in the app repository in the same pair of PRs. Prefer existing session lifecycle and core log events for the first runtime. Add new events only when the app cannot represent a TensorFold-specific state through existing contracts.

## 6. App-side acceptance checklist

- [ ] Provider appears only on the declared Linux x86_64 + NVIDIA CUDA scope.
- [ ] UI reads provider settings from the core contract and ships the matching vendored schema.
- [ ] App pins the core version containing TensorFold support.
- [ ] The runtime accepts only a validated local checkpoint for the first release.
- [ ] The app does not start, stop or reconfigure unrelated inference processes.
- [ ] Public API remains OpenAI-compatible and routes through Atomic's session gateway.
- [ ] Model Hub/download UI is added only after the checkpoint metadata and install contract are proven.
- [ ] UI tests, core tests, `make verify` and Linux/NVIDIA live acceptance pass.

## References

- [Atomic Chat repository](https://github.com/AtomicBot-ai/Atomic-Chat)
- [App agent instructions](https://github.com/AtomicBot-ai/Atomic-Chat/blob/main/AGENTS.md)
- [LiteRT-LM app install flow](https://github.com/AtomicBot-ai/Atomic-Chat/blob/main/web-app/src/services/litert-lm/install.ts)
- [LiteRT-LM Model Hub integration](https://github.com/AtomicBot-ai/Atomic-Chat/blob/main/web-app/src/lib/litert-lm/hub.ts)
- [Engine settings defaults](https://github.com/AtomicBot-ai/Atomic-Chat/blob/main/web-app/src/lib/engine-settings-defaults.ts)
- [Core version pin](https://github.com/AtomicBot-ai/Atomic-Chat/blob/main/src-tauri/build.rs)
- [Core integration contract map](atomic-chat-tensorfold-core-contracts-2026-11.md)
