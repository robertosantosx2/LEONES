# TensorFold Web — development roadmap

Status: initial implementation 0.2.0 created in branch feat/tensorfold-web-standalone.
Later destination: robertosantosx2/TensorFold.
LEONES remains the source of development until validation and review are complete.

## Goal
Deliver a self-contained local interface for TensorFold Engine: chat, streaming, model discovery, and a live status dashboard.

## Milestones
1. M0 — Base source: Python stdlib bridge, HTML/CSS/JS frontend, launcher, documentation.
2. M1 — Functional compatibility: test /health, /stats, /v1/models, SSE chat, errors, and reconnection.
3. M2 — UI and assets: local official logo, responsive layout, navigation, loading/error states, accessibility.
4. M3 — Dashboard: identify the real /stats schema in Engine 1.2.0; display only verified metrics.
5. M4 — Security and robustness: request limits, path traversal, client disconnects, timeouts, CORS/CSP, automated tests.
6. M5 — Release: reproducible tests on Ubuntu and RTX 3050; installation guide; versioning; review; transfer PR to TensorFold.

## Acceptance criteria
- Install and run without npm, pip, or external runtime libraries.
- Start with one shell script.
- Serve PNG, SVG, CSS, and JS with correct MIME types; GET and HEAD work.
- Chat discovers models automatically and streams SSE output progressively.
- Dashboard only displays metrics confirmed by actual Engine responses.
- UI reports Engine unavailability clearly.
- Default bind is 127.0.0.1.
- Reproducible tests documented before a stable release.

## Decisions
- Keep frontend and bridge separate from Engine source.
- Do not alter llama-server or other local services.
- Do not assume all TensorFold versions expose the same /stats schema.
- The official logo will be checked in locally for the offline-ready release; runtime should not depend on Hugging Face.
