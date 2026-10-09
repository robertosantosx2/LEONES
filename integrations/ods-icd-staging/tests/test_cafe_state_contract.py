import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
ODS_BIN = ROOT / "ods-src" / "ods" / "bin"
ODS_ROOT = ROOT / "ods-src" / "ods"
if ODS_BIN.exists():
    sys.path.insert(0, str(ODS_BIN))

from model_switchboard import state


def test_cafe_is_a_writable_backend_kind_in_python_state_contract():
    assert "cafe-llama" in state._WRITABLE_BACKEND_KINDS
    assert "cafe-llama" in state._BACKEND_KINDS


def test_cafe_is_a_published_backend_kind_in_json_schema():
    schema = json.loads((ODS_ROOT / "config/model-state.schema.v1.json").read_text())
    active_backend = schema["properties"]["active"]["oneOf"][1]["properties"]["backend"]
    assert "cafe-llama" in active_backend["properties"]["kind"]["enum"]


def test_cafe_endpoint_is_not_the_legacy_llama_server_endpoint():
    doc = json.loads((ODS_ROOT / "config/model-router/endpoints.json").read_text())
    endpoints = {item["id"]: item["baseUrl"] for item in doc["endpoints"]}
    assert endpoints["llama-server-default"] == "http://llama-server:8080"
    assert endpoints["cafe-llama-default"] == "http://cafe-llama:8081"

def test_host_agent_publishes_only_the_verified_runtime_endpoint():
    source = (ODS_ROOT / "bin/ods-host-agent.py").read_text()
    assert 'runtime_kind = proof.get("runtimeKind", "llama-server")' in source
    assert 'endpoint_id = "cafe-llama-default"' in source
    assert 'backend_kind=runtime_kind, endpoint_id=endpoint_id' in source
    assert 'endpoint_id = "llama-server-default"' in source
