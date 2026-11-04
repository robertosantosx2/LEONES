# TensorFold Web — development roadmap

Status: implementation 0.2.0 in active development on feat/tensorfold-web-standalone. Source-level integration tests and the documented native stats schema have been added; target-machine execution remains pending.
Later destination: robertosantosx2/TensorFold.
LEONES remains the source of development until validation and review are complete.

## Goal
Deliver a self-contained local interface for TensorFold Engine: chat, streaming, model discovery, and the native live status dashboard. The same frontend must be installable as a mobile-friendly PWA and packageable as native desktop apps with Pake.

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
- PWA manifest and service worker pass static-serving checks; offline mode is limited to the app shell and clearly reports that live Engine features require connectivity.
- Pake configuration points to the local bridge origin, never to a public hosted Engine; packaged desktop app can reach the bridge and stream chat.
- Ubuntu Pake build produces the selected installer formats and a standalone executable; Windows/macOS packaging is verified on native runners before release.
- Reproducible tests documented before a stable release.

## Decisions
- Keep frontend and bridge separate from Engine source.
- Do not alter llama-server or other local services.
- Do not assume all TensorFold versions expose the same /stats schema.
- The official logo will be checked in locally for the offline-ready release; runtime should not depend on Hugging Face.


## PWA and Pake packaging

PWA and Pake are complementary delivery targets, not alternatives:

- **PWA** serves the same frontend in a standards-based browser. The manifest supplies the app identity and icons; the service worker caches only the static shell. `/api/*`, `/api/dashboard`, model discovery, chat streaming and live statistics are never cached.
- **Pake** wraps the running local web UI in a native system WebView. The package target is `http://127.0.0.1:8787/`, served by the existing Python standard-library bridge. Do not package the raw HTML directory as a desktop app: its API calls require the bridge origin.
- **Lifecycle boundary:** the Pake app does not bundle TensorFold Engine, models, Python, or automatically start/stop the bridge in this first integration. Start the bridge with `run-tensorfold-web.sh` before opening the Pake app. A later native launcher/supervisor can be designed separately, with explicit ownership and safe shutdown.
- **Ubuntu build prerequisites:** Node.js 20.9+, Rust 1.85+, and Pake's WebKitGTK/Tauri development dependencies. Pake CLI emits Linux packages (DEB/AppImage by default when selected) and can retain a standalone executable.
- **Windows/macOS:** build on native runners with their own Tauri toolchains; do not claim cross-compilation from Ubuntu without a separately validated toolchain.

### First local Pake test

1. Start TensorFold Engine as usual (do not restart it from this packaging step).
2. Start TensorFold Web bridge on loopback:
   ```bash
   bash ./run-tensorfold-web.sh
   ```
3. In another terminal, verify `http://127.0.0.1:8787/` and then build:
   ```bash
   bash ./build-pake.sh
   ```
4. Install/open the generated Ubuntu package or run the retained binary. Verify model discovery, a streamed chat, navigation, and (if Engine was started with `--dashboard`) the native dashboard.
5. Record Pake CLI version, Rust/Node versions, output file names, build result and runtime checks in the validation log. A successful package build alone is not proof that bridge lifecycle or Engine features work.

Official Pake references:
- https://pake.run/docs/cli/getting-started
- https://pake.run/docs/cli/options
- https://pake.run/docs/cli/advanced
- https://github.com/tw93/Pake
