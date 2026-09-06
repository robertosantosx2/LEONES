import json

from scripts.rc4_resource_preflight import collect_resource_state, memory_state, swap_state


def test_memory_state_uses_available_ram_not_swap():
    state = memory_state({"MemTotal": 8 * 1024**3, "MemFree": 1 * 1024**3, "MemAvailable": 3 * 1024**3})
    assert state["total_bytes"] == 8 * 1024**3
    assert state["available_bytes"] == 3 * 1024**3
    assert state["used_bytes"] == 5 * 1024**3


def test_swap_is_separate_from_ram():
    state = swap_state({"SwapTotal": 10 * 1024**3, "SwapFree": 4 * 1024**3})
    assert state["total_bytes"] == 10 * 1024**3
    assert state["used_bytes"] == 6 * 1024**3
    assert state["free_bytes"] == 4 * 1024**3


def test_resource_state_has_three_tool_checks():
    state = collect_resource_state(".")
    assert state["schema"] == "leones.rc4.resource-state.v1"
    names = {item["name"] for item in state["resource_state"]["software"]}
    assert names == {"ODS", "Magnitude", "FitLLM / LLMFit"}
    assert state["policy"]["swap_counts_as_ram"] is False
    assert state["policy"]["automatic_install_or_update"] is False


def test_resource_state_is_json_serializable():
    state = collect_resource_state(".")
    json.dumps(state)
