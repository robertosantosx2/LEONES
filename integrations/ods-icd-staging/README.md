# ODS ICD staging workspace

This directory stages implementation artifacts for a later transfer into `Osmantic/ODS`. It is intentionally isolated from LEONES runtime code: nothing here is imported by LEONES, and no ODS runtime change is claimed to be deployed.

## Source and target

The working source is the ODS fork branch `robertosantosx2/ODS:feat/cafe-llama-icd-runtime-profile`. The upstream PR could not be created because the connected GitHub integration returns HTTP 403 for ODS Contents writes and PR creation.

Files in this staging area preserve ODS-relative target paths beneath `ods/` where practical. Use the manifest below when transferring them into ODS.

## Transfer manifest

| Staged file | Intended ODS destination | Status |
|---|---|---|
| `ods/extensions/services/dashboard-api/inference_configuration.py` | same path | Existing ICD core mirrored from ODS; tests remain the contract |
| `ods/extensions/services/dashboard-api/cafe_llama_icd.py` | same path | Includes canonical `CTX_SIZE` mapping correction |
| `ods/extensions/services/dashboard-api/routers/inference_configurations.py` | new router module | Staged GET/POST API; must be wired in `main.py` with hardware-aware profile, env, lifecycle and measurement callbacks |
| `ods/extensions/services/dashboard-api/routers/models.py` | merge into same path, not blind replacement | Staged existing benchmark-route extension validates config ID and returns exact workload evidence |
| `ods/extensions/services/dashboard-api/helpers.py` | merge into same path, not blind replacement | Extends existing performance store with config/workload-partitioned samples without contaminating model-level rankings |
| `ods/extensions/services/dashboard/src/components/models/InferenceConfigurationPanel.jsx` | same path | Staged UI panel; parent must pass the existing i18n translator |
| `ods/extensions/services/dashboard/src/components/models/inference-configuration-panel.css` | same path | Responsive panel styles |
| `ods/extensions/services/dashboard/src/i18n/inferenceConfiguration.*.json` | merge into canonical locale bundles | EN/ES/ZH strings; not standalone runtime locale files |
| `ods/extensions/services/dashboard/src/hooks/useInferenceConfigurations.js` | same path | Staged API hook |
| `tests/test_inference_configuration_routes.py` | ODS dashboard-api test suite | API contract, apply failure, partial apply and adapter-safety tests |
| `tests/test_inference_configuration_evidence.py` | Isolated LEONES CI process | Uses dependency stubs to test the staged store logic; port assertions into ODS-native tests rather than copying this stub file into the full ODS suite |
| `.github/workflows/ods-icd-staging.yml` | LEONES CI | Compiles staged API modules and runs the isolated route contract suite |
| `INTEGRATION.md` | PR/work plan | Required router, host-agent, lifecycle, i18n and test wiring

## Safety and merge rules

- ICD discovers candidates; it does not execute a runtime or authorize a model activation.
- Applying a configuration must reuse ODS's host-agent environment-update and service-lifecycle helpers. Never edit `.env` directly from this router.
- Preserve the existing model activation endpoint and default `llama-server` behavior.
- Never rank an unmeasured estimate as a benchmark result. A benchmark is tied to the exact `configuration_id`.
- The cafe adapter uses `CTX_SIZE`, not `MAX_CONTEXT`, for ODS context configuration.
- Dashboard labels must use the existing ODS i18n hook when wired into the application.
- No hardware performance claim is made by this staging branch.

## Validation state

The branch now includes a callback-injected API router, a staged extension to the existing benchmark endpoint/performance store for exact configuration and workload identity, Dashboard hook/panel/styles, locale strings and backend contract tests. These are committed as isolated staging artifacts, not yet wired into ODS. GitHub Actions run [`37855749394`](https://github.com/robertosantosx2/LEONES/actions/runs/37855749394) passed Python compilation for the ICD core, adapter, API router, and staged `helpers.py`/`routers/models.py`, plus the staged API contract suite (`10 passed`). The performance-store evidence tests and frontend tests/build remain unexecuted.

The ODS branch previously reported 211 passed and 7 skipped for focused ICD/model-selection tests, with clean `git diff --check` and Python compilation checks. Those results do not cover the staged API router, staged frontend, integration wiring, or real hardware.
