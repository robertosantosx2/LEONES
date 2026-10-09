# cafe-llama host-agent activation seam

**Workstream:** LEONES → ODS  
**Branch:** `ods-cafe-llama-icd-dashboard`  
**Reviewed:** 2026-10-09  
**Status:** Host-agent activation overlay staged and contract-tested; real runtime activation remains unverified.

## Verified staging status

Workflow run [37903835557](https://github.com/robertosantosx2/LEONES/actions/runs/37903835557) completed successfully for all three jobs, including static safety contracts for opt-in selection, build-before-start provenance checks, and rollback ordering:

- `cafe-artifact-contract`: the hardening patcher and artifact contract tests pass against an ephemeral checkout of `robertosantosx2/ODS` branch `feat/cafe-llama-runtime-improvements`.
- `backend-contracts`: staged adapter/backend contract tests pass against an ephemeral ODS checkout.
- `dashboard-contracts`: staged ICD panel tests and dashboard build pass.

These jobs do not modify the ODS branch, build the cafe image, or activate a running runtime.

## Current ODS lifecycle seams reviewed

The current `main` host agent has a single model activation transaction in `ods/bin/ods-host-agent.py`, the existing readiness helper `_wait_for_model_readiness`, and the existing Compose restart helper `_compose_restart_llama_server`. The existing runtime endpoint resolver is `_runtime_endpoint(env)`.

The staged `CafeLlamaAdapter` deliberately does not select itself. The LEONES overlay now wires explicit `ODS_INFERENCE_RUNTIME=cafe-llama` selection into the host-agent transaction, compiles against current ODS main, and adds a candidate-stop/stock-runtime restore branch. This remains a staged overlay: CI does not run Docker, activate the service, or prove rollback against a live ODS host.

## Required implementation sequence

1. **Resolve the selector before mutations.** Absent selector means existing `llama-server`. Accept `cafe-llama` only for the first supported platform: native Linux + host-managed Compose. Reject WSL/router, Apple, and container-host-agent modes until each has a separately tested implementation.
2. **Validate pinned provenance.** Require non-empty expected build ID, a 64-character lowercase SHA-256, architecture, and backend. Inspect the built image's labels; do not trust environment values as proof of image identity.
3. **Add a dedicated Compose lifecycle helper.** Start/recreate only the allowlisted `cafe-llama` service. If Compose flags or service configuration are missing, fail closed; never fall back to recreating stock `llama-server`.
4. **Resolve the correct endpoint.** For host-native Linux, use `127.0.0.1:${EXT_CAFE_LLAMA_PORT:-8081}`. Do not send cafe requests through the existing router transport by accident. Preserve the current port-8080 endpoint for the default runtime.
5. **Verify the actual running container.** Inspect `ods-cafe-llama`, require it to be running, compare its image ID with the inspected image, and compare build ID / artifact SHA-256 labels with the pinned profile.
6. **Run readiness and a real completion.** Check health, model listing, expected model identity, context capacity where supported, and a bounded completion. Publish the cafe route only after all checks pass.
7. **Rollback explicitly.** Snapshot the old provider/configuration before changes. If env persistence, service startup, readiness, identity, or completion fails, do not publish cafe as active; restore the prior selection and route. A cafe failure must never silently count as success or switch providers behind the user's back.
8. **Expose provenance.** Status and benchmark receipts should identify runtime kind, build ID, artifact digest, model, context, and resolved inference options.

## Artifact blocker

The staged Dockerfile hardening intentionally fails the build if `CAFE_LLAMA_RELEASE_SHA256` is empty. The digest has not yet been independently obtained and verified for the exact release asset. Do not fill it with a guessed value. Until it is pinned, a reproducible trusted image build cannot pass.

The current Docker Compose defaults identify a Linux x64 CUDA 12.4 asset; the build ID, architecture, backend, URL and digest must describe the same exact artifact. Changing the URL without updating the identity metadata must be rejected.

## Acceptance tests before claiming activation

- Missing selector and explicit `llama-server` preserve the current behavior and do not start cafe.
- Invalid selector, missing extension, missing digest, mismatched labels, wrong image ID, unsupported platform, and incompatible model fail before route publication.
- Cafe startup uses only the cafe Compose service.
- Failed service start, health, model-list, context, or completion triggers rollback and leaves the previous provider usable where possible.
- A successful activation proves the running container's provenance and routes an actual completion through the cafe endpoint.
- Switching back to `llama-server` works and does not leave a stale cafe route.
- Run tests against the real ODS host-agent transaction and schema, not only the staged adapter.

## Status language

Until those tests and a real image/runtime smoke test pass, describe this work as **staged contract + artifact hardening + activation design**, not as a completed cafe-llama integration.
