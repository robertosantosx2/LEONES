# TensorFold Web — development roadmap

Status: implementation 0.2.0 in active development on feat/tensorfold-web-standalone. Source-level integration tests and the documented native stats schema have been added; target-machine execution remains pending.
Later destination: robertosantosx2/TensorFold.
LEONES remains the source of development until validation and review are complete.

## Goal
Deliver a self-contained local interface for TensorFold Engine: chat, streaming, model discovery, and a live status dashboard.

## Milestones
1. M0 — Base source: Python stdlib bridge, HTML/CSS/JS frontend, launcher, documentation.
2. M1 — Functional compatibility: source-level integration tests now cover /health, /stats, /v1/models, SSE forwarding, static assets, and error routes. Run the suite on Ubuntu and complete an actual browser-to-Engine chat test.
3. M2 — UI and assets: responsive layout, navigation, model selection, live metric tiles, raw diagnostic JSON, and logo fallback are implemented. Check in the official logo as a local binary asset; complete accessibility review.
4. M3 — Dashboard: native /stats schema verified against upstream status_routes.zig; dashboard renders decode/prefill rates, scheduler counts, memory, and token totals. Confirm against the user's running Engine 1.2.0 response.
5. M4 — Security and robustness: request body limit, loopback default, path traversal protection, proxy timeouts, HTTPS engine URL support, and automated tests are implemented. Review client disconnect behavior, CORS/CSP, and production hardening.
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
