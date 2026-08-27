import json
import sys
import time
from pathlib import Path

from scripts.runtime_benchmark_evidence import now, run_once, sha256_file, sha256_text, summarize


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas/runtime-benchmark-evidence.v1.1.json"


def test_run_once_captures_stdout_stderr_and_tps():
    code = "import sys; print('Generation: 12.5 t/s'); print('err', file=sys.stderr)"
    result = run_once([sys.executable, "-c", code])
    assert result["exit_code"] == 0
    assert "12.5 t/s" in result["stdout"]
    assert "err" in result["stderr"]
    assert result["tokens_per_second"] == 12.5
    assert result["first_output_ms"] is not None
    assert result["ttft_ms"] == result["first_output_ms"]


def test_stderr_startup_does_not_define_first_output():
    code = "import sys,time; print('startup', file=sys.stderr); time.sleep(0.03); print('model output')"
    result = run_once([sys.executable, "-c", code])
    assert result["exit_code"] == 0
    assert result["first_output_ms"] >= 20
    assert result["stdout"].strip() == "model output"


def test_output_tokens_are_not_invented_from_stderr_or_tps():
    code = "import sys; print('Generation: 20 t/s', file=sys.stderr)"
    result = run_once([sys.executable, "-c", code])
    assert result["tokens_per_second"] == 20
    assert result["output_tokens"] is None


def test_summary_is_deterministic():
    measurements = [
        {"ttft_ms": 10, "generation_time_ms": 100, "output_tokens": 20, "tokens_per_second": 10, "total_time_ms": 110, "peak_memory_mb": 100, "peak_vram_mb": None, "power_w": None},
        {"ttft_ms": 20, "generation_time_ms": 120, "output_tokens": 24, "tokens_per_second": 12, "total_time_ms": 140, "peak_memory_mb": 110, "peak_vram_mb": None, "power_w": None},
    ]
    summary = summarize(measurements)
    assert summary["measurement_count"] == 2
    assert summary["metrics"]["tokens_per_second"]["median"] == 11
    assert "stdev" in summary["metrics"]["ttft_ms"]


def test_hash_helpers(tmp_path: Path):
    path = tmp_path / "model.gguf"
    path.write_bytes(b"LEONES")
    assert len(sha256_file(path)) == 64
    assert sha256_text("LEONES") == sha256_text("LEONES")


def test_timestamps_keep_subsecond_precision():
    first = now()
    time.sleep(0.002)
    second = now()
    assert first.endswith("Z") and second.endswith("Z")
    assert "." in first and len(first.split(".", 1)[1]) == 5
    assert second > first


def test_schema_is_strict_and_machine_readable():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$id"].endswith("runtime-benchmark-evidence.v1.1.schema.json")
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert {"execution_id", "model", "protocol", "runtime", "hardware", "measurements", "summary", "process", "artifact"} <= required
    assert schema["properties"]["measurements"]["items"]["additionalProperties"] is False


def test_schema_declares_observable_nulls():
    measurement = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["properties"]["measurements"]["items"]["properties"]
    for field in ("ttft_ms", "first_output_ms", "generation_time_ms", "output_tokens", "tokens_per_second", "peak_memory_mb", "peak_vram_mb", "power_w"):
        assert "null" in measurement[field]["type"]
