# Atomic Chat Core: TensorFold runtime test plan

**Date:** 2026-11-06  
**Status:** LEONES implementation-preparation artifact; no Atomic Core source or tests have been changed.  
**Target:** a future Linux x86_64 + NVIDIA CUDA implementation of TensorFold Native, initially one text-chat model per runtime process.

This plan turns the verified Core contracts and the TensorFold integration blueprint into an executable acceptance matrix. It is deliberately independent of a particular model: unit and lifecycle tests can be implemented before a model is available, but the live acceptance suite must remain blocked until an exact checkpoint has a native CUDA serving path and a measured memory floor that fits the test GPU.

## 1. Test architecture and boundaries

Keep policy tests separate from host I/O. Follow the Core repository's existing conventions and use injected seams for:

- platform and CUDA-device discovery;
- executable resolution and command execution (`--version`, `capabilities --json`);
- filesystem/model-root validation;
- free-port allocation;
- process spawn, stdout/stderr, exit notification and termination;
- HTTP health probes and gateway startup;
- GPU claim/occupancy reporting;
- clocks/timeouts where the existing test helpers permit injection.

Do not create a second process supervisor. The runtime under test must use the existing `LocalRuntime`, `SidecarTable`, `spawnAndAwaitReady`, `randomFreePort`, GPU-residency and managed-gateway contracts.

Recommended test layers:

1. **Pure unit tests:** parsers, model metadata, platform policy, argument construction and route policy. No GPU, network listener or TensorFold binary.
2. **Runtime lifecycle tests with fakes:** process ownership, startup/readiness, cancellation, gateway failure, unload and occupancy. No real model.
3. **Gateway contract tests:** use a local fake OpenAI-compatible backend to prove auth, Host validation, route allow-list, key stripping and SSE relay.
4. **Opt-in live Linux/CUDA tests:** exact TensorFold binary and exact checkpoint on a qualified GPU. Never run in generic CI.

## 2. Pure unit-test matrix

| ID | Area | Input / action | Required assertion |
|---|---|---|---|
| U-01 | Capabilities JSON | Valid supported schema, version and CUDA backend | Parse normalized capabilities and exact engine version. |
| U-02 | Capabilities JSON | Invalid JSON, empty output or wrong top-level types | Reject with stable, actionable error code; do not spawn a model. |
| U-03 | Capabilities JSON | Missing version/schema/backend | Reject; never infer defaults from a partial document. |
| U-04 | Backend policy | CPU-only or Metal-only capability output | Refuse Linux/CUDA load before process spawn. |
| U-05 | Family/format | Exact supported family + format pair | Accept only the exact admitted pair, not family-name substring matches. |
| U-06 | Family/format | Known family with unsupported format | Reject even if family appears in the registry. |
| U-07 | Model metadata | Valid typed `tensorfold` block and checkpoint directory | Accept and return normalized immutable model descriptor. |
| U-08 | Model metadata | Missing family/format, wrong types or invalid context | Reject with field-specific error; no fallback to GGUF metadata. |
| U-09 | Model path | Relative path inside TensorFold model root | Resolve to canonical path under the configured root. |
| U-10 | Model path | Traversal (`../`), symlink escape or disallowed absolute path | Reject; no path may escape the allowed root unless an explicit policy permits it. |
| U-11 | Arguments | Valid model, port and context | Produce argv array with `serve`, model, loopback host, selected port, explicit CUDA, parallel=1, bounded context and no-update-check. |
| U-12 | Arguments | Host override, parallel > 1 or unsupported option supplied by settings | Ignore/reject unsafe overrides; never bind wildcard/public interfaces. |
| U-13 | Arguments | Model path containing spaces or shell metacharacters | Preserve as one argv element; no shell command string is constructed. |
| U-14 | Platform gate | Linux x86_64 + detected NVIDIA CUDA | Eligible to proceed to executable/capability validation. |
| U-15 | Platform gate | macOS, Windows, non-x86_64, no NVIDIA or unsupported CUDA device | Refuse before process spawn with explicit unsupported-platform/device reason. |
| U-16 | Routes | GET models and POST chat completions | Allow exactly the two initial routes. |
| U-17 | Routes | Any other method/path (including embeddings, completions, tools, audio, vision) | Deny by default. |
| U-18 | Settings | Missing/invalid executable, timeout, context or parallel value | Apply documented safe default or reject invalid value; never resolve an arbitrary PATH alias silently. |

## 3. Runtime lifecycle and ownership matrix

All tests in this section should use injected fake process, HTTP, port and GPU-residency dependencies. Assertions must inspect calls and state transitions, not only returned values.

| ID | Scenario | Stimulus | Required assertion |
|---|---|---|---|
| L-01 | Successful load | Valid model; process starts; `/health` returns 200 | Session is published only after health readiness and gateway startup. |
| L-02 | Readiness retry | Health initially refuses/returns 503, then returns 200 | Retry until healthy; do not treat stdout text as readiness. |
| L-03 | Startup timeout | Health never succeeds | Fail load, terminate only the owned child, close reserved resources and release GPU claim only after child exit is confirmed. |
| L-04 | Early process exit | Child exits before health succeeds | Fail promptly with captured diagnostics; do not publish a session. |
| L-05 | GPU claim denied | Residency policy refuses claim | No process spawn and no port/gateway allocation. |
| L-06 | Gateway startup failure | Backend is healthy but managed gateway cannot bind/start | Terminate owned child; no session published; no leaked claim after confirmed exit. |
| L-07 | Cancellation during startup | Abort signal while waiting for health | Stop only the child owned by this load; reject as cancellation; no orphan process. |
| L-08 | Cancellation after ready | Abort/unload active session | Close gateway and terminate owned child; report completion only after exit. |
| L-09 | Unload success | Normal active session unload | Gateway closes; owned child exits; session table clears; occupancy clears after exit. |
| L-10 | Failed termination | Owned child ignores/does not confirm termination | Keep GPU occupancy reserved and expose failure; never kill another PID to recover. |
| L-11 | Concurrent load same model | Two callers request the same model simultaneously | Existing SidecarTable serialization/deduplication semantics prevent duplicate unmanaged servers. |
| L-12 | Concurrent different model | Second load while GPU is claimed | Respect Core GPU arbitration; do not oversubscribe or silently evict another provider. |
| L-13 | Core shutdown | Shutdown while idle and while model is active | Idempotent shutdown; active owned child is stopped; no unrelated process is signalled. |
| L-14 | Process exits after ready | Child exits unexpectedly | Session is invalidated, gateway closes and occupancy is reconciled with confirmed process exit. |
| L-15 | Port allocation | Requested backend port is occupied | Allocate a fresh free loopback port; never fall back to a wildcard bind. |
| L-16 | Diagnostics | Startup or runtime failure | Preserve bounded stdout/stderr/log context without leaking bearer keys or private checkpoint tokens. |

## 4. Managed-gateway security and API matrix

Use a fake backend bound to loopback and the actual Core managed gateway. Do not substitute a hand-written proxy.

| ID | Scenario | Request / backend observation | Required assertion |
|---|---|---|---|
| G-01 | Gateway bind | Inspect listener address | Gateway binds only to 127.0.0.1. |
| G-02 | Backend bind | Inspect TensorFold argv/config | Backend is instructed to bind only to 127.0.0.1. |
| G-03 | Valid authentication | Correct per-session Bearer key and valid Host | Request reaches the declared backend route. |
| G-04 | Missing/wrong key | No key or incorrect key | Gateway rejects request; backend receives nothing. |
| G-05 | Host validation | Host header outside gateway's accepted local host policy | Gateway rejects request; backend receives nothing. |
| G-06 | Key stripping | Backend records inbound headers | Client Authorization and x-api-key are not forwarded upstream. |
| G-07 | Route allow-list | Try undeclared method/path | Gateway rejects it before proxying. |
| G-08 | Models endpoint | Authenticated GET /v1/models | Backend response is passed through with expected status/body. |
| G-09 | Chat JSON | Authenticated POST /v1/chat/completions with JSON response | Status, content type and body are preserved. |
| G-10 | Chat SSE | Backend emits multiple SSE frames and flushes incrementally | Client receives streamed frames without full-response buffering; completion/termination is propagated. |
| G-11 | Backend unavailable | Backend closes/refuses after gateway is created | Gateway returns controlled upstream failure; no credentials leak. |
| G-12 | Session isolation | Two sessions use different generated keys | A key from session A cannot access session B. |
| G-13 | Public session metadata | Inspect SessionInfo returned to app | Only gateway port/key are published; backend port and backend key are not exposed. |
| G-14 | Health endpoint | Supervisor probes backend /health | Probe remains internal and is not added to frontend route policy. |

**Authentication design constraint:** do not configure a second TensorFold API key when the Core managed gateway is the security boundary. The gateway-generated session key is client-facing and is stripped before forwarding upstream.

## 5. Live Linux/CUDA acceptance suite (opt-in only)

These tests must be explicitly enabled by a maintainer on a dedicated test machine. They must not run on ordinary CI runners or automatically download a model.

### Admission prerequisites

- Exact TensorFold binary path and pinned version are recorded.
- `--version` and `capabilities --json` succeed for that binary.
- Exact checkpoint repository/revision, family and format are recorded.
- The checkpoint passes TensorFold's own `info` inspection.
- Its reported memory floor fits currently free VRAM, and a conservative free-VRAM guard is satisfied.
- The device is not being used by another workload that would be interrupted; the test must not stop or signal unrelated processes.
- If any prerequisite fails, mark the live suite **SKIPPED/BLOCKED**, not passed.

### Required live cases

| ID | Scenario | Evidence to retain |
|---|---|---|
| E-01 | Binary identity and capabilities | Version, SHA-256, capabilities JSON, driver/CUDA/device details. |
| E-02 | Model admission | Repository/revision, local checkpoint path, family/format, `info` output and memory floor. |
| E-03 | Server startup | Exact argv (redacted), PID ownership, loopback listener, startup duration and /health response. |
| E-04 | Model discovery | Authenticated /v1/models response through the Core gateway. |
| E-05 | Non-streaming chat | Request/response pair, status, latency and generated text. |
| E-06 | SSE chat | Raw event sequence, first-token latency, completion marker and stream termination. |
| E-07 | Gateway boundary | Valid/invalid bearer and Host checks; backend header capture proving key stripping. |
| E-08 | Unload | Session removal, owned child exit, gateway close and GPU occupancy release. |
| E-09 | Cancellation | Cancel an in-flight load or generation; prove only the owned process is affected. |
| E-10 | Shutdown | Core shutdown leaves no owned TensorFold child or listener behind. |
| E-11 | Resource record | VRAM before/peak/after, RAM before/peak/after, load time, prompt/decode tokens/s, context and full logs. |

A passing `tensorfold info`, capability registry entry, CUDA fatbin, health endpoint alone, or successful process start is **not** a passing live test. The full general-chat JSON and SSE paths must succeed through the authenticated Core gateway.

## 6. CI and test-command policy

- Keep pure unit and fake lifecycle/gateway tests in normal Core CI.
- Keep live CUDA tests behind an explicit opt-in environment flag and a dedicated self-hosted runner label; default behavior must be skip.
- Never download model weights as part of generic CI.
- Preserve test logs but redact bearer keys, tokens and private repository credentials.
- Run the Core repository's documented formatting, lint, type-check and test commands; record exact commands and outcomes in the implementation PR.
- Add regression tests before changing shared contracts or provider wiring.

## 7. Exit criteria and sequencing

The future implementation is ready for review only when:

1. All pure unit tests pass.
2. All fake lifecycle and gateway security tests pass.
3. Existing Core runtime regression tests pass.
4. A model-specific live CUDA run passes health, models, JSON chat, SSE, gateway auth/key stripping, unload and shutdown on the declared support hardware.
5. The PR records exact engine version, binary hash, checkpoint revision, GPU/driver, memory floor and measured resource/performance evidence.
6. App/UI and catalog changes are separately tested against the finalized Core provider/model contract.

Until item 4 is complete, keep the upstream Core/app implementation deferred and keep LEONES PR #139 in draft. This avoids shipping a provider that registers correctly but cannot actually generate text on its advertised hardware.

## References

- [Atomic Core LocalRuntime contract](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/local-runtime.ts)
- [Atomic Core SidecarTable](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/sidecar.ts)
- [Atomic Core process supervision](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/process.ts)
- [Atomic Core managed-text gateway](https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/managed-text/gateway.ts)
- [LEONES Core contract map](atomic-chat-tensorfold-core-contracts-2026-11.md)
- [LEONES implementation blueprint](atomic-chat-tensorfold-implementation-blueprint-2026-11.md)
- [LEONES readiness and gateway security contract](atomic-chat-tensorfold-readiness-gateway-security-2026-11-06.md)
- [LEONES checkpoint eligibility audit](atomic-chat-tensorfold-checkpoint-eligibility-2026-11-06.md)
