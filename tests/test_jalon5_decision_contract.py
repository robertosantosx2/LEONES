from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/leones-ods-magnitude-decision.v1.json"
DOC = ROOT / "docs/jalones/jalon5.md"


def test_jalon5_contract_files_exist() -> None:
    assert DOC.is_file()
    assert SCHEMA.is_file()


def test_jalon5_schema_has_canonical_contract() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$id"] == "leones-ods-magnitude-decision.v1"
    assert schema["required"] == [
        "schema",
        "decision_id",
        "timestamp",
        "workload",
        "hardware",
        "runtime",
        "sources",
        "decision",
    ]
    assert schema["properties"]["sources"]["properties"]["llmfit"]["properties"][
        "estimate_only"
    ]["const"] is True


def test_jalon5_separates_external_signals_from_measurement() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Una fuente externa nunca puede escribir `measured`" in text
    assert "LLMFit conserva siempre `estimate_only: true`" in text
    assert "JALÓN 3" in text
    assert "selector LEONES" in text
