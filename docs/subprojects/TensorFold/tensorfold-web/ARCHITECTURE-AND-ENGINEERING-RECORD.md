# TensorFold Web — architecture, engineering record and transfer dossier

**Document status:** implementation record for the LEONES staging project  
**Code status:** prototype / integration candidate; not a production release  
**Development branch:** `feat/tensorfold-web-standalone`  
**Staging PR:** [LEONES #138](https://github.com/robertosantosx2/LEONES/pull/138)  
**Intended upstream:** [ashhart/TensorFold](https://github.com/ashhart/TensorFold)  
**Engine endpoint used by the local development setup:** `http://127.0.0.1:8080`  
**Default Web bridge:** `http://127.0.0.1:8787`

This document is deliberately explicit about what is implemented, what has been source-tested, what has passed CI, what still needs a real workstation test, and which decisions are intentional compromises. A green test suite is not presented as proof of a complete desktop release.

## 1. Executive summary

TensorFold Web is a local-first control and interaction surface for TensorFold Engine. It combines:

1. A browser interface for chat, model discovery, Engine health and diagnostics.
2. A small Python standard-library bridge that serves the frontend and proxies selected Engine APIs.
3. An embedded view of TensorFold's own native `/dashboard` page rather than a second independently maintained dashboard.
4. A PWA delivery path for browser installation and a conservative offline application shell.
5. An experimental Pake desktop wrapper that opens the local bridge through a native WebView.
6. A documented Engine process manager for users who explicitly choose to launch an Engine process from the UI.

Development was intentionally staged in LEONES first. This provides a reviewable engineering record, repeatable tests and a transfer dossier before any integration into the upstream TensorFold repository.

The intended product is a single interface that works in a desktop browser, mobile browser/PWA and packaged desktop window. The Engine, model weights, accelerator runtimes and inference process remain separate components.

## 2. Objectives and non-goals

### 2.1 Product objectives

- Provide a simple local control panel for TensorFold Engine.
- Discover the models exposed by the Engine instead of maintaining a static model catalogue.
- Submit OpenAI-compatible chat-completion requests and display server-sent-event (SSE) output progressively.
- Show Engine health and real status information without fabricating performance values.
- Reuse the upstream native dashboard when it is available.
- Expose model/server diagnostics and a guided process-launch surface.
- Work at narrow/mobile viewport sizes and support browser installation as a PWA.
- Package the same local interface as a native desktop window with Pake.
- Keep the frontend and bridge independently testable and easy to move upstream.
- Avoid requiring a JavaScript build toolchain or third-party Python modules to run the web interface itself.

### 2.2 Explicit non-goals for this iteration

- Reimplement the inference engine, scheduler, tokenizer, model loader or accelerator backend.
- Bundle model weights, CUDA, Metal, Python or TensorFold Engine inside the Pake desktop package.
- Provide remote multi-user access, accounts, authentication, authorization roles or tenant isolation.
- Claim production security for a server exposed to a LAN or the public internet.
- Guarantee compatibility with every TensorFold release or every possible `/stats` schema.
- Implement every OpenAI API feature, tool-call flow, multimodal payload or arbitrary event format.
- Guarantee Windows/macOS desktop artifacts before native CI builds and runtime tests exist.
- Treat PWA offline caching as offline inference.
- Automatically take ownership of, restart or terminate a pre-existing user-managed Engine or llama-server process.

## 3. Design principles and commitments

These are the project commitments used to evaluate changes:

1. **Engine remains authoritative.** Inference and performance metrics come from TensorFold Engine responses, not browser-side estimates.
2. **Local-first by default.** The bridge binds to loopback (`127.0.0.1`) and the Pake target is a loopback URL.
3. **No disturbance to existing services.** The UI must not silently restart, reconfigure or kill an Engine it did not launch.
4. **Small runtime footprint.** The web interface uses HTML, CSS and browser JavaScript; the bridge uses Python's standard library.
5. **No mandatory frontend build chain.** Node/npm is not needed to serve or use the browser UI. Node/Rust are build-time prerequisites for Pake only.
6. **Preserve upstream UI behavior.** The native Engine dashboard is embedded where possible instead of maintaining a divergent duplicate.
7. **Discover rather than invent.** Model lists and Engine options are read from the installed Engine CLI/API where supported. Any curated UI hints must be identified as guidance, not authoritative capabilities.
8. **Fail visibly.** Engine unavailability and optional dashboard absence must be reported rather than hidden behind fake values.
9. **PWA cache is conservative.** Cache only the app shell; never cache inference, status, models, chat or live dashboard API responses.
10. **Pake is a wrapper, not a supervisor.** The first Pake iteration opens an already running bridge. Service lifecycle management is a separate future design.
11. **Stage before upstream.** LEONES remains the development/staging record until the transfer is reviewed and validated.
12. **Document evidence honestly.** Source tests, CI, target-machine runtime tests and release acceptance are distinct evidence levels.

## 4. Architecture

### 4.1 Logical component diagram

```text
Desktop browser / mobile browser / installed PWA
                     |
                     | HTTP, same origin
                     v
        TensorFold Web frontend (HTML/CSS/JS)
                     |
                     v
       Python standard-library HTTP bridge
             127.0.0.1:8787 (default)
              |                  |
              | static files     | selected API proxy
              |                  v
              |           TensorFold Engine
              |           127.0.0.1:8080
              |           health / models / chat
              |           optional stats/dashboard
              |
              +---- optional local process manager
                    launches only a process explicitly
                    started and tracked by this UI

Pake desktop package:
  Native WebView -> http://127.0.0.1:<bridge-port>/
  It does not contain the Engine or model weights.
```

### 4.2 Responsibilities

| Component | Responsibility | Deliberately does not do |
|---|---|---|
| Frontend | Chat UI, model picker, navigation, settings, local workspace and status presentation | Inference, scheduler or metric calculation |
| Python bridge | Static HTTP serving, API forwarding, SSE streaming and optional managed-process endpoints | Model loading or inference |
| TensorFold Engine | Model execution, API responses, native dashboard and performance metrics | Web UI packaging |
| PWA layer | Install metadata and cache of static shell | Offline inference or cached live data |
| Pake | Native desktop WebView shell around the local URL | Install/start/stop Engine or Python bridge |
| LEONES docs/tests | Staging record, test evidence and transfer criteria | Claim upstream acceptance |

### 4.3 Why same-origin proxying is used

The browser talks to the bridge, and the bridge talks to the Engine. This avoids requiring browser CORS changes in the Engine and gives the UI one local origin for static content and API calls. It also means the bridge is a security boundary and must remain loopback-only until authentication, origin validation, CSRF protections and a production threat model are designed.

The bridge currently maps selected routes:

| Web route | Engine route | Method |
|---|---|---|
| `/api/health` | `/health` | GET / HEAD |
| `/api/stats` | `/stats` | GET / HEAD |
| `/api/dashboard` | `/dashboard` | GET / HEAD |
| `/api/v1/models` | `/v1/models` | GET / HEAD |
| `/api/v1/chat/completions` | `/v1/chat/completions` | POST, streamed |

The bridge preserves query strings for proxied GET/HEAD requests. This is needed for dashboard polling when the Engine dashboard uses query parameters. The actual embedded dashboard's relative/absolute asset and polling paths must still be verified against the exact Engine build; source-level proxy tests alone do not prove every browser request made by the native dashboard is routed correctly.

Additional local management endpoints are implemented under `/api/engine/*`:
- `GET /api/engine/status`: reports only the process tracked by this bridge instance.
- `GET /api/engine/log`: returns a bounded tail of the managed process log.
- `POST /api/engine/inspect`: executes the selected CLI's `capabilities --json` and `serve --help`.
- `POST /api/engine/start`: launches the selected binary using an argument array, not a shell command.
- `POST /api/engine/stop`: terminates only the process stored by this bridge instance, with a kill fallback after timeout.

The process manager is optional and must not be confused with control of an Engine started outside this bridge.

## 5. Technologies and rationale

### Runtime technologies

- **HTML5:** simple document structure and semantic controls.
- **CSS:** responsive layout, dark visual presentation and mobile adaptation without a framework.
- **Browser JavaScript:** UI state, fetch requests, SSE parsing and local workspace behavior.
- **Python 3.10+:** standard-library HTTP server, HTTP client, JSON parsing, filesystem path checks, subprocess management and threading.
- **TensorFold HTTP API:** health, model discovery, chat completions, optional statistics and native dashboard.
- **Server-Sent Events:** progressive chat completion output.
- **Web App Manifest:** browser-installable app metadata.
- **Service Worker / Cache API:** conservative static-shell caching.
- **SVG:** local scalable PWA icon.
- **Pake CLI / native WebView toolchain:** experimental desktop packaging.
- **GitHub Actions:** Python-version test matrix, shell syntax and JSON validation.

### Why no frontend framework

A framework would add a build system, dependency graph and update surface without being necessary for the current interface. Plain HTML/CSS/JS keeps the browser artifact directly inspectable and reduces the number of runtime dependencies. This is a deliberate simplicity trade-off, not a claim that a framework is inherently unsuitable.

### Why Python standard library

The bridge needs only HTTP serving, HTTP forwarding, JSON, filesystem safety and process management. Python's standard library is sufficient for this prototype and avoids pip dependencies. Python remains a runtime requirement for the bridge; the goal is not a single statically linked binary at this stage.

### Why Pake

Pake provides a native desktop shell around a web URL. It is used to reuse the same UI rather than create a separate desktop frontend. The trade-off is that the first package depends on a separately running local bridge and the host's WebView runtime/toolchain. Pake is not a substitute for a service supervisor or a fully self-contained TensorFold installer.

### PWA and Pake are complementary

PWA targets browser installation and mobile/desktop browser environments. Pake targets a native desktop window. Both use the same bridge origin and frontend. Neither packages the Engine or model weights.

## 6. PWA behavior and offline contract

The manifest declares the app identity, start URL, standalone display mode, theme/background and SVG icon.

The service worker:
- pre-caches the application shell;
- replaces old TensorFold Web shell cache versions;
- may serve the cached shell when navigation is offline;
- bypasses all `/api/*` requests;
- does not cache chat, model discovery, health, statistics, dashboard data or Engine process control.

Therefore offline means **the shell may open**, not that chat or inference works. Live features require the bridge and Engine to be reachable.

PWA acceptance still requires browser installation checks on desktop and mobile, update behavior checks, and confirmation that the service worker never intercepts live API requests.

## 7. Pake desktop packaging contract

### Target

Default URL: `http://127.0.0.1:8787/`.

For safe parallel testing where an older bridge already occupies 8787, the build script accepts a loopback override:

```bash
TENSORFOLD_WEB_PORT=8789 bash ./run-tensorfold-web.sh
TENSORFOLD_WEB_URL=http://127.0.0.1:8789/ bash ./build-pake.sh
```

The build script rejects non-loopback URLs and writes a generated Pake configuration into the build output directory. The checked-in config is the default template.

### Build-time requirements

- Pake CLI installed separately.
- Node.js and Rust versions meeting the Pake CLI's documented requirements.
- Ubuntu WebKitGTK/Tauri development libraries and system build tools.
- Native Windows/macOS toolchains for those platforms.

The exact prerequisites and supported artifact targets must be rechecked against the selected Pake CLI release when packaging. A CI syntax check does not prove the native linker or WebView environment is correctly installed.

### Lifecycle compromise

First iteration:
1. User starts Engine independently.
2. User starts the bridge independently.
3. Pake opens the local bridge URL.
4. Closing Pake closes only the window; it does not stop the bridge or Engine.

This is intentional: it avoids killing user-owned processes or assuming that Pake owns a pre-existing service. A future one-click launcher may start a bridge and optionally an Engine process it created, but it must track exact PIDs/process groups, handle crashes, avoid port collisions, and never kill unrelated processes.

### Not bundled

The Pake desktop package does not include:
- TensorFold Engine binary;
- model files or model cache;
- Python runtime or bridge service installer;
- CUDA/Metal/driver stack;
- a background service supervisor.

## 8. Security model and known risks

This is a local prototype, not a hardened remote service.

### Existing mitigations

- Default bind is loopback.
- Static file resolution is constrained to the configured web root; path traversal is rejected.
- Request body sizes are bounded (chat body up to 8 MiB; JSON management body up to 1 MiB).
- Engine process-control POST endpoints check that the client address is loopback.
- Managed CLI processes are launched with an argument array and not via shell interpolation.
- Process inspection uses timeouts.
- Static responses include `X-Content-Type-Options: nosniff`.
- API responses are marked `no-store`.
- The service worker does not cache API routes.

### Outstanding security work

- No user authentication or authorization.
- No TLS termination.
- No multi-user isolation.
- No formal CSRF/origin policy for local process-control endpoints.
- No CSP/security-header policy reviewed against the embedded dashboard.
- No rate limiting or per-client quotas.
- No comprehensive audit trail for process-control actions.
- No formal threat model for malicious websites attempting to contact localhost services.
- The Engine URL is a bridge configuration setting; deployments must avoid forwarding credentials or secrets into logs.
- Local browser storage is not an encrypted secret store.

**Rule:** do not bind this prototype to `0.0.0.0`, expose it through a reverse proxy, or make it internet-accessible without a separate security design and review.

## 9. Data handling and persistence

- Chat conversations are currently held in browser memory and are not persisted as a server-side history.
- Bots, projects, settings and activity are stored in browser `localStorage` as local UI state.
- Bot instructions and project context are added to the next chat as a system message.
- No cloud account or remote database is introduced by this prototype.
- The Engine remains the source of truth for model names, health and runtime statistics.
- The bridge writes managed Engine stdout/stderr to `~/.local/state/tensorfold-web/engine.log`; the log endpoint returns a bounded tail.
- Users should not store API keys, credentials or sensitive material in localStorage or logs.

## 10. Compatibility and API behavior

The current chat path is OpenAI-compatible `/v1/chat/completions` and the frontend handles streamed `choices[0].delta.content` text.

Not implemented in this iteration:
- general tool/function-call orchestration;
- multimodal image/audio/video payload handling;
- all possible provider-specific SSE event formats;
- guaranteed structured-output compatibility;
- every OpenAI-compatible extension or vendor-specific parameter.

The native dashboard and `/stats` are optional Engine routes and may return 404 unless the Engine is launched with `--dashboard`. The UI must explain this condition. Dashboard metric schemas may vary across versions; optional/missing values must not be filled with fabricated values.

Engine CLI options are inspected from the installed executable using `capabilities --json` and `serve --help`. The UI may provide curated guidance for common options, but the executable's actual output is authoritative. A future release should preserve raw capability data, version it and test against multiple Engine versions.

## 11. Test strategy and evidence levels

Four evidence levels must remain separate:

1. **Static/source checks:** Python compilation, shell syntax, JSON parsing, unit/integration tests.
2. **CI checks:** repeatable GitHub Actions matrix on Python 3.10, 3.12 and 3.14.
3. **Target workstation checks:** actual Ubuntu bridge, TensorFold Engine, browser, chat stream, dashboard and Pake package.
4. **Release/transfer acceptance:** review by upstream maintainers, supported platform build matrix, security review and documented release artifacts.

### Current automated coverage

The standard-library tests cover static serving, index/query handling, MIME types, GET/HEAD, missing files, encoded traversal rejection, health/stats/model proxying, SSE forwarding, unavailable/unknown routes, dashboard forwarding, PWA assets and Pake config invariants.

CI additionally:
- compiles the bridge and tests;
- validates Pake shell script syntax;
- parses the Pake and PWA JSON files;
- runs tests on Python 3.10, 3.12 and 3.14.

The CI matrix for the current staging head passed on all three Python versions. This establishes source-level regression status, not runtime success on the target workstation.

### Target workstation test checklist

- [ ] Fetch current branch in the LEONES worktree.
- [ ] Run `py_compile` and the complete unittest suite.
- [ ] Validate shell syntax and both JSON manifests/config.
- [ ] Start an isolated bridge on port 8789; leave any existing 8787 service alone.
- [ ] Confirm root page and static assets load.
- [ ] Confirm Engine health and model discovery.
- [ ] Submit a chat request and observe progressive SSE output.
- [ ] Confirm Engine unavailability is displayed cleanly.
- [ ] If Engine is deliberately launched with `--dashboard`, verify iframe HTML, CSS/JS assets and every polling request in browser devtools.
- [ ] Install PWA and verify shell cache/API bypass.
- [ ] Build Pake on Ubuntu; record CLI, Node, Rust and WebKitGTK versions and artifact names.
- [ ] Open the packaged app and verify bridge connectivity, chat and dashboard.
- [ ] Close Pake and confirm the bridge and Engine remain running.
- [ ] Test window resize, keyboard navigation, focus and mobile layout.
- [ ] Record logs and evidence in `PAKE-VALIDATION.md`.

## 12. Development history and decision log

### Stage A — local prototype and API bridge

A local web UI was developed separately from the Engine. The first integration issue was API route handling: the bridge must expose explicit `/api/*` routes rather than assume the Engine is a static file server. The chat route must forward request bodies and preserve streaming instead of buffering the entire completion.

### Stage B — LEONES staging

The implementation was staged in `robertosantosx2/LEONES` on `feat/tensorfold-web-standalone`. The branch and PR are intended as a traceable development record, not an upstream release claim.

### Stage C — automated bridge tests

The standard-library suite was expanded to exercise HTTP behavior and proxy behavior without requiring a live inference model. The CI matrix uses Python 3.10, 3.12 and 3.14. This improves reproducibility but cannot replace a live Engine/browser test.

### Stage D — native dashboard reuse

The Dashboard view was changed to embed TensorFold Engine's original `/dashboard` page and the bridge gained a `/api/dashboard` proxy. Query strings are preserved on the proxy path to support polling. The reason is to avoid a second dashboard implementation that could drift from upstream metrics and visual semantics.

Remaining proof: inspect all native dashboard asset/polling URLs in the target Engine version and validate the embedded page in a real browser.

### Stage E — PWA

A manifest, SVG icon and service worker were added. The service worker's intentionally narrow cache policy prevents stale health, model, chat or dashboard data from being presented as live.

### Stage F — Pake

A Pake config and build script were added. The default target is the local bridge, not the raw static folder. A loopback-only URL override supports safe tests on port 8789 without disturbing an existing bridge on 8787. Pake does not own Engine or bridge lifecycle in this iteration.

### Current state

- Code and detailed documentation are staged in LEONES.
- Automated CI passes for Python 3.10, 3.12 and 3.14.
- Pake configuration and build script are present.
- A native Pake package has **not** yet been built and run on the target Ubuntu workstation.
- Native dashboard browser polling/asset behavior still needs live verification.
- Upstream TensorFold transfer has not been accepted or merged.

## 13. Known compromises and technical debt

| Area | Current compromise | Follow-up |
|---|---|---|
| Frontend architecture | Plain JS, no component framework | Keep modules manageable; consider framework only if complexity justifies build tooling |
| Bridge runtime | Python interpreter required | Optional self-contained packaging only after requirements are stable |
| Desktop | Pake wraps an already running local URL | Design a safe launcher/supervisor separately |
| Engine lifecycle | Existing processes are not adopted | Track only processes created by this bridge |
| Dashboard | Native iframe reused | Verify every relative/absolute asset and polling URL against Engine versions |
| Stats compatibility | Raw JSON/native dashboard | Version schema or capability-detect fields before custom visualizations |
| Chat | Text-only OpenAI SSE subset | Tool calls, multimodal and provider-specific events later |
| Persistence | Chat is volatile; workspace uses localStorage | User-controlled export/import; secure handling for sensitive data |
| Security | Loopback prototype | Origin/CSRF policy, CSP, auth, TLS and threat model before network exposure |
| PWA | Shell-only offline cache | Test cache updates and browser-specific install behavior |
| Pake platform support | Ubuntu first | Native Windows/macOS builds and runtime checks |
| Branding | SVG fallback; official logo binary not yet vendored | Add authorized local asset and license/provenance record |
| Accessibility | Responsive layout exists | Keyboard, screen-reader, contrast and reduced-motion audit |
| Release | No signed installers or auto-update | Signing, provenance, checksums and update policy |

## 14. Transfer plan to upstream TensorFold

The upstream target is `ashhart/TensorFold`. The first upstream contribution should be a focused issue describing the proposal and linking this LEONES PR. It should ask maintainers to agree on:
- the appropriate repository path (for example a web UI subproject);
- whether the Python bridge is acceptable or should be replaced/embedded;
- whether the native dashboard iframe/proxy strategy matches upstream expectations;
- the security boundary for localhost process control;
- Pake as an optional desktop packaging target;
- PWA support and static hosting expectations;
- version compatibility and API contracts;
- CI ownership and supported platforms.

After maintainers respond:
1. Rebase/port the reviewed source into an upstream feature branch.
2. Preserve LEONES history and test evidence in the transfer notes.
3. Adapt naming, versioning, code style and licenses to upstream conventions.
4. Run upstream CI and add integration tests against supported Engine versions.
5. Verify dashboard requests and Pake builds on actual supported systems.
6. Address security review before any remote-access claim.
7. Submit a separate upstream PR; do not assume the LEONES PR itself can be merged across repositories.

## 15. Release acceptance gates

A release candidate is not ready until all of these gates pass:

- **G1 — Source:** clean Python compilation, tests and shell/JSON validation.
- **G2 — Engine integration:** real health, models, streamed chat and clear unavailable state.
- **G3 — Dashboard:** real native dashboard page, static resources and polling verified in browser.
- **G4 — PWA:** installability and shell-only offline behavior verified.
- **G5 — Pake:** native Ubuntu package built and runtime tested; no unwanted service shutdown.
- **G6 — Security:** loopback-only deployment documented; process-control and browser-origin risks reviewed.
- **G7 — Accessibility:** keyboard, focus, contrast and mobile checks completed.
- **G8 — Cross-platform:** Windows/macOS native builds completed before claiming support.
- **G9 — Upstream:** maintainers approve architecture and a separate upstream PR is reviewed.
- **G10 — Distribution:** checksums, licenses, release notes and artifact provenance recorded.

## 16. References

- TensorFold repository: https://github.com/ashhart/TensorFold
- TensorFold API documentation: https://github.com/ashhart/TensorFold/blob/main/docs/api.md
- TensorFold status route implementation: https://github.com/ashhart/TensorFold/blob/main/zig/src/server/status_routes.zig
- TensorFold live status fields: https://github.com/ashhart/TensorFold/blob/main/zig/src/server/live.zig
- Pake CLI getting started: https://pake.run/docs/cli/getting-started
- Pake CLI options: https://pake.run/docs/cli/options
- Pake CLI advanced usage: https://pake.run/docs/cli/advanced
- Pake source: https://github.com/tw93/Pake
- LEONES staging PR: https://github.com/robertosantosx2/LEONES/pull/138
