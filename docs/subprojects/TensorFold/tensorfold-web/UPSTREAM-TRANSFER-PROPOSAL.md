# Upstream proposal — TensorFold Web

**Target:** [ashhart/TensorFold](https://github.com/ashhart/TensorFold)  
**Staging implementation:** [LEONES PR #138](https://github.com/robertosantosx2/LEONES/pull/138)  
**Purpose:** obtain maintainer feedback on architecture before porting code upstream.

## Proposal

TensorFold Web is a local-first browser/PWA interface and optional Pake desktop shell for TensorFold Engine. It provides chat using the Engine's OpenAI-compatible `/v1/chat/completions` API with SSE streaming, dynamic model discovery, health/status views, reuse of the native `/dashboard` page, and an optional local Engine process manager.

The implementation is staged in LEONES to make the architecture and test evidence reviewable before an upstream code PR is proposed. The LEONES merge is only a staging-repository merge; it does not imply acceptance by TensorFold maintainers.

## Architecture

- Plain HTML, CSS and browser JavaScript for the frontend.
- Python 3.10+ standard-library HTTP bridge for static serving, same-origin API proxying, SSE forwarding and optional process management.
- TensorFold Engine remains responsible for inference, models, scheduler and metrics.
- PWA manifest and service worker cache only the static shell; live API routes are never cached.
- Pake optionally wraps the local bridge URL in a native WebView. It does not bundle or supervise the Engine or bridge in the first iteration.

## Constraints and security boundary

- Loopback-only default. Not suitable for LAN/public exposure without authentication, TLS, origin/CSRF protections and security review.
- No Engine/model/CUDA/Metal bundling.
- No chat history persistence on a server; local workspace state uses browser localStorage.
- Chat currently supports text in OpenAI-style SSE deltas; tool calls and multimodal payloads are not implemented.
- Native dashboard and stats routes are optional and may require Engine `--dashboard`.
- Pake native build and target Ubuntu runtime test remain pending; Windows/macOS builds are not claimed.

## Automated validation

The LEONES staging CI passes the Python 3.10, 3.12 and 3.14 matrix, Python compilation, standard-library integration tests, shell syntax and PWA/Pake JSON validation. These checks are not a substitute for live browser-to-Engine, dashboard polling, PWA install and Pake runtime tests on supported systems.

## Questions for maintainers

1. Should this live in the main repository (for example `web/` or `tools/tensorfold-web/`) or in a separate repository?
2. Is a Python standard-library bridge acceptable, or should the UI integrate into an existing server route?
3. Is embedding the native dashboard preferred to duplicating its visualization?
4. What security requirements apply to localhost process-control endpoints and browser-origin handling?
5. Are PWA and Pake welcome as optional distribution targets?
6. Which Engine versions and API contracts should be supported?
7. Which CI platforms and package artifacts are acceptable?

## Links

- Staging PR: https://github.com/robertosantosx2/LEONES/pull/138
- Full engineering record: [ARCHITECTURE-AND-ENGINEERING-RECORD.md](ARCHITECTURE-AND-ENGINEERING-RECORD.md)
- Pake validation log: [PAKE-VALIDATION.md](PAKE-VALIDATION.md)
