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
