import json
from pathlib import Path

from scripts.runtime_benchmark_evidence import run_once, sha256_file, summarize


def test_run_once_captures_output_and_timing():
    result = run_once(["python3", "-c", "print('generation speed: 12.5 tok/s')"])
    assert result["exit_code"] == 0
    assert "12.5 tok/s" in result["stdout"]
    assert result["first_output_ms"] is not None
    assert result["tokens_per_second"] == 12.5


def test_sha256_is_stable(tmp_path: Path):
    p = tmp_path / "artifact.gguf"
    p.write_bytes(b"LEONES")
    assert len(sha256_file(p)) == 64
    assert sha256_file(p) == sha256_file(p)


def test_summary_contains_median_and_stdev():
    measurements = [
        {"ttft_ms": 10, "generation_time_ms": 100, "tokens_per_second": 10, "total_time_ms": 110, "peak_memory_mb": 100, "peak_vram_mb": None, "power_w": None},
        {"ttft_ms": 20, "generation_time_ms": 120, "tokens_per_second": 12, "total_time_ms": 140, "peak_memory_mb": 110, "peak_vram_mb": None, "power_w": None},
    ]
    out = summarize(measurements)
    assert isinstance(out, dict)
    assert out["measurement_count"] == 2
    assert out["metrics"]["tokens_per_second"]["median"] == 11
    assert "stdev" in out["metrics"]["ttft_ms"]


def test_schema_example_is_json():
    schema = Path("schemas/runtime-benchmark-evidence.v1.1.json")
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["$id"] == "https://leones.local/schemas/runtime-benchmark-evidence.v1.1.schema.json"
