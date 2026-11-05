# Atomic Chat / TensorFold: Model Hub, extension packaging and install-path findings

**Date:** 2026-11-05  
**Scope:** current `main` source inspection of Atomic Chat's browser catalog/download pipeline and extension packaging, plus Atomic Core's provider data layout and engine-build lifecycle.

This is a continuation of the verified contract note. It narrows the app integration design and records the remaining implementation blockers. No Atomic Chat or Core source has been changed.

## Current source revisions inspected

| Repository | Path | Blob SHA |
|---|---|---|
| atomic-chat-core | `src/config/paths.ts` | `e0ca85dd1698eb510657d9231af8124f1f416b6f` |
| atomic-chat-core | `src/core/create.ts` | `335e05050406bd2dd557a83d1fe5b42112d80d17` |
| atomic-chat-core | `src/runtime/litert-lm/runtime.ts` | `2b7e243d392d71bb87033b82033863262f0fd7b9` |
| atomic-chat-core | `src/engine-builds/manifest.ts` | current main snapshot |
| atomic-chat-core | `src/engine-builds/litert-lm.ts` | current main snapshot |
| Atomic-Chat | `core/src/browser/catalogProtocol.ts` | `337aacf1b6a16c5be7b35b9baab6950d0f912e59` |
| Atomic-Chat | `core/src/browser/modelCatalog.ts` | `337aacf1b6a16c5be7b35b9baab6950d0f912e59` |
| Atomic-Chat | `core/src/browser/modelDownloads.ts` | `9f37a5074dff22139aca4f726357285159a3dfc1` |
| Atomic-Chat | `core/src/browser/extensions/engines/EngineManager.ts` | `34ef45afd100dbb77529890617778237774ea278` |
| Atomic-Chat | `extensions/foundry-local-extension/package.json` | current main snapshot |
| Atomic-Chat | `extensions/foundry-local-extension/settings.json` | current main snapshot |
| Atomic-Chat | `extensions/litert-lm-extension/package.json` | `4145d2401f83375a297475988ed42815c1a7a92d` |
| Atomic-Chat | `extensions/litert-lm-extension/src/index.ts` | `bee3a7a67a82b2d5cf8dc5dad674ac5cb1faff09` |

## Findings that change the implementation plan

### 1. Core provider paths are an explicit contract

`DataLayout.provider(id)` is an exhaustive switch for native providers. LiteRT-LM owns:

- `<data>/litert-lm/backends`
- `<data>/litert-lm/models`
- `<data>/litert-lm/accelerators`
- `<data>/litert-lm/cache`
- `<data>/litert-lm/runtime`
- `<data>/litert-lm/tmp`
- `<data>/litert-lm/logs`

TensorFold needs a deliberate path layout, not a guessed reuse of the GGUF `llamacpp/models` directory. The model store should hold a TensorFold-native checkpoint plus the provider's `model.yml`; the backend install directory should hold a pinned, verified TensorFold executable/build if Atomic Chat is to manage that binary. If v1 intentionally uses an externally installed executable, that must be a documented opt-in setting with an absolute path and an explicit missing-binary error; it must not silently search arbitrary PATH entries.

### 2. Core construction requires several synchronized registrations

The LiteRT-LM wiring in `src/core/create.ts` is not just `new Runtime()`. It includes:

- host platform detection and a host command resolver;
- provider path resolution;
- a model registry;
- an engine manifest source;
- accelerator/build lifecycle services;
- GPU residency claim hook;
- runtime registration in both `registries` and `runtimes`;
- an `EngineBuildsService` root, manifest, host platform, host probe and `EngineHost`;
- provider check/accelerator services;
- engine version reporting and shutdown.

For TensorFold, the minimal design should avoid inventing a separate installer if the upstream executable is externally managed. If Atomic Chat ships/updates TensorFold itself, add a proper immutable manifest with platform assets, SHA-256, size, minimum Core version, and a host ABI/protocol version, following the existing manifest acceptance rules. A release asset without integrity metadata is not installable.

### 3. Catalog collections are explicitly allow-listed

The browser catalog protocol accepts generic model entries but only recognizes named collections in its `fields` map. Current provider-specific collections include `litert-lm-models`, `geniex-models`, and `foundry-local-models`.

A TensorFold Model Hub collection therefore needs a coordinated schema change in `catalogProtocol.ts` (e.g. `tensorfold-models` mapped to `models`), plus a corresponding `kind` check and conf catalog collection. Merely adding an entry to `catalog.json` is insufficient: `parseAtomicModelCatalog` calls `projectAtomicModelCollection` for every allow-listed collection, and the collection's entries must reference valid model IDs and variants.

The generic catalog entry shape can represent a non-GGUF format, but TensorFold-specific metadata must be validated by the installer and Core's `model.yml` parser. Do not force the checkpoint into the `chat`/GGUF recommendation collection if the model Hub UI assumes GGUF file variants or projector semantics.

### 4. The current model downloader is Hugging Face file-plan centric

`prepareAtomicDownload` resolves HF model revisions to immutable 40-character commit SHAs, reads the repository's file metadata, validates paths, sizes and optional SHA-256, and pins URLs to that commit. It can download a declared file list and persist plans for resume.

This is useful if the supported TensorFold checkpoints are hosted on Hugging Face as ordinary files, but the install flow still must:
- select the exact TensorFold-supported checkpoint files (not download arbitrary repository contents);
- verify total size and all required hashes;
- stage under a temporary directory;
- write `model.yml` last, after every required file is complete and verified;
- clean only files created by that failed operation;
- resume only from the recorded immutable plan.

If TensorFold uses a non-HF source or a specialized package/container, the current downloader needs an explicit source adapter. Do not treat any HF repo as automatically compatible just because it contains safetensors.

### 5. Extension packages are workspace packages, not dynamically discovered by the package glob alone

The extensions workspace includes `**`, but that only makes package directories workspaces. A new provider extension still needs the app's actual extension installation/registration path and release packaging changes. `EngineManager.register()` only stores an instantiated extension; it does not discover or load packages.

The new extension should follow the Foundry Local/LiteRT-LM responsibilities:
- register provider settings descriptors;
- ask Core `POST /engines/versions` whether `tensorfold` is registered before showing the provider;
- list provider-specific model folders with a complete `model.yml`;
- mirror settings before load and subscribe to Core settings changes;
- load/unload/cancel through Core;
- chat through the Core gateway port and Bearer key;
- unload before deleting model files.

Before coding, trace the app's real startup loader and build/release packaging list so the new extension is bundled in development and production. Workspace inclusion by itself does not prove this.


### 6. The real extension loader and platform bundle rules are now confirmed

The startup path is concrete:

- `web-app/src/providers/ExtensionProvider.tsx` creates the managers, then awaits `ExtensionManager.registerActive()` and `load()`.
- `web-app/src/lib/extension.ts` reads active extension manifests from the Tauri Core service, imports the package's installed `dist/index.js`, instantiates its default class and registers its `provider` in the engine map.
- `src-tauri/src/core/setup.rs` installs every `.tgz` found in the app's `resources/pre-install` folder, reads each package's `package.json`, extracts it under the per-user extensions directory, and records the package name and entrypoint in `extensions.json`.
- The extension package name is a compatibility contract: the installer and persisted extension registry use it. Every shipped extension must retain the `@janhq/*` namespace. The pre-install tests reject renamed packages and duplicate provider IDs.
- Root `package.json` selects extension tarballs through `build:extensions:linux`, `build:extensions:win32` and `build:extensions:darwin`; the scripts use exclusions. The pre-install test derives platform membership from those scripts and verifies every included package has a tarball.

**Implication:** TensorFold needs one package named `@janhq/tensorfold-extension`, with `engine: "tensorfold"`, included by the Linux build script and excluded from Windows/macOS for v1. It must have a unique `providerId`, publish a pre-install tarball, and pass `tests/pre-install-tarballs.test.mjs`. Do not create a second package claiming the same provider.

### 7. The Atomic Chat Conf catalog has a unified schema and generated provider exports

The current `atomic-chat-conf/models/schema.catalog.json` enumerates provider `kind` values and required collection names. The catalog protocol in the app separately enumerates supported collection names and maps each to the expected array field. The existing provider exports (for example `litert-lm-models.json`) are generated compatibility views of the unified `models/catalog.json`, not independent sources of truth.

A TensorFold catalog change therefore spans at least:
- `models/schema.catalog.json`: add the `tensorfold` kind and required `tensorfold-models` collection;
- `models/catalog.json`: add entries with immutable source revision, file list, format and provider metadata, and collection references;
- `core/src/browser/catalogProtocol.ts`: add `tensorfold-models` to the collection allow-list and validate its `kind`;
- `atomic-chat-conf` validation scripts/workflow: validate TensorFold-specific metadata and supported family/format/platform constraints;
- generated legacy export only if a consumer is deliberately retained for compatibility.

The existing LiteRT-LM legacy JSON is explicitly marked deprecated and generated from the unified catalog. Do not add a parallel hand-maintained catalog source.

## Revised v1 architecture recommendation

- **Provider class:** native Core provider `tensorfold`; not a managed Docker provider.
- **Host scope:** Linux x86_64 + NVIDIA CUDA only for initial release. Core decides provider visibility through `/engines/versions`; the extension does not duplicate platform checks.
- **Executable:** choose one explicit ownership model before implementation:
  1. managed, signed/hashed TensorFold release assets installed under `<data>/tensorfold/backends/<version>/<platform>/`; or
  2. opt-in externally installed executable path in settings, default disabled/unset.
  
  Do not mix both resolution paths implicitly.
- **Models:** provider-specific `<data>/tensorfold/models/<id>/`, explicit TensorFold family and format metadata. No GGUF support claim.
- **Runtime:** one supervised TensorFold host per model through `SidecarTable`; loopback-only listener, readiness timeout, cancellation, journal, GPU residency hook and Core gateway.
- **Gateway:** only verified `GET /v1/models` and `POST /v1/chat/completions`; SSE only after confirmed against TensorFold's actual server.
- **Hub:** new catalog collection and install flow for exact compatible checkpoints; model metadata written last.
- **No unrelated process control:** never kill an existing llama.cpp server or any process not spawned and owned by this Core instance.

## Outstanding gates

1. Inspect the app's extension startup loader and release bundle allow-list.
2. Inspect the conf model catalog schemas/CI and determine how a provider-specific collection is published.
3. Confirm TensorFold Native 1.2.3's exact CLI contract, listen address, readiness marker, model argument format, model metadata/capability output and OpenAI/SSE behavior from source/docs or a safe local CLI-only inspection.
4. Choose managed binary distribution vs externally configured executable; document upgrade and integrity rules.
5. Validate one exact checkpoint against TensorFold's declared family/format and minimum VRAM before adding it to the Hub.
6. Implement Core unit tests for args, capability validation, path resolution, readiness, gateway route restrictions, cancellation, GPU occupancy and unload.
7. Only then implement the app extension and catalog installer.

## Current implementation status

**Still research only.** No changes were made to `AtomicBot-ai/atomic-chat-core`, `AtomicBot-ai/Atomic-Chat`, or `AtomicBot-ai/atomic-chat-conf`. This document is committed only to the LEONES research branch. The user's RTX 3050 has 4 GiB VRAM and the existing llama-server must remain untouched; therefore no GPU model-load or inference success is claimed.
