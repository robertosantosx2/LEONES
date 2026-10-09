# ODS Dashboard ICD implementation gate

## Purpose

This gate tracks the production implementation of Inference Configuration Discovery (ICD) in ODS. LEONES owns the acceptance contract and evidence discipline; ODS owns the runtime and Dashboard implementation.

Related specifications:

- [ICD runtime port](ods-cafe-llama-icd-port.md)
- [Dashboard ICD contract](ods-cafe-llama-dashboard-icd.md)

## Gate rule

Do not mark a row PASS because the design or prototype exists. PASS requires an identifiable ODS implementation and reproducible test/evidence. LEONES prototype tests validate the contract, not ODS production wiring or hardware performance.

| ID | Acceptance criterion | Required ODS evidence | Status |
|---|---|---|---|
| ICD-01 | Generic ICD schema and deterministic configuration IDs | Unit tests for canonical signatures, schema validation, and deterministic deduplication | IMPLEMENTED — focused tests reported passing |
| ICD-02 | Existing model/runtime compatibility remains authoritative | Regression tests show `rank_catalog_models()` and runtime-profile matching unchanged | IMPLEMENTED — focused model-selection matrix passed |
| ICD-03 | ICD is second-stage discovery on an existing selected Candidate | Test that no runtime profile returns no configurations and compatible profiles produce candidates | IMPLEMENTED — ODS Candidate bridge present |
| ICD-04 | Discovery candidates contain no measurements and do not authorize execution | Tests reject measurement fields and assert `measurement_required=true`, `execution_authorized=false` | IMPLEMENTED — contract tests |
| ICD-05 | cafe-llama.cpp owns runtime-specific capabilities and validation | Adapter tests for Turbo KV/Flash Attention and MTP draft-token constraints | IMPLEMENTED — focused tests |
| ICD-06 | Dashboard can fetch configurations for a model | GET `/api/models/{model_id}/inference-configurations`, API tests and documented response schema | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-07 | Dashboard exposes editable supported parameters without unbounded combinations | Models-page panel, capability-driven controls, numeric coercion and frontend tests | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-08 | Apply validates model, runtime, schema and runtime-specific constraints | POST `/api/models/{model_id}/inference-configuration` tests for valid and invalid payloads | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-09 | Applying settings reuses existing ODS host-agent environment and lifecycle paths | Tests verify env merge/update and targeted service recreation; no direct .env writes from router | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-10 | Existing model activation remains the sole model-loading path | Regression test that configuration apply does not create a competing activation mechanism | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-11 | Benchmark uses existing ODS evidence path and exact configuration identity | Benchmark receipt associates result with exact `configuration_id`; no duplicate evidence store | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-12 | Only measured evidence can support performance ranking | Test where an ESTIMATED high value loses to an exact MEASURED candidate | CONTRACT PROVEN IN LEONES; ODS WIRING NOT VERIFIED |
| ICD-13 | Default llama-server path is unchanged when cafe runtime is not selected | Existing runtime and model lifecycle regression tests | NOT VERIFIED |
| ICD-14 | Dashboard text is ready for EN/ES/ZH i18n integration | UI calls the existing i18n hook and has keys under `models.inferenceConfiguration.*` | NOT IMPLEMENTED / NOT VERIFIED |
| ICD-15 | Hardware performance claims are based on real target-host runs | Benchmark receipt includes hardware, runtime/build, model, exact config ID, workload, tokens/s and latency | NOT RUN — no hardware claim |

## Validation already reported

On the ODS branch `feat/cafe-llama-icd-runtime-profile`:

- `211 passed, 7 skipped` for the focused ICD and model-selection test suites.
- `git diff --check` clean.
- Python compilation checks clean for the ICD core, cafe adapter, Candidate bridge and focused tests.

These results cover the ICD core and model-selection regression surface only. They do not validate Dashboard endpoints, frontend build, lifecycle application, or physical performance.

The LEONES prototype and its tests are contract evidence only. Do not reuse any LEONES result as a measurement of ODS on the user's machine.

## Merge gate

Before proposing the Dashboard phase for upstream review:

1. Complete ICD-06 through ICD-10.
2. Add backend tests for missing model, unsupported runtime, invalid configuration, environment merge and lifecycle failure.
3. Add frontend tests/build checks for loading, empty/error states, parameter edits, apply and benchmark actions.
4. Confirm all labels use the existing i18n hook and English fallback; provide Spanish and Simplified Chinese keys.
5. Run the focused ICD/model-selection tests plus the relevant Dashboard API/frontend suites.
6. Run `git diff --check` and inspect the final diff.
7. Record the actual PR URL and CI status. Do not treat a pushed branch or an uncreated PR as an upstream submission.

## Hardware qualification gate

After code review and merge, run a controlled benchmark on the target hardware. Record the exact model file and checksum, runtime revision, kernel, quantization, context, GPU layers, KV cache, Flash Attention, offload, speculation/draft depth, batch settings, warm-up policy, workload, measured tokens/s, latency, peak VRAM/RAM, and `configuration_id`.

A configuration is MEASURED only for the exact configuration and workload represented by its receipt. Any change to a performance-relevant dimension requires a new measurement.
## Upstream submission status (2026-10-09)

The branch `robertosantosx2/ODS:feat/cafe-llama-icd-runtime-profile` is available, but the ChatGPT GitHub integration cannot create the upstream pull request: a direct attempt against `Osmantic/ODS` returned HTTP 403, `Resource not accessible by integration`, on GitHub's create-pull-request endpoint. A second attempt to create a draft PR in the fork also returned 403; an issue-creation attempt in the fork was blocked as well. This points to an integration authorization limitation, not evidence that the branch or tests are invalid.

- **No upstream PR has been created by the integration.**
- Manual compare/new-PR page: https://github.com/Osmantic/ODS/compare/main...robertosantosx2:feat/cafe-llama-icd-runtime-profile
- GitHub documents that creating a PR needs repository **Pull requests: write** permission; `X-Accepted-GitHub-Permissions` on a 403 can identify the missing permission. See https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request and https://docs.github.com/en/enterprise-cloud@latest/rest/using-the-rest-api/troubleshooting-the-rest-api.
- To repair the connector, reconnect the GitHub app from ChatGPT Settings → Apps, confirm that the app installation includes `robertosantosx2/ODS` and the required repository permissions, and approve any requested permission upgrade on GitHub. If the integration still returns 403 despite those settings, this needs to be fixed by the integration provider; do not share a personal access token in chat.

The PR description must retain the scope boundary above: this is ICD foundation work, not a claim that Dashboard GET/POST, the editor, lifecycle wiring, i18n, or hardware benchmarking are complete.
## Pre-merge issue found during remote review

The current ODS cafe adapter maps the ICD `context` dimension to `MAX_CONTEXT`, while the ODS `.env.example` canonical setting is `CTX_SIZE`. Correct the adapter and its environment-mapping test together before treating runtime application as complete. This mismatch has not been changed because the GitHub integration also returned HTTP 403 on the ODS Contents API (`create-or-update-file-contents`), so it currently cannot push code changes to the ODS branch.

Additional confirmed blocker: the integration's PR-creation endpoint and Contents write endpoint both return `Resource not accessible by integration`. Reconnecting the app may help only if the integration's actual token can receive the needed scopes; if the integration provider does not expose repository writes, use the manual PR page for submission and ask the integration provider to restore write capability. No credentials should be pasted into chat.
## Staged implementation on LEONES branch (2026-10-09)

This branch is now the working area for all further ODS ICD work until the upstream PR is ready. The staged code is isolated under `integrations/ods-icd-staging/` so LEONES runtime code is not accidentally coupled to ODS.

- Branch: `ods-cafe-llama-icd-dashboard` (based on `ods-evolution`).
- Staged ICD core and cafe adapter, with context mapping corrected to `CTX_SIZE`.
- Added a callback-injected FastAPI router for GET discovery and POST apply, including candidate signature validation, runtime-specific constraints, exact-workload measured ranking, and fail-closed reporting when environment update or service recreation is not confirmed.
- Staged a merge (not blind replacement) of the existing benchmark route and performance store so measured records are partitioned by exact `configuration_id` and workload ID; model-level rankings exclude ICD-specific records.
- Added staged Dashboard hook and parameter panel, stylesheet, and EN/ES/ZH locale strings.
- Added backend route contract tests, exact configuration/workload evidence-store tests, and a transfer/integration checklist.

**Important status distinction:** these artifacts are committed in LEONES staging only. They are not yet installed into ODS or wired into the ODS FastAPI app. GitHub Actions run [37856005959](https://github.com/robertosantosx2/LEONES/actions/runs/37856005959) passed Python compilation, API route contracts (`10 passed`), exact configuration/workload evidence-store tests, Dashboard panel tests (`6 passed`), and the Dashboard production build. These isolated staging checks do not prove ODS app wiring or full ODS regression safety. Do not change ICD-06..10 or ICD-14 to PASS until the code is wired and the required tests pass in ODS.

Next implementation gates:
1. Add ODS-native integration tests for real host-agent callbacks, lifecycle guards, persisted environment verification, and benchmark receipt identity; the isolated staging tests now pass.
2. Complete the ODS main.py wiring with the actual hardware-compatible profile resolver, existing host-agent env merge, mode/lifecycle guards, and exact service allowlist.
3. Merge the staged panel into the current Models page without dropping concurrent ODS/i18n changes, and merge EN/ES/ZH keys into the canonical locale dictionaries.
4. Run the staged API/evidence tests, add frontend tests/build, and verify env update failure and service recreation failure/partial apply in the ODS test environment.
5. Validate cache/offload/speculation env keys against the exact cafe-llama build and ODS env schema.
6. Transfer the finished patch from this LEONES staging branch into the ODS fork branch, run the full focused suites, then open the upstream PR when GitHub write access is restored.

## Staged app-wiring review (2026-10-09)

A full staged copy of the current ODS `main.py` now includes the ICD router factory and callback bindings for hardware-profile matching, host-agent env persistence, allowlisted `llama-server` recreation, lifecycle/mode/Pixel guards, and exact-workload hardware-filtered measurements. The staging workflow compiles this file.

**Runtime-selection blocker remains:** the current model catalog profiles are hardware compatibility profiles (for example `backend: nvidia`) and do not identify `cafe-llama.cpp` as the active runtime. The resolver intentionally refuses to relabel generic profiles. Consequently the endpoint can be wired while returning no applicable cafe configurations until an explicit ODS runtime-selection/profile field and a supported runtime build/activation path are added. ICD-06..10 and ICD-14 remain NOT VERIFIED in ODS; no hardware performance claims are allowed.
