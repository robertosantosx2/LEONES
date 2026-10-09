"""Fail-closed host-agent overlay for explicit cafe-llama activation.

This first implementation is restricted to native Linux + NVIDIA + host Compose.
It aborts if any expected upstream seam has drifted.
"""
from pathlib import Path

ROOT = Path("ods-src/ods")
AGENT = ROOT / "bin/ods-host-agent.py"


def replace_once(old: str, new: str) -> None:
    text = AGENT.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"host-agent activation overlay expected one anchor, found {count}: {old[:100]!r}")
    AGENT.write_text(text.replace(old, new, 1))


# Import the adapter without making it mandatory for stock ODS installations.
replace_once(
'''    _switchboard_adapters = None
    _switchboard_reconciler = None
try:
    from remote_provider.egress import (''',
'''    _switchboard_adapters = None
    _switchboard_reconciler = None
try:
    from model_switchboard.cafe_adapter import CafeLlamaAdapter as _CafeLlamaAdapter
except Exception:  # optional extension, default runtime remains llama-server
    _CafeLlamaAdapter = None
try:
    from remote_provider.egress import ('''
)

# Endpoint routing is opt-in and uses the published host port.
replace_once(
'''    if _runtime_uses_router_transport(env):
        return _native_llm_container_origin(env), "router"''',
'''    if str(env.get("ODS_INFERENCE_RUNTIME") or "llama-server").strip().lower() == "cafe-llama":
        port = str(env.get("EXT_CAFE_LLAMA_PORT") or "8081")
        return f"http://127.0.0.1:{port}", "direct"
    if _runtime_uses_router_transport(env):
        return _native_llm_container_origin(env), "router"'''
)

# Dedicated restart helper. Unlike stock llama-server, cafe never falls back to
# container recreation if the Compose project cannot be resolved.
anchor = '''def _compose_restart_llama_server(env: dict):
    """Restart llama-server via docker compose (host-native path).'''
helper = '''def _cafe_compose_env(env):
    compose_env = dict(os.environ)
    compose_env.update({str(key): str(value) for key, value in env.items()})
    model_ref = str(env.get("GGUF_FILE") or "").strip()
    if model_ref:
        compose_env["CAFE_LLAMA_MODEL"] = Path(model_ref).name
    return compose_env


def _compose_build_cafe_llama_image(env: dict):
    """Build the pinned image without starting a runtime candidate."""
    compose_flags = resolve_compose_flags()
    if not compose_flags:
        raise RuntimeError("cafe-llama requires resolved Compose flags; refusing fallback")
    result = subprocess.run(
        ["docker", "compose"] + compose_flags + ["build", "cafe-llama"],
        cwd=str(INSTALL_DIR), env=_cafe_compose_env(env),
        capture_output=True, text=True, timeout=900,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"cafe-llama Compose build failed (exit {result.returncode}): "
            f"{(result.stderr or "").strip()[:300]}"
        )
    logger.info("cafe-llama image built; adapter will verify provenance before start")


def _compose_restart_cafe_llama_server(env: dict):
    """Start only the already-built, provenance-verified cafe image."""
    compose_flags = resolve_compose_flags()
    if not compose_flags:
        raise RuntimeError("cafe-llama requires resolved Compose flags; refusing fallback")
    result = subprocess.run(
        ["docker", "compose"] + compose_flags + [
            "up", "-d", "--force-recreate", "--no-deps", "cafe-llama"
        ],
        cwd=str(INSTALL_DIR), env=_cafe_compose_env(env),
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"cafe-llama Compose start failed (exit {result.returncode}): "
            f"{(result.stderr or "").strip()[:300]}"
        )
    logger.info("cafe-llama service started after image provenance verification")


def _cafe_image_manifest():
    """Read provenance labels from the actual local image, never from .env."""
    result = subprocess.run(
        ["docker", "image", "inspect", "ods-cafe-llama:local"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError("cafe-llama image is not inspectable")
    import json as _json
    rows = _json.loads(result.stdout)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise RuntimeError("cafe-llama image inspection returned no image")
    image = rows[0]
    labels = (image.get("Config") or {}).get("Labels") or {}
    return {
        "build_id": str(labels.get("org.osmantic.cafe.build-id") or ""),
        "sha256": str(labels.get("org.osmantic.cafe.artifact-sha256") or ""),
        "architecture": str(labels.get("org.osmantic.cafe.architecture") or ""),
        "backend": str(labels.get("org.osmantic.cafe.backend") or ""),
        "image_id": str(image.get("Id") or ""),
    }


def _cafe_running_manifest(env):
    """Prove the named running container uses the inspected image and labels."""
    import json as _json
    result = subprocess.run(
        ["docker", "inspect", "ods-cafe-llama"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError("cafe-llama running container is not inspectable")
    rows = _json.loads(result.stdout)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise RuntimeError("cafe-llama container inspection returned no container")
    container = rows[0]
    if not (container.get("State") or {}).get("Running"):
        raise RuntimeError("cafe-llama container is not running")
    image = _cafe_image_manifest()
    if not image["image_id"] or container.get("Image") != image["image_id"]:
        raise RuntimeError("running cafe-llama container image ID differs from inspected image")
    labels = (container.get("Config") or {}).get("Labels") or {}
    return {
        "build_id": str(labels.get("org.osmantic.cafe.build-id") or ""),
        "artifact_sha256": str(labels.get("org.osmantic.cafe.artifact-sha256") or ""),
    }


''' + anchor
replace_once(anchor, helper)

# Validate selection before activation proceeds into model/config mutations.
anchor = '''        effective_mode, configured_mode = _model_activation_modes(persisted_env)
        mode_denial = _model_activation_mode_denial(effective_mode, configured_mode)'''
replace_once(
anchor,
'''        runtime_selector = str(persisted_env.get("ODS_INFERENCE_RUNTIME") or "llama-server").strip().lower()
        if runtime_selector not in {"llama-server", "cafe-llama"}:
            json_response(self, 409, {"error": "Unsupported ODS_INFERENCE_RUNTIME", "requestedRuntime": runtime_selector})
            return
        if runtime_selector == "cafe-llama":
            # This initial adapter is intentionally Linux-host-Compose + NVIDIA only.
            if (
                os.environ.get("ODS_HOST_INSTALL_DIR")
                or str(persisted_env.get("GPU_BACKEND") or "nvidia").lower() != "nvidia"
                or _wsl_runtime.candidate(persisted_env)
                or _is_windows_host_llama_server(persisted_env)
            ):
                json_response(self, 409, {
                    "error": "cafe-llama currently requires native Linux host Compose with NVIDIA",
                    "code": "cafe_runtime_platform_unsupported",
                })
                return
            required = {
                "CAFE_LLAMA_BUILD_ID": persisted_env.get("CAFE_LLAMA_BUILD_ID"),
                "CAFE_LLAMA_RELEASE_SHA256": persisted_env.get("CAFE_LLAMA_RELEASE_SHA256"),
                "CAFE_LLAMA_ARCHITECTURE": persisted_env.get("CAFE_LLAMA_ARCHITECTURE") or "linux-x64",
                "CAFE_LLAMA_BACKEND": persisted_env.get("CAFE_LLAMA_BACKEND") or "cuda-12.4",
            }
            digest = str(required["CAFE_LLAMA_RELEASE_SHA256"] or "")
            if (
                _CafeLlamaAdapter is None
                or not str(required["CAFE_LLAMA_BUILD_ID"] or "").strip()
                or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
            ):
                json_response(self, 409, {
                    "error": "cafe-llama adapter or pinned artifact identity is unavailable",
                    "code": "cafe_runtime_artifact_unpinned",
                })
                return
        mode_denial = _model_activation_mode_denial(effective_mode, configured_mode)'''
)

# Select cafe only in the native host Compose branch. Keep stock behavior untouched.
anchor = '''            else:
                runtime_restart_strategy = "compose-llama"
                if _switchboard_adapters is not None:
                    switchboard_adapter = _switchboard_adapters.ContainerLlamaAdapter(
                        restart=_compose_restart_llama_server,'''
replace_once(
anchor,
'''            else:
                if str(env.get("ODS_INFERENCE_RUNTIME") or "llama-server").strip().lower() == "cafe-llama":
                    runtime_restart_strategy = "compose-cafe-llama"
                    if _CafeLlamaAdapter is None:
                        raise RuntimeError("cafe-llama adapter is unavailable")
                    build_id = str(env.get("CAFE_LLAMA_BUILD_ID") or "").strip()
                    digest = str(env.get("CAFE_LLAMA_RELEASE_SHA256") or "").strip()
                    architecture = str(env.get("CAFE_LLAMA_ARCHITECTURE") or "linux-x64").strip()
                    backend = str(env.get("CAFE_LLAMA_BACKEND") or "cuda-12.4").strip()
                    switchboard_adapter = _CafeLlamaAdapter(
                        restart=_compose_restart_cafe_llama_server,
                        wait_ready=_sb_wait_ready,
                        build_artifact=_compose_build_cafe_llama_image,
                        expected_gguf=gguf_file,
                        context_length=int(context_length),
                        expected_build_id=build_id,
                        expected_sha256=digest,
                        architecture=architecture,
                        backend=backend,
                        inspect_artifact=_cafe_image_manifest,
                        probe_runtime_build=_cafe_running_manifest,
                        capabilities=switchboard_capabilities,
                        rollback=_compose_restart_llama_server,
                    )
                else:
                    runtime_restart_strategy = "compose-llama"
                    if _switchboard_adapters is not None:
                        switchboard_adapter = _switchboard_adapters.ContainerLlamaAdapter(
                            restart=_compose_restart_llama_server,'''
)

# Finish the indentation adjustment in the stock fallback branch after the anchor.
replace_once(
'''                        capabilities=switchboard_capabilities,
                    )
                else:
                    _compose_restart_llama_server(env)

            hermes_model_name = gguf_file''',
'''                            capabilities=switchboard_capabilities,
                        )
                    else:
                        _compose_restart_llama_server(env)

            hermes_model_name = gguf_file'''
)

# Include cafe in the fast readiness cadence and terminal-load diagnosis.
replace_once(
'''if runtime_restart_strategy in {"compose-llama", "container-llama", "windows-native-llama"}:''',
'''if runtime_restart_strategy in {"compose-llama", "compose-cafe-llama", "container-llama", "windows-native-llama"}:'''
)
replace_once(
'''terminal_failure_probe=(_staged_llama_load_failure_probe(gguf_file, runtime_stage_started)
                        if runtime_restart_strategy in {'compose-llama', 'container-llama'} else None),''',
'''terminal_failure_probe=(_staged_llama_load_failure_probe(gguf_file, runtime_stage_started)
                        if runtime_restart_strategy in {'compose-llama', 'compose-cafe-llama', 'container-llama'} else None),'''
)

print("Applied explicit cafe-llama host activation overlay.")
