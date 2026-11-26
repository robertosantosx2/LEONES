# TensorFold Native 1.2.3: readiness and gateway security contract

Date: 2026-11-06  
Scope: source-level verification only; no model was loaded and no live gateway test was run.

## Findings verified against upstream source

### Process readiness

Atomic Core's `src/runtime/shared/process.ts` exposes `ReadyOptions.healthCheck`.  
`spawnAndAwaitReady` polls this callback every 200 ms (configurable with `healthIntervalMs`) and resolves with `readyVia: 'health'` when it returns true. A failed or not-yet-listening request is retried until startup timeout or process exit.

TensorFold Native v1.2.3 implements `GET /health` in `zig/src/server/status_routes.zig`:
- It reads the engine status and returns HTTP 503 with `{"status":"unavailable"}` while the engine is unhealthy.
- It returns HTTP 200 when the engine is healthy.
- When API-key authentication is enabled, the health response is deliberately reduced to `{"status":"ok"}`; the endpoint remains public so a local supervisor can probe it without credentials.
- During shutdown drain it returns a draining response rather than claiming normal health.

**Integration decision:** use Core's `healthCheck` callback against `http://127.0.0.1:<backend-port>/health`. Do not rely on a TensorFold log marker. Keep the health probe internal; it is not a frontend route.

### Authentication boundary

Atomic Core's `src/runtime/managed-text/gateway.ts`:
- binds its gateway only to `127.0.0.1`;
- checks the client's Host and Bearer key;
- validates method/path against the adapter-declared routes;
- proxies the request to the loopback backend;
- explicitly removes `authorization` and `x-api-key` before forwarding upstream;
- relays successful SSE responses as a stream rather than buffering them.

TensorFold Native v1.2.3's `zig/src/server/auth.zig` exempts `/health` from API-key gating; `/v1/models` and chat routes remain gated when a TensorFold API key is configured.

**Integration decision:** when Core's managed gateway is in front, do not set a TensorFold API key. The gateway's generated per-session key is the client-facing credential and is intentionally not forwarded upstream. Run TensorFold on `127.0.0.1` only; never expose its backend port in `SessionInfo`. Publish the gateway port and gateway key only.

### Routes and streaming

The existing LiteRT-LM runtime declares the minimal managed-text route set:
- `GET /v1/models`
- `POST /v1/chat/completions`

TensorFold supports these OpenAI-compatible endpoints and SSE chat responses. A TensorFold adapter should declare the same two routes unless additional API surface is deliberately reviewed and tested.

### Process ownership

Reuse `SidecarTable` for single-process-per-model tracking, serialization, process journaling, cancellation, exit monitoring and shutdown. Reuse `spawnAndAwaitReady`, `randomFreePort`, `generateGatewayKey` and `startManagedGateway`. Do not create a second process supervisor or expose the backend's port.

## Remaining validation

This note is a source-contract reconciliation, not runtime proof. Still required:
1. Exercise a real TensorFold checkpoint and verify `/health`, `/v1/models`, non-streaming chat and SSE.
2. Exercise the Core gateway against that live process, including Bearer authentication, Host validation and proof that the upstream receives no client key.
3. Verify clean unload/shutdown and cancellation through the Core runtime.
4. Keep the reference machine's GPU safety floor; do not stop or signal unrelated GPU processes to make room.

No inference throughput, model compatibility, or actual RTX 3050 load success is claimed.

## Source references

- TensorFold v1.2.3 health: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/server/status_routes.zig
- TensorFold v1.2.3 auth: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/server/auth.zig
- TensorFold v1.2.3 serve lifecycle: https://github.com/ashhart/TensorFold/blob/v1.2.3/zig/src/server/serve.zig
- Atomic Core process readiness: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/process.ts
- Atomic Core sidecar table: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/shared/sidecar.ts
- Atomic Core managed gateway: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/managed-text/gateway.ts
- Atomic Core LiteRT-LM route/gateway pattern: https://github.com/AtomicBot-ai/atomic-chat-core/blob/main/src/runtime/litert-lm/runtime.ts
