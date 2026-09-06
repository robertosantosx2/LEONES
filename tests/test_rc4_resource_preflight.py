from scripts.rc4_resource_preflight import memory_state, swap_state, collect


def test_memory_state_has_available_without_swap():
    state = memory_state()
    assert state["total_bytes"] >= state["available_bytes"] >= 0
    assert state["used_bytes"] >= 0


def test_swap_is_separate_from_ram():
    ram = memory_state()
    swap = swap_state()
    assert "available_bytes" in ram
    assert "total_bytes" in swap
    assert "swap" not in ram


def test_collect_has_all_three_software_targets():
    result = collect(".")
    names = {item["name"] for item in result["software"]}
    assert names == {"ODS", "Magnitude", "FitLLM / LLMFit"}
    assert result["rules"]["swap_counts_as_ram"] is False
    assert result["rules"]["unknown_sizes_are_null"] is True


def test_installation_budget_does_not_invent_unknown_sizes():
    budget = collect(".")["installation_budget"]
    assert budget["model_artifact_required_disk_bytes"] is None
    assert budget["runtime_required_disk_bytes"] is None
