"""Static safety contracts for the staged host-agent overlay.

These tests complement compilation and adapter unit tests. They ensure the
overlay keeps the stock runtime as default, verifies the built image before
starting it, and includes an explicit candidate-stop/stock-restore rollback.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "scripts" / "apply_cafe_host_activation_overlay.py"
ADAPTER = ROOT / "ods" / "bin" / "model_switchboard" / "cafe_adapter.py"


def test_stock_runtime_remains_the_default_and_cafe_is_opt_in():
    source = OVERLAY.read_text()
    assert 'env.get("ODS_INFERENCE_RUNTIME") or "llama-server"' in source
    assert '"llama-server", "cafe-llama"' in source
    assert 'runtime_restart_strategy = "compose-llama"' in source
    assert 'runtime_restart_strategy = "compose-cafe-llama"' in source


def test_pinned_image_is_built_and_verified_before_candidate_start():
    adapter = ADAPTER.read_text()
    build = adapter.index("self._build_artifact(env)")
    inspect = adapter.index("artifact = self._inspect_artifact()", build)
    verify = adapter.index("self._artifact_verified = True", inspect)
    start = adapter.index("self._restart(env)", verify)
    assert build < inspect < verify < start

    overlay = OVERLAY.read_text()
    assert '["docker", "compose"] + compose_flags + ["build", "cafe-llama"]' in overlay
    assert '"docker", "image", "inspect", "ods-cafe-llama:local"' in overlay


def test_rollback_stops_candidate_then_restores_stock_runtime():
    source = OVERLAY.read_text()
    stop = source.index('elif runtime_restart_strategy == "compose-cafe-llama":')
    stop_candidate = source.index("_compose_stop_cafe_llama_server(rollback_env)", stop)
    restore_stock = source.index("_compose_restart_llama_server(rollback_env)", stop_candidate)
    assert stop < stop_candidate < restore_stock


def test_running_identity_is_bound_to_inspected_image_and_running_container():
    source = OVERLAY.read_text()
    assert '"docker", "inspect", "ods-cafe-llama"' in source
    assert 'container.get("Image") != image["image_id"]' in source
    assert 'if not (container.get("State") or {}).get("Running")' in source
