# TensorFold implementation blueprint for Atomic Chat Core

**Date:** 2026-11-05  
**Status:** LEONES engineering blueprint; not an upstream implementation.  
**Reference source:** `AtomicBot-ai/atomic-chat-core` `main`, inspected 2026-11-05.  
**Initial scope:** Linux x86_64 + NVIDIA CUDA, one text model per native server, OpenAI chat only.

## 1. Architectural decision

Implement TensorFold as a **native local runtime**, not as a managed/container provider and not as a remote OpenAI-compatible URL.

Reasons:

- The Linux release is a native Zig executable and the README says serving requires no Python or MLX installation.
- Atomic Core already has a `LocalRuntime` contract and native sidecar/process supervision.
- The engine exposes an OpenAI-compatible local HTTP API, so Atomic can place its existing authenticated session gateway in front of it.
- TensorFold's checkpoint directory and family/format metadata are not GGUF. Reusing the GGUF loader or GGUF compatibility checks would be incorrect.

The engine's own port must remain private to the runtime. Clients receive only the gateway's loopback port and per-session bearer key in `SessionInfo`.

## 2. Proposed model contract (requires ADR + app/core contract change)

Add a typed `tensorfold` block to `ModelYml`, initially:

```ts
export interface ModelYmlTensorFold {
  /** TensorFold family, validated against capabilities output. */
  family: string
  /** Exact native checkpoint format, validated against the family. */
  format: string
  /** Checkpoint directory, either absolute or data-folder-relative via model_path. */
  repository?: string
  revision?: string
  /** Optional context ceiling read from checkpoint metadata. */
  context_length?: number
}
```

Add `tensorfold?: ModelYmlTensorFold` to `ModelYml` and append `tensorfold` to `MODEL_YML_KEY_ORDER`.

This is a proposed minimal contract, not a claim that these fields are already accepted by Atomic. Before coding, verify the actual checkpoint metadata keys and decide whether `repository/revision` belong in the typed block or remain optional provenance. Do not duplicate model weights or create a new Hugging Face downloader.

## 3. Exact core touch points

| File | Required change |
|---|---|
| `src/contracts/session.ts` | Add `'tensorfold'` to `LocalProviderId`; document Linux x64 + NVIDIA CUDA scope. |
| `src/contracts/model-yml.ts` | Add `ModelYmlTensorFold`, optional `tensorfold` block and key order. |
| `src/contracts/settings.ts` | Add `TensorFoldConfig` with `executable`, `ctx_len`, `timeout`, `parallel` defaults/semantics. |
| `src/settings/schema.ts` | Register provider in `LOCAL_PROVIDER_IDS` and `CANONICAL_VALUE_TYPES`. |
| `src/settings/schema/tensorfold.json` | Add schema with executable path, context, timeout and one-slot default. |
| `src/config/paths.ts` | Add `layout.provider('tensorfold')` model root; do not share the GGUF models root. |
| `src/runtime/tensorfold/model-yml.ts` | Strictly parse/validate the typed block and reject absent/invalid family or format. |
| `src/runtime/tensorfold/capabilities.ts` | Parse `capabilities --json`; validate schema, engine version, CUDA backend, family and format. |
| `src/runtime/tensorfold/args.ts` | Pure argv builder: `serve MODEL --host 127.0.0.1 --port PORT --parallel 1 --context N --backend cuda --no-update-check`. |
| `src/runtime/tensorfold/runtime.ts` | Implement `LocalRuntime`, process lifecycle, session table, route policy and GPU occupancy. |
| `src/runtime/tensorfold/index.ts` | Public module entry. |
| `src/runtime/index.ts` | Export the provider. |
| `src/core/create.ts` | Instantiate only when Linux x64 + NVIDIA CUDA and a usable executable are detected; add to runtime map. |
| `test/runtime/tensorfold/` | Unit tests for parsers, argv, platform gating, lifecycle, cancellation and route policy. |

The final file list must be reconciled with the current core tree when the upstream implementation branch is opened.

## 4. Runtime lifecycle

1. Read the provider's model entry from a TensorFold-specific `ModelRegistry`.
2. Validate `model.yml` and the checkpoint directory; do not inspect it as GGUF.
3. Resolve the explicit executable setting (default only to a documented, validated install path; never assume a PATH alias exists).
4. Run `tensorfold-native --version` and `capabilities --json`; reject unsupported versions, non-CUDA binaries, unknown family/format pairs and malformed output before spawning a model.
5. Acquire the core's GPU claim before starting the child. Report occupancy while loading.
6. Reserve a loopback port and launch with argv (never a shell), `--host 127.0.0.1`, `--backend cuda`, `--parallel 1`, bounded context and `--no-update-check`.
7. Use `spawnAndAwaitReady` with a real `GET /health` 2xx health check, not an assumed log phrase.
8. Start `startManagedGateway` with a fresh key and exactly these initial routes:
   - `GET /v1/models`
   - `POST /v1/chat/completions`
9. Publish the gateway's port/key in `SessionInfo`; never expose the engine port.
10. On unload/cancel/shutdown, terminate only the owned child and close the gateway. Retain GPU occupancy until the child exit is confirmed.

## 5. Behavior deliberately excluded from v1

- Model downloads, Hub catalogue and installer.
- macOS, Windows, AMD, CPU and multi-GPU support.
- Embeddings, raw completions, Responses API, tool calling, JSON schema, vision, audio, reranking and other TensorFold endpoints.
- Dynamic runtime updates or package-manager integration.
- Automatic eviction of unrelated processes.

Every extra capability requires a separate contract and tests; a route appearing in TensorFold's API documentation is not enough to expose it through Atomic.

## 6. Acceptance gates

### Static/unit
- Capabilities parser rejects malformed JSON, missing schema/version, no CUDA backend and unsupported family/format.
- Argument builder always binds loopback, explicit CUDA and one parallel slot; never emits shell text.
- Model path validation prevents traversal outside the configured TensorFold models root unless an explicitly supported absolute path is selected.
- Platform probe refuses unsupported OS/architecture/GPU combinations before loading.
- Cancellation, timeout, early exit, failed termination and gateway startup failure leave no orphan process or leaked port.
- Route policy refuses undeclared methods/paths; streaming responses are relayed without buffering.
- GPU occupancy remains claimed until process termination is confirmed.

### Live Linux/CUDA
- TensorFold version/capabilities are detected from the exact executable path.
- A real checkpoint loads on the supported GPU.
- `/health`, `/v1/models`, non-streaming chat and SSE complete.
- Atomic gateway auth works and direct engine-port access is not returned to clients.
- Load/unload/cancel/shutdown do not stop other processes.
- Record model revision, format, context, free/used VRAM before and after, load time, prompt/decode throughput and full logs.

## 7. Current reference-machine gate

The captured RTX 3050 has 4096 MiB total VRAM. The last snapshot showed 2714 MiB used (2685 MiB by the pre-existing `llama-server`) and only 1382 MiB free. That process was deliberately left running.

The LEONES PoC now refuses to start a model unless at least 3072 MiB is free by default. This is a safety floor, not a fit guarantee. The live acceptance gate remains **not run** until sufficient VRAM is available without terminating or changing unrelated workloads.

## References

- [Atomic Core LocalRuntime contract](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/local-runtime.ts)
- [Atomic Core native LiteRT-LM runtime](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/litert-lm/runtime.ts)
- [Atomic Core process supervisor](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/process.ts)
- [Atomic Core session gateway](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/managed-text/gateway.ts)
- [Atomic Core model contract](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/contracts/model-yml.ts)
- [TensorFold Linux quick start and API](https://github.com/ashhart/TensorFold/blob/main/README.md)
- [TensorFold API routes](https://github.com/ashhart/TensorFold/blob/main/docs/api.md)
