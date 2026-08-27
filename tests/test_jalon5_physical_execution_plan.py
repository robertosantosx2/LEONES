import json
from pathlib import Path


PLAN = Path("docs/runtime-physical-execution-plan.v1.json")
SCHEMA = Path("schemas/runtime-physical-execution-plan.v1.schema.json")
EXPECTED = {"llama.cpp", "ollama", "AirLLM", "FreeToken", "vLLM", "SGLang"}


def test_physical_plan_is_valid_and_complete():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["schema_version"] == "runtime-physical-execution-plan.v1"
    assert plan["profile_order"] == ["soho", "cpd"]
    executions = {item["runtime"]: item for item in plan["executions"]}
    assert set(executions) == EXPECTED
    assert all(item["requires_physical_host"] is True for item in executions.values())
    assert all(item["measurement_contract"] == "runtime-benchmark-evidence.v1.1" for item in executions.values())
    assert {executions[r]["profile"] for r in ("llama.cpp", "ollama", "AirLLM", "FreeToken")} == {"soho"}
    assert {executions[r]["profile"] for r in ("vLLM", "SGLang")} == {"cpd"}


def test_physical_plan_schema_is_json_schema_2020_12():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("runtime-physical-execution-plan.v1.schema.json")
