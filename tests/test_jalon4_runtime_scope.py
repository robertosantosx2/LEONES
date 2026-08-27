import json
from pathlib import Path


def test_jalon4_operational_scope_is_explicit():
    data = json.loads(Path("runtime_registry.v1.1.json").read_text(encoding="utf-8"))
    assert data["operational_runtimes"] == {
        "soho": ["llama.cpp", "FreeToken", "AirLLM", "ollama"],
        "cpd": ["vLLM", "SGLang"],
    }
    assert [x["id"] for x in data["runtimes"]] == [
        "llama.cpp", "FreeToken", "AirLLM", "ollama", "vLLM", "SGLang"
    ]


def test_jalon4_keeps_two_distinct_deployment_profiles():
    data = json.loads(Path("runtime_registry.v1.1.json").read_text(encoding="utf-8"))
    runtimes = {x["id"]: x for x in data["runtimes"]}
    assert "datacenter" in runtimes["vLLM"]["deployment_class"]
    assert "multi_user" in runtimes["vLLM"]["serving_profiles"]
    assert "datacenter" in runtimes["SGLang"]["deployment_class"]
    assert "multi_user" in runtimes["SGLang"]["serving_profiles"]
    assert "workstation" in runtimes["llama.cpp"]["deployment_class"]
    assert "single_user" in runtimes["llama.cpp"]["serving_profiles"]
