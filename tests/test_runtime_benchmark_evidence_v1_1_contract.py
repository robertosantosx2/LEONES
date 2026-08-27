import json
import subprocess
import sys
from pathlib import Path

from scripts.runtime_benchmark_evidence import run_once, sha256_file, summary, validate


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/runtime-benchmark-evidence.v1.1.json"


def test_schema_is_strict_and_machine_readable():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$id"] == "runtime-benchmark-evidence.v1.1"
    assert schema["additionalProperties"] is False
    assert "measurements" in schema["required"]
    assert "summary" in schema["required"]
    assert "artifact" in schema["required"]


def test_run_once_keeps_stdout_and_stderr_separate():
    result = run_once([
        sys.executable,
        "-c",
        "import sys; print('out 12.5 tok/s'); print('err', file=sys.stderr)",
    ])
    assert result["exit_code"] == 0
    assert "out 12.5 tok/s" in result["stdout"]
    assert "err" in result["stderr"]
    assert result["first_output_ms"] is not None
    assert result["tokens_per_second"] == 12.5


def test_summary_has_reproducible_statistics():
    measurements = [
        {"ttft_ms": 10, "first_output_ms": 10, "generation_time_ms": 100, "output_tokens": 100, "tokens_per_second": 10, "total_time_ms": 110, "peak_memory_mb": 100, "peak_vram_mb": None, "power_w": None},
        {"ttft_ms": 20, "first_output_ms": 20, "generation_time_ms": 120, "output_tokens": 120, "tokens_per_second": 12, "total_time_ms": 140, "peak_memory_mb": 110, "peak_vram_mb": None, "power_w": None},
    ]
    out = summary(measurements)
    assert out["tokens_per_second"]["median"] == 11
    assert "stdev" in out["ttft_ms"]
    assert out["output_tokens"]["mean"] == 110


def test_validate_rejects_failed_measurement():
    payload = {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": "rt-12345678",
        "timestamp_start": "2026-08-27T10:00:00Z",
        "timestamp_end": "2026-08-27T10:00:01Z",
        "model": {}, "protocol": {}, "runtime": {}, "hardware": {},
        "measurements": [{"exit_code": 1}], "summary": {}, "process": {}, "artifact": {},
    }
    try:
        validate(payload)
    except ValueError as exc:
        assert "failed measurement" in str(exc)
    else:
        raise AssertionError("failed measurement was accepted")


def test_artifact_hash_is_stable(tmp_path: Path):
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"LEONES")
    digest = sha256_file(artifact)
    assert len(digest) == 64
    assert digest == sha256_file(artifact)
