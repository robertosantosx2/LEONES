# ODS integration checklist for the staged ICD implementation

This file is the transfer checklist for moving the staged code into ODS. The staged API router is not live until it is wired into ODS's existing runtime profile, environment-update, and service lifecycle code.

## 1. Backend wiring

Target files are under `ods/extensions/services/dashboard-api/`.

1. Copy the staged ICD core and cafe adapter into their target locations.
2. Copy/merge `routers/inference_configurations.py` and add the module to the API app's router imports. Merge the staged `routers/models.py` changes into the branch's current file rather than blindly replacing it if upstream has moved.
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
10. Verify `CTX_SIZE`, `LLAMA_BATCH_SIZE`, `LLAMA_ARG_CACHE_TYPE_K/V`, `LLAMA_ARG_FLASH_ATTN`, `LLAMA_ARG_SPEC_TYPE`, and `LLAMA_ARG_SPEC_DRAFT_N_MAX` against the exact cafe-llama runtime build and ODS env schema before merge. The current staged adapter intentionally limits KV cache to `f16`/`q8_0` and offload to `none`; `ptq1-mmV`, TurboQuant, host/CPU MoE offload, and SSD streaming are recorded as future capabilities but are not exposed as applicable choices until their exact runtime/env mappings are verified.

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

import platform
from model_selection import matching_runtime_profile

def _icd_compatible_profiles(model):
    gpu = get_gpu_info()
    ram = get_ram_metrics()
    profile = matching_runtime_profile(
        model,
        backend=getattr(gpu, "gpu_backend", "cpu") if gpu else "cpu",
        memory_type=getattr(gpu, "memory_type", "system") if gpu else "system",
        vram_mb=getattr(gpu, "memory_total_mb", 0) if gpu else 0,
        ram_gb=(ram or {}).get("total_gb"),
        host_arch=platform.machine(),
    )
    return [profile] if profile else []

def _icd_can_apply_runtime_configuration():
    mode_denial = models_router._model_activation_mode_denial(
        ODS_MODE_EFFECTIVE, models_router._configured_ods_mode(), LLM_BACKEND,
    )
    if mode_denial is not None or models_router.pixel_stream_active():
        return False
    if models_router._windows_hosted_runtime() and not models_router._model_management().get("canActivate"):
        return False
    # Fail closed when host-agent status is unavailable or a model/bootstrap
    # lifecycle operation is active.
    status = models_router._get_agent_model_status()
    if status is None or models_router._model_lifecycle_from_agent_status(status):
        return False
    if models_router._bootstrap_upgrade_download_conflict() is not None:
        return False
    return True

from helpers import get_inference_configuration_measurements

def _icd_get_measurements(model_id, workload_id):
    gpu = get_gpu_info()
    if not gpu:
        return []
    return [
        sample for sample in get_inference_configuration_measurements(workload_id=workload_id)
        if sample.get("model_id") == model_id
        and sample.get("gpu") == gpu.name
        and sample.get("backend") == gpu.gpu_backend
        and int(sample.get("vram_total_mb") or 0) == int(gpu.memory_total_mb or 0)
    ]

icd_router = create_inference_configuration_router(
    find_model=models_router._find_loadable_model,
    get_runtime_profiles=_icd_compatible_profiles,
    apply_environment=_icd_apply_environment,
    recreate_services=_icd_recreate_services,
    can_apply=_icd_can_apply_runtime_configuration,
    get_measurements=_icd_get_measurements,
)
app.include_router(icd_router)
```

The sketch reads existing env text but does not write it directly. All persistence goes through the host agent. Production wiring must also handle missing/unreadable env files and host-agent exceptions using ODS's existing error translation.

## 2. Dashboard wiring

Target files are under `ods/extensions/services/dashboard/src/`.

- Merge the staged `hooks/useModels.js` change into the branch's current hook (it adds optional `configuration_id` to the existing benchmark request), and copy `hooks/useInferenceConfigurations.js`.
- Copy `components/models/InferenceConfigurationPanel.jsx` and its stylesheet.
- Import the existing `useI18n` hook in `Models.jsx`, pass its translator to the panel, and render the panel for the selected model. Do not create a second language state or bypass the shared i18n provider.
- Merge the staged EN/ES/ZH keys under `models.inferenceConfiguration.*` into the canonical locale bundles on the ODS i18n branch. Keep English fallback.
- Do not add a second activation action or a second benchmark engine. The staged `routers/models.py` change validates the requested ID against the hardware-compatible candidate and persisted env, calls the existing benchmark routine, and records the exact `configuration_id` plus `workload_id` through the existing performance store. The staged `helpers.py` extension partitions those samples by configuration/workload and excludes them from model-level ranking. Merge both files carefully, not by blind replacement. The GET endpoint returns rankings only for the requested workload and the current model/hardware.
- Add frontend tests for loading, no candidates, API error, invalid combinations, apply pending/success/failure, and language fallback.

## 3. Backend and merge tests

The staged tests are contract tests for the router callbacks. Once wired in ODS, run them with the ODS Dashboard API test environment plus the existing ICD/model-selection tests. Add cases for:

- incompatible hardware profile and runtime;
- local/cloud mode denial, unmanaged Windows-host runtime, busy lifecycle, and active Pixel stream;
- env update failure, service recreation failure after env update, and cache invalidation;
- exact configuration ID and MEASURED-only benchmark evidence;
- regression that default llama-server model activation is unchanged.

The staged route deliberately accepts callback injection so it can be tested without running ODS's real host agent. The isolated LEONES evidence-store test uses dependency stubs and must not be copied unchanged into ODS's full pytest suite; port its assertions into an ODS-native test that uses the real module graph. The production callbacks still require ODS integration tests.

## 4. Evidence boundary

The earlier ODS result of 211 passed / 7 skipped covers the pre-existing focused ICD/model-selection tests only. It does not certify this staged route, Dashboard component, integration wiring, or hardware performance. No throughput claim may be attached until a real target-host benchmark records the exact configuration and workload.
