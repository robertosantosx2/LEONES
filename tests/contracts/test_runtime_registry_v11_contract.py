import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "runtime_selection" / "v1_1" / "runtime_registry.json"


REQUIRED_RUNTIME_FIELDS = {
    "runtime_id",
    "display_name",
    "version_policy",
    "adapter_id",
    "entrypoint_ref",
    "availability",
    "execution_modes",
    "architectures",
    "formats",
    "hardware",
    "capabilities",
    "metrics",
    "measurement_policy",
}


def test_v11_registry_declares_first_wave_runtimes_with_common_contract():
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))

    assert document["contract"] == "runtime-registry.v1.1"
    runtimes = document["runtimes"]
    by_id = {runtime["runtime_id"]: runtime for runtime in runtimes}

    assert {"llama.cpp", "ollama", "freetoken", "airllm"} <= set(by_id)

    for runtime in runtimes:
        assert REQUIRED_RUNTIME_FIELDS <= runtime.keys()
        assert runtime["entrypoint_ref"].startswith("trusted://")
        assert runtime["availability"]["status"] in {
            "available",
            "unavailable",
            "unknown",
            "blocked",
        }
        assert runtime["measurement_policy"]["measured_tps_requires_benchmark"] is True


def test_v11_registry_keeps_runtime_commands_out_of_registry_metadata():
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))

    forbidden = {"command", "argv", "shell", "executable"}
    for runtime in document["runtimes"]:
        assert forbidden.isdisjoint(runtime)
        assert forbidden.isdisjoint(runtime.get("metadata", {}))
