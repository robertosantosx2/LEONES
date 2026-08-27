import json
from pathlib import Path

from scripts.runtime_registry import capability_match, registry_entries


def test_registry_has_complete_deployment_taxonomy():
    data = json.loads(Path("runtime_registry.v1.1.json").read_text(encoding="utf-8"))
    allowed = set(data["taxonomy"]["deployment_class"])
    profiles = set(data["taxonomy"]["serving_profile"])
    entries = registry_entries()
    assert len(entries) == 6
    assert [entry.id for entry in entries.values()] == [
        "llama.cpp", "FreeToken", "AirLLM", "ollama", "vLLM", "SGLang"
    ]
    for entry in entries.values():
        assert entry.deployment_class
        assert set(entry.deployment_class) <= allowed
        assert entry.serving_profiles
        assert set(entry.serving_profiles) <= profiles


def test_cpudatacenter_profile_filters_out_local_runtimes():
    entries = registry_entries()
    ok, reasons = capability_match(entries["ollama"], deployment_class="datacenter")
    assert not ok
    assert any("deployment class" in reason for reason in reasons)
    ok, reasons = capability_match(entries["vLLM"], deployment_class="datacenter", serving_profile="multi_user")
    assert ok
    assert reasons == []


def test_local_profile_keeps_workstation_runtimes():
    entries = registry_entries()
    ok, reasons = capability_match(entries["FreeToken"], deployment_class="workstation", serving_profile="single_user")
    assert ok
    assert reasons == []
