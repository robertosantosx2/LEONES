import json
from pathlib import Path
from scripts.runtime_benchmark_evidence import run_once, sha256_file, sha256_text, summarize


def test_run_once_captures_stdout_stderr_and_tps():
    r = run_once(["python3", "-c", "import sys; print('Generation: 12.5 t/s'); print('err', file=sys.stderr)"])
    assert r["exit_code"] == 0
    assert "12.5 t/s" in r["stdout"]
    assert "err" in r["stderr"]
    assert r["tokens_per_second"] == 12.5
    assert r["first_output_ms"] is not None


def test_summary_is_deterministic():
    ms = [{"ttft_ms": 10, "generation_time_ms": 100, "output_tokens": 20, "tokens_per_second": 10, "total_time_ms": 110, "peak_memory_mb": 100, "peak_vram_mb": None, "power_w": None}, {"ttft_ms": 20, "generation_time_ms": 120, "output_tokens": 24, "tokens_per_second": 12, "total_time_ms": 140, "peak_memory_mb": 110, "peak_vram_mb": None, "power_w": None}]
    s = summarize(ms)
    assert s["measurement_count"] == 2
    assert s["metrics"]["tokens_per_second"]["median"] == 11
    assert "stdev" in s["metrics"]["ttft_ms"]


def test_hash_helpers(tmp_path: Path):
    p = tmp_path / "model.gguf"
    p.write_bytes(b"LEONES")
    assert len(sha256_file(p)) == 64
    assert sha256_text("LEONES") == sha256_text("LEONES")


def test_schema_is_strict_and_machine_readable():
    schema = json.loads(Path("schemas/runtime-benchmark-evidence.v1.1.json").read_text())
    assert schema["$id"].endswith("runtime-benchmark-evidence.v1.1.schema.json")
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert {"execution_id", "model", "protocol", "runtime", "hardware", "measurements", "summary", "process", "artifact"} <= required
    assert schema["properties"]["measurements"]["items"]["additionalProperties"] is False
