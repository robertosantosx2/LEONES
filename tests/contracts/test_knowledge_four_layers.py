import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "web" / "data" / "knowledge.json"
CONTRACT = ROOT / "docs" / "sources" / "KNOWLEDGE-FICHA-CONTRACT.md"


def test_knowledge_registry_declares_exactly_four_layers():
    data = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    assert data["contract"] == "KNOWLEDGE-FICHA-CONTRACT.v1"
    assert [x["id"] for x in data["layers"]] == ["source", "evidence", "estimate", "measurement"]
    for record in data["records"]:
        assert set(("source", "evidence", "estimate", "measurement")).issubset(record)
        assert set(record["source"]) == {"title", "text"}
        assert set(record["evidence"]) == {"title", "text"}
        assert set(record["estimate"]) == {"title", "text"}
        assert set(record["measurement"]) == {"title", "text"}


def test_external_results_cannot_be_labeled_as_leones_measurement():
    data = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    for record in data["records"]:
        text = record["measurement"]["title"] + " " + record["measurement"]["text"]
        if any(token in text.lower() for token in ("evidencia externa", "mediciones externas", "claims externos")):
            assert "no" in text.lower() or "pendiente" in text.lower()


def test_contract_document_defines_the_same_four_questions():
    text = CONTRACT.read_text(encoding="utf-8")
    for phrase in (
        "FUENTE / DESCUBRIMIENTO",
        "EVIDENCIA",
        "ESTIMACIÓN",
        "MEDICIÓN LEONES",
    ):
        assert phrase in text


def test_strategic_sources_are_present():
    data = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    names = {r["name"] for r in data["records"]}
    expected = {
        "FreeToken",
        "El otro FreeToken",
        "Odysseus",
        "LLMFit",
        "AirLLM",
        "ODS",
        "Magnitude",
        "Runtimes locales 2026",
        "Artificial Analysis / Optima",
        "Buddy",
    }
    assert expected <= names
