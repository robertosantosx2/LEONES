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
| `ods/extensions/services/dashboard-api/routers/inference_configurations.py` | new router module | Staged API implementation; must be wired in `main.py` and integrated with existing model/environment helpers |
| `ods/extensions/services/dashboard/src/components/models/InferenceConfigurationPanel.jsx` | same path | Staged UI panel |
| `ods/extensions/services/dashboard/src/hooks/useInferenceConfigurations.js` | same path | Staged API hook |
| `tests/test_inference_configuration_routes.py` | ODS dashboard-api test suite | Contract tests; run in ODS environment after wiring |

## Safety and merge rules

- ICD discovers candidates; it does not execute a runtime or authorize a model activation.
- Applying a configuration must reuse ODS's host-agent environment-update and service-lifecycle helpers. Never edit `.env` directly from this router.
- Preserve the existing model activation endpoint and default `llama-server` behavior.
- Never rank an unmeasured estimate as a benchmark result. A benchmark is tied to the exact `configuration_id`.
- The cafe adapter uses `CTX_SIZE`, not `MAX_CONTEXT`, for ODS context configuration.
- Dashboard labels must use the existing ODS i18n hook when wired into the application.
- No hardware performance claim is made by this staging branch.

## Validation state

The ODS branch previously reported 211 passed and 7 skipped for focused ICD/model-selection tests, with clean `git diff --check` and Python compilation checks. Those results do not cover the staged API router, staged frontend, integration wiring, or real hardware.
