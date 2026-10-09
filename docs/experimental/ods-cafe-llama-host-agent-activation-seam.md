# cafe-llama host-agent activation seam

**Workstream:** LEONES → ODS  
**Branch:** `ods-cafe-llama-icd-dashboard`  
**Reviewed:** 2026-10-09  
**Status:** Pinned cafe artifact image builds successfully in CI and its SHA-256 is verified; host-agent activation, GPU inference, and rollback remain unverified.

## Verified staging status

Workflow run [37906555180](https://github.com/robertosantosx2/LEONES/actions/runs/37906555180) completed successfully at commit `e082bd8c18a66ed59ee7112afab2af2bd938585e`. All three jobs passed:

- `backend-contracts`: staged adapter/backend contracts passed against an ephemeral checkout of current `Osmantic/ODS` main.
- `dashboard-contracts`: staged ICD panel tests and dashboard build passed.
- `cafe-artifact-contract`: artifact patcher and contract tests passed, and the patched pinned image built on a GitHub-hosted Linux runner.

The artifact job downloaded the official release asset and verified its bytes with `sha256sum -c -` successfully. The image's ELF architecture and shared-library dependencies were inspected. As expected on a runner without an NVIDIA driver, `libcuda.so.1` was unresolved at image-build time; all other inspected dependencies resolved. This is the driver library expected to be injected by the NVIDIA container runtime on a compatible host. The workflow deliberately does not claim that `llama-server --version` or inference works without that driver.

Earlier build failures exposed Dockerfile LABEL continuation syntax, incorrect ZIP-vs-gzip detection, the shared-library search path, a missing CUDA runtime (`libcudart.so.12`), and a missing OpenMP runtime (`libgomp.so.1`). Those build blockers are resolved in the successful run.

**What is now verified:** pinned release download, SHA-256 match, image build, expected x86-64 ELF architecture, resolution of non-driver shared dependencies, image provenance labels, staged backend contracts, and dashboard contracts.

**What is not verified:** starting the container with an actual NVIDIA driver/GPU, `llama-server --version` on that host, model-list/health endpoints, a real bounded model completion, host-agent activation, or rollback against a running ODS installation. CI does not activate cafe on a live ODS host and is not a GPU runtime test.

## Current ODS lifecycle seams reviewed

The current `main` host agent has a single model activation transaction in `ods/bin/ods-host-agent.py`, the existing readiness helper `_wait_for_model_readiness`, and the existing Compose restart helper `_compose_restart_llama_server`. The existing runtime endpoint resolver is `_runtime_endpoint(env)`.

The staged `CafeLlamaAdapter` deliberately does not select itself. The LEONES overlay wires explicit `ODS_INFERENCE_RUNTIME=cafe-llama` selection into the host-agent transaction, compiles against current ODS main, and adds a candidate-stop/stock-runtime restore branch. This remains a staged overlay: CI does not run Docker, activate the service, or prove rollback against a live ODS host.

## Pinned release artifact

The candidate is pinned to the official cafe-llama.cpp 0.75 Linux x64 CUDA 12.4 release asset:

- Asset: `llama-0.75-bin-linux-cuda-12.4-x64.tar.gz`
- Release: [quimmedes/cafe-llama.cpp 0.75](https://github.com/quimmedes/cafe-llama.cpp/releases/tag/0.75)
- Asset URL: `https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-0.75-bin-linux-cuda-12.4-x64.tar.gz`
- SHA-256 pinned from GitHub release asset metadata: `536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c`
- Build ID: `cafe-llama-0.75-linux-x64-cuda12.4`
- Architecture/backend labels: `linux-x64` / `cuda-12.4`

The Dockerfile checks the downloaded bytes with `sha256sum -c -` and labels the image with the declared build ID, digest, architecture, and backend. In workflow run [37906555180](https://github.com/robertosantosx2/LEONES/actions/runs/37906555180), the asset was fetched and the SHA-256 check passed, and the image built successfully. The digest originates from GitHub release asset metadata; the CI run confirms that the downloaded bytes match that pinned value. Any URL override must be paired with the SHA-256 of that exact asset and matching identity metadata.


## Isolated GPU runtime smoke test

The script `integrations/ods-icd-staging/scripts/smoke_test_cafe_runtime.sh` is now staged for the next hardware-enabled validation. It checks the pinned image labels, starts a **separate** Docker container with `--gpus all`, requests up to 999 GPU layers by default, then tests `/health`, `/v1/models`, and a bounded `/v1/chat/completions` request. It removes its temporary container on exit and does not modify ODS `.env`, Compose services, or the active `llama-server`.

After the hardened image has been built locally as `ods-cafe-llama:local`, run from the LEONES repository root, replacing the model path if needed:

```bash
bash integrations/ods-icd-staging/scripts/smoke_test_cafe_runtime.sh "$HOME/ods/data/models/Qwen3.5-2B-Q4_K_M.gguf"
```

Optional environment overrides: `CAFE_SMOKE_PORT` (default `18081`), `CAFE_SMOKE_TIMEOUT_SECONDS` (default `240`), `CAFE_SMOKE_IMAGE` (default `ods-cafe-llama:local`), and `CAFE_SMOKE_EXTRA_ARGS` (default `-ngl 999`). The script requires Docker, `curl`, `python3`, a working NVIDIA driver, and Docker's NVIDIA GPU support. **This script has been staged and its shell syntax is checked in CI; it has not been run against a physical NVIDIA GPU.** A passing result would validate the isolated runtime only, not ODS host-agent activation or rollback.

## Required implementation sequence

1. **Resolve the selector before mutations.** Absent selector means existing `llama-server`. Accept `cafe-llama` only for the first supported platform: native Linux + host-managed Compose. Reject WSL/router, Apple, and container-host-agent modes until each has a separately tested implementation.
2. **Validate pinned provenance.** Require non-empty expected build ID, a 64-character lowercase SHA-256, architecture, and backend. Inspect the built image's labels; do not trust environment values as proof of image identity.
3. **Build before starting.** Build only the allowlisted `cafe-llama` image, inspect its labels, and refuse to start it if the artifact identity does not match the expected profile. Do not use a combined Compose build-and-start operation that bypasses this check.
4. **Resolve the correct endpoint.** For host-native Linux, use `127.0.0.1:${EXT_CAFE_LLAMA_PORT:-8081}`. Do not send cafe requests through the existing router transport by accident. Preserve the current port-8080 endpoint for the default runtime.
5. **Verify the actual running container.** Inspect `ods-cafe-llama`, require it to be running, compare its image ID with the inspected image, and compare build ID / artifact SHA-256 labels with the pinned profile.
6. **Run readiness and a real completion.** Check health, model listing, expected model identity, context capacity where supported, and a bounded completion. Publish the cafe route only after all checks pass.
7. **Rollback explicitly.** Snapshot the old provider/configuration before changes. If env persistence, service startup, readiness, identity, or completion fails, do not publish cafe as active; restore the prior selection and route. A cafe failure must never silently count as success or switch providers behind the user's back.
8. **Expose provenance.** Status and benchmark receipts should identify runtime kind, build ID, artifact digest, model, context, and resolved inference options.

## Acceptance tests before claiming activation

- Missing selector and explicit `llama-server` preserve the current behavior and do not start cafe.
- Invalid selector, missing extension, missing digest, mismatched labels, wrong image ID, unsupported platform, and incompatible model fail before route publication.
- Cafe startup uses only the cafe Compose service.
- Failed service start, health, model-list, context, or completion triggers rollback and leaves the previous provider usable where possible.
- A successful activation proves the running container's provenance and routes an actual completion through the cafe endpoint.
- Switching back to `llama-server` works and does not leave a stale cafe route.
- Run tests against the real ODS host-agent transaction and schema, not only the staged adapter.

## Status language

Until a real image build, runtime activation, readiness, bounded completion, and forced rollback/switch-back smoke test pass, describe this work as **staged contract + pinned artifact metadata + activation design**, not as a completed cafe-llama integration.
