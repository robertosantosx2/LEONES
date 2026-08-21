from pathlib import Path

import pytest

from llmserve_a01 import build_a01_result


def _plan():
    return {
        "execution_authorized": True,
        "model": {"id": "demo-2", "revision": "fixture"},
        "runtime": {"name": "fixture-runtime", "command": ["/bin/true"]},
        "hardware": {"ram_gb": 1, "os": "test"},
        "inference": {},
    }


def _lookup(model_id: str):
    assert model_id == "demo-2"
    return {"id": model_id, "name": "Beta"}


def _write(path: str, name: str):
    Path(path).write_text(f"Model: {name}\n", encoding="utf-8")
    return path


def test_real_adapter_emits_measured_result(tmp_path: Path):
    output = '\n'.join([
        '{"tool":"lookup_model","arguments":{"model_id":"demo-2"}}',
        '{"tool":"write_report","arguments":{"path":"report.txt"}}',
    ])
    result = build_a01_result(_plan(), workspace=tmp_path, model_output=output,
                              lookup_model=_lookup, write_report=_write,
                              output_path="report.txt")
    assert result["evidence"]["evidence_type"] == "measured"
    assert result["evidence"]["execution_id"]
    assert result["agentic"]["grader"]["status"] == "passed"
    assert result["agentic"]["outcome"]["score"] == 1.0


def test_free_form_text_is_not_executed(tmp_path: Path):
    with pytest.raises(ValueError):
        build_a01_result(_plan(), workspace=tmp_path,
                         model_output="lookup_model demo-2; write_report report.txt",
                         lookup_model=_lookup, write_report=_write,
                         output_path="report.txt")


def test_bad_sequence_is_rejected(tmp_path: Path):
    output = '{"tool":"write_report","arguments":{"path":"report.txt"}}\n{"tool":"lookup_model","arguments":{"model_id":"demo-2"}}'
    with pytest.raises(ValueError):
        build_a01_result(_plan(), workspace=tmp_path, model_output=output,
                         lookup_model=_lookup, write_report=_write,
                         output_path="report.txt")
