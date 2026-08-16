import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_atlas_storage_accepts_only_canonical_entities():
    schema = load("atlas-storage-v1.json")
    state = schema["properties"]["entity"]["properties"]["state"]["const"]
    required = schema["required"]
    assert state == "ACCEPTED"
    assert {"entity", "evidence_refs", "lineage"}.issubset(required)


def test_atlas_storage_requires_lineage():
    schema = load("atlas-storage-v1.json")
    lineage_required = schema["properties"]["lineage"]["required"]
    assert "source_type" in lineage_required


def test_evidence_storage_requires_provenance():
    schema = load("evidence-storage-v1.json")
    assert "provenance" in schema["required"]
    assert "source" in schema["properties"]["provenance"]["required"]


def test_storage_contract_versions_are_aligned():
    assert load("atlas-storage-v1.json")["properties"]["contract_version"]["const"] == "1.0"
    assert load("evidence-storage-v1.json")["properties"]["contract_version"]["const"] == "1.0"


def test_storage_evidence_keeps_verification_states():
    schema = load("evidence-storage-v1.json")
    states = schema["properties"]["verification_state"]["enum"]
    assert set(states) == {"VERIFIED", "ESTIMATED", "UNVERIFIED", "DISPUTED", "STALE"}
