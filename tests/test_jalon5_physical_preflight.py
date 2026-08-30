from scripts.jalon5_physical_preflight import build_preflight


def test_jalon5_preflight_is_observation_only():
    payload = build_preflight()
    assert payload["schema"] == "jalon5-physical-preflight.v1"
    assert payload["status"] == "observed"
    assert payload["physical_execution_required"] is True
    assert payload["measurement_status"] == "not_measured"


def test_jalon5_preflight_reports_known_runtime_slots():
    payload = build_preflight()
    assert set(payload["runtimes"]) == {"llama.cpp", "vllm", "sglang"}
    for runtime in payload["runtimes"].values():
        assert set(runtime) == {"available", "version"}
        assert isinstance(runtime["available"], bool)
