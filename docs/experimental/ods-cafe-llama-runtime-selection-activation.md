# cafe-llama.cpp runtime selection and activation decision

**Workstream:** LEONES → ODS  
**Branch:** `ods-cafe-llama-icd-dashboard`  
**Date:** 2026-10-09  
**Status:** Decision contract / implementation gate — not a claim of production completion

## Decision

Treat cafe-llama.cpp as a distinct, opt-in runtime provider that exposes the llama.cpp-compatible server API. Do not infer its identity from the model name, GPU backend, generic `llama-server` binary name, or the presence of the optional extension alone.

The default remains the existing ODS `llama-server` runtime unless an explicit runtime selection is persisted and validated.

### 1. Runtime identity and selection

The runtime registry/profile must distinguish at least:

- `id: llama-server` — existing ODS baseline; default.
- `id: cafe-llama` — optional advanced provider; only eligible when its extension/build is installed and its capabilities are declared.
- A runtime implementation/build identity (source/release, version or digest), API compatibility, supported hardware backend, and supported capability set.

The model compatibility profile remains the authority for model/hardware compatibility. ICD is a second stage: it may propose concrete configurations only after a compatible runtime profile has been selected. A generic profile such as `backend: nvidia` must never be relabelled as cafe-llama.

Selection precedence:

1. An explicit, persisted per-model/per-profile runtime selection, if it passes compatibility and availability checks.
2. Otherwise the configured global runtime selection, if explicitly set and valid.
3. Otherwise the current ODS baseline `llama-server`.

Do not silently auto-switch to cafe-llama because it is installed, and do not silently fall back after an explicit cafe selection. Report an actionable error if the requested provider is unavailable or incompatible. An operator may explicitly return to `llama-server`.

Suggested canonical setting: `ODS_INFERENCE_RUNTIME=llama-server|cafe-llama`, default `llama-server`. This is a selection key, not a substitute for a resolved profile. If ODS already has a canonical runtime/provider selector, reuse it rather than creating a competing setting.

Persist the resolved runtime ID and build identity alongside the selected model/configuration. Include them in status output and benchmark receipts.

### 2. Activation without changing the default path

The cafe service is a separate optional process and endpoint (currently staged as port 8081); its presence must not replace, shadow, or mutate the existing `llama-server` service (port 8080).

Runtime activation must go through the existing ODS model activation / Model Switchboard / host-agent lifecycle path. At the point ODS resolves the selected runtime, the existing provider routing target must resolve to the selected provider's API endpoint. Do not make clients choose between unrelated APIs, and do not write `.env` directly from a Dashboard router.

For the default value or an absent selector:

- keep `LLM_BACKEND=llama-server` and the current `LLM_API_URL=http://llama-server:8080` behavior unchanged;
- do not start or recreate cafe-llama as a side effect;
- preserve existing health checks, startup order, model switching, and rollback behavior.

For an explicit cafe selection:

1. Confirm the extension is installed/enabled and its binary identifies itself as a cafe-capable build.
2. Validate the selected model path, model format, hardware backend, and requested flags against the build's declared capabilities.
3. Prepare the environment using ODS's existing host-agent environment merge/persistence mechanism.
4. Start or recreate only the allowlisted cafe service through the existing lifecycle mechanism.
5. Wait for readiness and verify `/health` plus `/v1/models` (or the exact endpoints supported by the build).
6. Only after readiness succeeds, switch the resolved provider target to the cafe endpoint and mark the selection active.
7. On failure, do not claim activation; keep the prior provider active where safe, report the failed phase, and retain enough state for explicit retry/rollback.

The switch must be atomic from the consumer's perspective: do not publish the cafe target before it is healthy. The exact ODS provider-resolution seam must be identified from current `main` before implementation; do not assume changing `LLM_API_URL` alone is sufficient.

### 3. Environment and argument contract

Use canonical ODS env keys that already exist in `.env.example` / schema. The staged mapping reviewed so far includes:

| ICD dimension | ODS key / cafe argument | Gate |
|---|---|---|
| Context | `CTX_SIZE` | Do not use the mismatched `MAX_CONTEXT` key |
| GPU layers | `N_GPU_LAYERS` | Verify mapping to `-ngl` in the selected build |
| KV cache K/V | `LLAMA_ARG_CACHE_TYPE_K`, `LLAMA_ARG_CACHE_TYPE_V` | Verify allowed values for this build |
| Flash Attention | `LLAMA_ARG_FLASH_ATTN` | Turbo KV requires compatible FA support |
| Speculation | `LLAMA_ARG_SPEC_TYPE` | Validate supported mode |
| Draft depth | `LLAMA_ARG_SPEC_DRAFT_N_MAX` | Positive only with a supported speculative mode |
| MoE/offload | structured cafe-specific keys | Reject unsupported combinations; do not pass cafe-only flags to stock llama-server |

Avoid using one ambiguous set of cafe-only arguments in the default llama-server path. Either namespace advanced-only keys under `CAFE_LLAMA_*` or ensure the adapter only passes them to a confirmed cafe build. Do not accept arbitrary extra CLI flags from the Dashboard; any escape hatch must be operator-only and explicitly outside the safe configuration editor.

The binary name `llama-server` is not proof of cafe-llama identity. Record build provenance at image/build time and expose a deterministic runtime/build ID to the selector.

### 4. Required ODS-native tests

The LEONES staging tests validate the contract only. ODS implementation is not accepted until tests run against the real ODS app, host-agent callbacks, environment schema, lifecycle, and routing code.

**Selection / recognition**
- Missing selector resolves to the existing baseline.
- Explicit `llama-server` resolves exactly as before.
- Explicit cafe selection resolves only to a registered cafe profile/build.
- Generic hardware profiles do not identify the runtime.
- Missing extension, stock upstream binary, unsupported backend, or incompatible model fails closed.
- Runtime/build identity is returned in status and included in the configuration identity.

**Activation / lifecycle**
- Default startup does not start/recreate cafe or change the existing API URL.
- Explicit cafe selection uses ODS env merge/persistence and the allowlisted lifecycle path.
- Provider routing changes only after readiness checks pass.
- Failed env write, failed service recreation, failed health check, and failed `/v1/models` check never report success.
- No direct router writes to `.env`; no unrestricted service-name input.
- Switching back to llama-server restores the baseline endpoint and behavior.
- Restart/reload preserves the chosen runtime or deterministically resolves the documented default.

**ICD / measurements**
- No compatible selected runtime profile means no candidates.
- Runtime-specific invalid combinations are rejected before process execution.
- Discovery results contain no fabricated performance fields.
- Measurements are tied to the exact runtime/build, `configuration_id`, model identity, and workload.
- Existing non-ICD model ranking/evidence remains unchanged.

**Dashboard / localization**
- Runtime selector shows only installed and compatible providers.
- Pending/unavailable/failed activation is represented honestly.
- Apply/benchmark use existing lifecycle/evidence paths.
- EN/ES/ZH keys are merged into current locale dictionaries without replacing concurrent work.

### 5. Merge and PR gates

Do not open the single upstream PR until all of these are true:

- [ ] The runtime-resolution seam in current ODS `main` is identified and the selection contract is implemented there.
- [ ] Cafe identity is verified from a known build/source, not guessed from a binary name.
- [ ] Default llama-server behavior is regression-tested unchanged.
- [ ] Explicit cafe selection successfully activates and routes through the real ODS lifecycle in integration tests.
- [ ] Env keys are aligned with the current schema; no `MAX_CONTEXT` / `CTX_SIZE` mismatch.
- [ ] ICD focused tests, model-selection regressions, service/compose tests, Dashboard tests/build and relevant full ODS regressions pass.
- [ ] EN/ES/ZH merge preserves concurrent Dashboard/i18n changes.
- [ ] CI for the exact candidate commit is green and recorded.
- [ ] Final diff is reviewed for unintended changes and passes `git diff --check`.
- [ ] One consolidated branch/PR contains the implementation; earlier scaffolding PRs are not submitted as separate upstream PRs.
- [ ] Hardware performance claims remain absent until a controlled target-host benchmark produces MEASURED receipts.

## Current known blockers

1. The staged ICD router can be wired while producing no cafe candidates because the ODS model catalog's hardware profiles do not themselves identify cafe as the active runtime.
2. The current optional extension starts a separate endpoint, but the provider-selection/routing seam that makes ODS clients use that endpoint must be integrated and tested in the actual ODS app.
3. The staged `CTX_SIZE` correction and `N_GPU_LAYERS` mapping require tests against the current ODS environment schema and cafe binary.
4. The latest staged wiring needs a fresh green workflow. The older successful run does not validate newer commits.
5. Dashboard and EN/ES/ZH work must be merged against the current ODS tree, not copied over it.

Until these blockers are cleared, describe the runtime selector/activation as **designed but not production-validated**. Do not mark ICD-06..10 or ICD-14 complete, and do not open the consolidated upstream PR.


## Current ODS tree audit (2026-10-09)

Read-only review of `robertosantosx2/ODS:main` confirms why a Dashboard-only patch cannot finish this integration:

- `ods/.env.example` currently documents `LLM_BACKEND=llama-server` as the local default and lists `llama-server`, `lemonade`, `litellm`, and `external` as backend choices; cafe-llama is not a recognized backend/provider there.
- `ods/.env.example` sets `LLM_API_URL=http://llama-server:8080` for the baseline.
- `ods/docker-compose.base.yml` defines the core `llama-server` service directly and binds its command, model path, port, environment, and health check. The optional cafe extension is a separate service and endpoint.
- `ods/bin/model_switchboard/adapters.py` exposes a `ContainerLlamaAdapter` with `kind = "llama-server"`; that adapter is a model lifecycle seam, not evidence that cafe-llama is registered as a distinct provider.
- The prior optional-extension scaffold uses a binary called `llama-server`. The executable's filename alone cannot distinguish the upstream build from the cafe fork.

Therefore the implementation needs a runtime/provider resolution boundary that is explicit about provider ID and build provenance, and then must connect that provider to the existing model activation and request-routing flow. Merely adding `ODS_INFERENCE_RUNTIME` to `.env`, starting the optional extension, or changing `LLM_API_URL` by itself would be insufficient.

This is a source-tree audit, not a passing integration test. It does not establish the exact final code change or runtime correctness; those require an ODS-native patch and CI.


### Additional Model Switchboard findings

The current ODS source tree also has these concrete integration points:

- `ods/bin/model_switchboard/state.py` constrains `active.backend.kind` to `llama-server`, `lemonade`, `hipfire`, or `unknown`. Cafe needs an explicit, schema-validated identity rather than being misreported as the upstream engine.
- `ods/bin/model_switchboard/adapters.py` defines the runtime adapter protocol and a container adapter whose `kind` is `llama-server`. A cafe adapter/provider must use the same activation proof contract while preserving distinct runtime identity and build provenance.
- `ods/extensions/services/dashboard-api/runtime_projection.py` currently projects active runtime model/context information but does not expose a verified runtime ID/build identity. Status and API schemas need a safe, bounded extension.
- `ods/docker-compose.base.yml` owns the baseline `llama-server` process and its readiness probe. The cafe extension's separate service cannot be made active by registering ICD candidates alone; the selected provider must be represented in the host-authoritative Switchboard state and in request routing.

The implementation plan should therefore touch the Switchboard state/schema and adapter contract, the host-agent lifecycle/route publication, and the Dashboard/API projection as one coordinated change. Keep the default provider path byte-for-byte equivalent where practical, and add migration/defaulting tests for older state records before extending the allowed backend kinds.


### Repository/PR hygiene check (2026-10-09)

The staged-contract workflow now completes successfully at commit `7fbfcfd26193bac7baff0a8c8e6f426dbfbb4dc7`:
https://github.com/robertosantosx2/LEONES/actions/runs/37894384934

A branch audit found the existing fork branch `robertosantosx2/ODS:feat/cafe-llama-icd-runtime-profile` is not a safe upstream PR head: GitHub's compare endpoint reports it as diverged from current `main`, 715 commits ahead and 3 behind (merge base `e3b3c89b40f7bc10e5552c0cb0fd8741ce861bbb`; main `d8b04c7f229116ecc378411210b049c913427857`). Do not open the consolidated PR from that branch or merge it wholesale. Once the implementation is validated in LEONES, port only the reviewed integration commits onto a fresh branch based on the current upstream main.

The fork currently has only closed cafe-related PRs (#1, #2, #3); none is an open consolidated implementation PR. The final delivery should therefore be a new, single PR after the runtime activation gate passes, not a reopening or layering of those earlier scaffolding PRs.


### Activation transaction detail from current host agent

The current `_do_model_activate` transaction writes the selected model and runtime profile into `.env`, then selects a platform restart strategy. On the host-native container path it always calls `_compose_restart_llama_server`; the rollback and container recovery flow is likewise centered on `ods-llama-server`. After proof, the route publisher currently maps only Lemonade versus `llama-server`, and the generated endpoint allowlist contains `llama-server-default` plus an optional `lemonade-default`.

This establishes a specific engineering requirement: cafe selection must be a first-class branch of the activation transaction, not a URL-only switch. The transaction must capture both runtime container states, stop the currently active provider to release GPU memory, start/recreate cafe, prove model identity/context and a real completion, publish `cafe-llama-default` in the endpoint allowlist and active state, then update dependent consumers. Rollback must stop cafe and restore/prove the prior provider and route. Any failed phase must leave the previous verified route active or return an explicit rollback failure.

The existing `ods/extensions/library/services/cafe-llama` on `main` is still a scaffold whose Dockerfile can build without a bundled binary when no release URL is set. The fork branch `feat/cafe-llama-runtime-improvements` contains one commit on top of current `main` that adds a default 0.75 CUDA binary download and flag mapping; its branch compares cleanly to `main` (1 commit ahead, 0 behind). That improvement is a candidate for the final consolidated PR, but the default download should still be reviewed for release integrity and architecture/backend constraints before activation is enabled.

Do not yet change the host-agent transaction by a broad textual rewrite. First extract the current rollback/service-state seams into focused helpers and add deterministic fake-process tests, then wire the cafe path through those helpers. The target acceptance test must assert actual service calls and active `model-state.json` endpoint identity, not only test a pure selector.


## Latest validation and concrete host-agent seam (2026-10-09)

The staged contract workflow has now completed successfully on commit
`bc523244667ddc386ef7a99c33d6b0c1c9050fba`:
[run 37895433020](https://github.com/robertosantosx2/LEONES/actions/runs/37895433020).
Both `backend-contracts` and `dashboard-contracts` are green, including the
runtime-selection contract tests, exact-configuration/workload evidence-store
tests, Dashboard panel tests, and Dashboard production build. This validates
the LEONES staging layer only; it does not test an ODS host-agent activation.

A closer read of current `Osmantic/ODS:main` identifies the exact transaction
seams:

- `ods/bin/ods-host-agent.py::_do_model_activate` resolves the model/profile,
  captures snapshots for `.env`, model-router endpoints and consumers, writes
  the selected model configuration, then stages a runtime.
- The current Linux host-native container path chooses
  `_compose_restart_llama_server`; the in-container path uses
  `_recreate_llama_server`. The Windows, macOS and WSL branches have separate
  ownership/activation paths and must not be redirected to the Linux cafe
  service.
- The existing `ContainerLlamaAdapter` in
  `ods/bin/model_switchboard/adapters.py` already provides the stage,
  identity-verification and completion-verification seam. It is currently
  constructed with the llama-server restart helper.
- After readiness, `_publish_activation_route` and
  `model_switchboard/state.py::record_verified_route` publish a verified
  route; the current publication records `backend_kind="llama-server"`.
- `ods/config/model-state.schema.v1.json` and the Python validator currently
  allow `llama-server`, `lemonade`, `hipfire`, and `unknown`, but not
  `cafe-llama`. `ods/config/model-router/endpoints.json` currently defines
  the llama-server and legacy Lemonade endpoints only.

This narrows the production patch: runtime selection must be resolved before
the service-stage branch; cafe must get its own adapter/restart target and
endpoint ID; route publication and model-state schema/validator must carry the
same provider identity; the existing snapshot/rollback path must restore both
the prior runtime and prior router target. The default branch must continue to
choose the existing llama-server path exactly as before.

**Release gate remains closed.** No cafe activation was run against a live ODS
instance, no ODS-native activation/rollback regression suite was executed, and
no upstream PR has been opened. A green staging workflow must not be reported
as full ODS CI or runtime proof. The implementation should not be merged by
editing only the backend enum/endpoint allowlist: those changes would advertise
a route without providing a safe runtime lifecycle.


### CI fixture freshness finding — corrected

The staging workflow now checks out the authoritative `Osmantic/ODS:main` for
both backend adapter-contract tests and Dashboard integration. The fork's
`feat/dashboard-i18n-es-zh` branch remains only a source of locale files that
are missing in the target tree. Existing locale files are never overwritten;
translation additions are merged by key and collisions fail for review.

### Staged runtime provenance implementation (2026-10-09)

The staging overlay now includes `CafeLlamaAdapter` and a fail-closed patcher
that applies its contract to a fresh upstream checkout. It verifies before
restart that the installed artifact manifest matches the pinned build ID,
SHA-256, architecture and backend; after startup it requires the running
runtime to report the same build ID and artifact digest. Missing or mismatched
provenance prevents a successful activation result.

The overlay also adds `cafe-llama` to the model-state Python validator and JSON
Schema, adds a distinct `cafe-llama-default` endpoint, and modifies the staged
reconciler so build identity and artifact digest survive the runtime activation
proof. The staged host-agent route publisher chooses the cafe endpoint only
when the proof explicitly reports `runtimeKind=cafe-llama`; absent that proof,
the legacy route remains `llama-server-default`. The current contract tests
exercise artifact mismatch, build mismatch, missing digest, activation proof,
schema identity and endpoint separation.

The staging workflow including the host-agent publication delta passed
both jobs in
[run 37896945923](https://github.com/robertosantosx2/LEONES/actions/runs/37896945923)
on commit `cb91800972464203a3c582d0a1e38ffdef4640f0`. This is successful
contract/build validation against the current upstream source tree, not a live
ODS runtime activation test or the full ODS regression suite.

**Still not production-complete:** the host agent's `_do_model_activate` does
not yet select and start the cafe service from `ODS_INFERENCE_RUNTIME`; the
optional service definition and pinned, digest-verified image build are not
integrated into upstream; and there is no live activation/rollback test. The
overlay validates the runtime adapter/provenance and route-publication seams,
not a complete ODS runtime swap. The final PR gate remains closed until those
pieces and ODS-native regressions pass.
