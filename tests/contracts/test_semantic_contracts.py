import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_promotion_requires_quality_pass_and_osi():
    schema = load("promotion-quality-gate-v1.json")
    rules = schema["allOf"]
    assert rules
    then = rules[0]["then"]["properties"]["quality_gate"]["properties"]
    assert then["state"]["const"] == "PASS"
    assert set(then["osi_state"]["enum"]) == {"NOT_REQUIRED", "PASS"}


def test_router_only_exposes_allowed_osi_modes():
    schema = load("atlas-router-contract-v1.json")
    modes = schema["properties"]["request"]["properties"]["osi_mode"]["enum"]
    assert modes == ["OPEN_ALL", "FORCE_COPYLEFT_CHECK"]


def test_evidence_states_keep_estimated_distinct_from_verified():
    schema = load("atlas-evidence-contract-v1.json")
    states = schema["properties"]["evidence"]["items"]["properties"]["verification_state"]["enum"]
    assert "ESTIMATED" in states
    assert "VERIFIED" in states
    assert states.index("ESTIMATED") != states.index("VERIFIED")


def test_router_recommendation_requires_evidence_and_uncertainty():
    schema = load("atlas-router-contract-v1.json")
    required = schema["properties"]["recommendation"]["required"]
    assert "evidence_refs" in required
    assert "uncertainty" in required


def test_canonical_writer_is_not_part_of_router_contract():
    schema = load("atlas-router-contract-v1.json")
    serialized = json.dumps(schema, sort_keys=True)
    assert "ATLAS_WRITE" not in serialized


def test_contract_versions_are_aligned():
    names = [
        "atlas-evidence-contract-v1.json",
        "promotion-quality-gate-v1.json",
        "atlas-router-contract-v1.json",
    ]
    versions = {load(name)["properties"]["contract_version"]["const"] for name in names}
    assert versions == {"1.0"}
