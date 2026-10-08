# ODS integration checklist for the staged ICD implementation

This file is the transfer checklist for moving the staged code into ODS. The staged API router is not live until it is wired into ODS's existing runtime profile, environment-update, and service lifecycle code.

## 1. Backend wiring

Target files are under `ods/extensions/services/dashboard-api/`.

1. Copy the staged ICD core and cafe adapter into their target locations.
2. Copy `routers/inference_configurations.py` and add the module to the API app's router imports.
3. In `main.py`, create the router using `create_inference_configuration_router(...)` and include it alongside `models_router.router`.
4. Bind `find_model` to `models_router._find_loadable_model` (or the canonical model lookup used by the branch).
5. Bind `get_runtime_profiles` to the same hardware-aware compatibility decision used by ODS model selection. It must return only the profile selected/validated for the current hardware and runtime; do not pass every catalog profile as if it were compatible.
6. Bind `can_apply` to the existing local/hybrid-mode and host-runtime-management checks. Reject apply when the model/runtime lifecycle is busy, Pixel is streaming, or the host runtime is unmanaged.
7. Implement `apply_environment(values)` in `main.py` using ODS's existing helpers:
   - read current env text using the existing runtime env path and parser;
   - merge only the adapter's allowlisted keys;
   - render the complete env using `_render_env_from_values`;
   - call `_call_agent_env_update(raw_text)` (never write `.env` from the router);
   - clear the existing settings/status caches.
8. Implement `recreate_services(service_ids)` by validating the IDs against `_SETTINGS_APPLY_ALLOWED_SERVICES`, then calling `_call_agent_core_recreate(service_ids)` and clearing caches. Preserve the existing model activation endpoint as the sole model-loading path.
9. Ensure the route fails closed if a host-agent update or service recreation is not confirmed. If the env update succeeds but recreation fails, return an explicit partial-application error and direct the UI to refresh runtime status; do not report a successful apply.
10. Verify `CTX_SIZE` is used for context and reconcile the adapter's cache/offload/speculation keys with the exact cafe-llama runtime build and ODS env schema before merge.

### Wiring sketch (adapt to the exact ODS branch helpers)

```python
from routers.inference_configurations import create_inference_configuration_router

# These callbacks belong in main.py, where ODS's private host-agent and env
# helpers already exist. They must reuse ODS lifecycle policy; this sketch is
# deliberately not a drop-in patch until hardware-profile selection is bound.
async def _icd_apply_environment(values):
    raw_text = _resolve_runtime_env_path().read_text(encoding="utf-8")
    env_values, parse_issues = _parse_env_text(raw_text)
    if parse_issues:
        raise RuntimeError("Existing ODS environment has parse errors")
    env_values.update(values)
    saved_text = _render_env_from_values(env_values)
    response = await asyncio.to_thread(_call_agent_env_update, saved_text)
    _clear_settings_caches()
    return response

async def _icd_recreate_services(service_ids):
    allowed = _SETTINGS_APPLY_ALLOWED_SERVICES
    if any(service_id not in allowed for service_id in service_ids):
        raise ValueError("Service is not eligible for Dashboard apply")
    response = await asyncio.to_thread(_call_agent_core_recreate, service_ids)
    _clear_settings_caches()
    return response

# _icd_compatible_profiles must call the same hardware/runtime-profile matcher
# used by ODS model selection. It must not simply return all model profiles.
icd_router = create_inference_configuration_router(
    find_model=models_router._find_loadable_model,
    get_runtime_profiles=_icd_compatible_profiles,
    apply_environment=_icd_apply_environment,
    recreate_services=_icd_recreate_services,
    can_apply=_icd_can_apply_runtime_configuration,
)
app.include_router(icd_router)
```

The sketch reads existing env text but does not write it directly. All persistence goes through the host agent. Production wiring must also handle missing/unreadable env files and host-agent exceptions using ODS's existing error translation.

## 2. Dashboard wiring

Target files are under `ods/extensions/services/dashboard/src/`.

- Copy `hooks/useInferenceConfigurations.js`.
- Copy `components/models/InferenceConfigurationPanel.jsx` and its stylesheet.
- Import the existing `useI18n` hook in `Models.jsx`, pass its translator to the panel, and render the panel for the selected model. Do not create a second language state or bypass the shared i18n provider.
- Merge the staged EN/ES/ZH keys under `models.inferenceConfiguration.*` into the canonical locale bundles on the ODS i18n branch. Keep English fallback.
- Do not add a second activation action. After applying runtime settings, the existing benchmark action should benchmark the currently loaded model, and the receipt must identify the exact `configuration_id` before the result can rank a candidate.
- Add frontend tests for loading, no candidates, API error, invalid combinations, apply pending/success/failure, and language fallback.

## 3. Backend and merge tests

The staged tests are contract tests for the router callbacks. Once wired in ODS, run them with the ODS Dashboard API test environment plus the existing ICD/model-selection tests. Add cases for:

- incompatible hardware profile and runtime;
- local/cloud mode denial, unmanaged Windows-host runtime, busy lifecycle, and active Pixel stream;
- env update failure, service recreation failure after env update, and cache invalidation;
- exact configuration ID and MEASURED-only benchmark evidence;
- regression that default llama-server model activation is unchanged.

The staged route deliberately accepts callback injection so it can be tested without running ODS's real host agent. The production callbacks still require ODS integration tests.

## 4. Evidence boundary

The earlier ODS result of 211 passed / 7 skipped covers the pre-existing focused ICD/model-selection tests only. It does not certify this staged route, Dashboard component, integration wiring, or hardware performance. No throughput claim may be attached until a real target-host benchmark records the exact configuration and workload.
