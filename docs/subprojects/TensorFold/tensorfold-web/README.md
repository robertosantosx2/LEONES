# TensorFold Web

Lightweight local web UI for TensorFold Engine. Development starts in LEONES; a reviewed release will later be transferred to the TensorFold repository.

## Principles
- Python standard library only; no Node.js, npm, framework, or third-party Python package.
- Plain HTML, CSS, and JavaScript.
- Local-first: bridge binds to 127.0.0.1 by default.
- OpenAI-compatible chat streaming through /v1/chat/completions.
- Engine health, model discovery, and best-effort statistics view.
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

Or run ./run-tensorfold-web.sh .

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
- The TensorFold logo is loaded from the official TensorFold Hugging Face asset URL; a local checked-in asset is planned for offline use.

Version 0.2.0 is the first source implementation in LEONES. It is not yet a verified release: run the local test checklist and record results before tagging or transferring it to TensorFold.
