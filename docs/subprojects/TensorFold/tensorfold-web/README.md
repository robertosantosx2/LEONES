# TensorFold Web

Lightweight local web UI for TensorFold Engine. Development starts in LEONES; a reviewed release will later be transferred to the TensorFold repository.

## Principles
- Python standard library only; no Node.js, npm, framework, or third-party Python package.
- Plain HTML, CSS, and JavaScript.
- Local-first: bridge binds to 127.0.0.1 by default.
- OpenAI-compatible chat streaming through /v1/chat/completions.
- Engine health, model discovery, and a dashboard based on the native `/stats` fields.
- Static assets (PNG, SVG, CSS, JS) served with MIME types and GET/HEAD support.

## Architecture

    Browser :8787
       |-- static files (HTML, images, CSS, JS)
       |-- /api/health ----------> Engine /health
       |-- /api/stats ----------> Engine /stats
       |-- /api/v1/models -------> Engine /v1/models
       \`-- /api/v1/chat/completions -> Engine /v1/chat/completions (SSE)

## Run

Requires Python 3.10+ and a running TensorFold Engine.

    python3 tensorfold-web-bridge.py --web-root . --engine-url http://127.0.0.1:8080 --host 127.0.0.1 --port 8787

Open http://127.0.0.1:8787/ .

Or run `bash ./run-tensorfold-web.sh` (or make it executable once with `chmod +x run-tensorfold-web.sh` and then use `./run-tensorfold-web.sh`).

## API routes

| Web route | Engine route | Method |
|---|---|---|
| /api/health | /health | GET, HEAD |
| /api/stats | /stats | GET, HEAD |
| /api/v1/models | /v1/models | GET, HEAD |
| /api/v1/chat/completions | /v1/chat/completions | POST, streamed |

The bridge serves files below its configured web root, rejects path traversal, sets MIME types, supports HEAD, and disables caching for the application shell.

## Security

The default bind is loopback. Do not expose this server to a LAN or the public internet as-is. There is no user authentication, TLS termination, or multi-user isolation in this prototype. Keep the Engine and bridge on a trusted local machine.

## Current prototype limits

- Statistics are displayed as raw JSON because the exact /stats schema varies by Engine build.
- The UI handles OpenAI-style SSE choices[0].delta.content; tool calls, multimodal payloads, and nonstandard event formats are not implemented.
- Conversations are held in browser memory only and are not persisted.
- The TensorFold logo currently loads from the official TensorFold Hugging Face asset URL with a visual fallback. A checked-in local binary asset is still required for fully offline operation.

Version 0.2.0 is the first source implementation in LEONES. It is not yet a verified release: run the local test checklist and record results before tagging or transferring it to TensorFold.

## Smoke tests

Run the standard-library static-serving checks from this directory:

    python3 -m unittest discover -s tests -v

The standard-library integration tests cover the index route (including query strings), PNG MIME type, GET/HEAD behavior, missing files, encoded path traversal, health/stats/model proxying, SSE chat forwarding, and unavailable/unknown routes. They are source-level tests and have not yet been executed on the target Ubuntu workstation.

## Dashboard data contract

The UI follows the native TensorFold `GET /stats` snapshot when the Engine is started with `--dashboard`:

- `running`, `waiting`
- `decode_tokens_per_second`, `prefill_tokens_per_second`
- `generation_tokens_running`
- `prompt_tokens_total`, `generation_tokens_total`
- `mtp_drafted_total`, `mtp_accepted_total`, `decode_rounds_total`
- `memory.active`, `memory.cache`, `memory.peak`, optional `memory.limit`

The current dashboard surfaces the most useful live values and keeps the complete response available for diagnostics. Memory counters are bytes and are displayed as GiB. Optional/missing values are not fabricated.

The native `/health` response supplies the served model name, backend, device and readiness state. `/stats` and `/dashboard` are opt-in Engine routes and return 404 if the Engine was not started with `--dashboard`.

Upstream references:
- [TensorFold API contract](https://github.com/ashhart/TensorFold/blob/main/docs/api.md)
- [Native stats snapshot implementation](https://github.com/ashhart/TensorFold/blob/main/zig/src/server/status_routes.zig)
- [Native live status fields](https://github.com/ashhart/TensorFold/blob/main/zig/src/server/live.zig)
