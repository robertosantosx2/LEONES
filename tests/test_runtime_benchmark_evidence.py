import json
from pathlib import Path

from scripts.runtime_benchmark_evidence import _run_checked, run_once, sha256_file, summary


def test_run_once_captures_output_and_timing():
    result = run_once(["python3", "-c", "print('generation speed: 12.5 tok/s')"])
    assert result["exit_code"] == 0
    assert "12.5 tok/s" in result["stdout"]
    assert result["first_output_ms"] is not None
    assert result["tokens_per_second"] == 12.5


def test_run_checked_rejects_nonzero_exit():
    try:
        _run_checked(["python3", "-c", "raise SystemExit(7)"])
    except RuntimeError as exc:
        assert "exit code 7" in str(exc)
    else:
        raise AssertionError("failed measurement was accepted")


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
    out = summary(measurements)
    assert out["tokens_per_second"]["median"] == 11
    assert "stdev" in out["ttft_ms"]


def test_schema_example_is_json():
    schema = Path("schemas/runtime-benchmark-evidence.v1.1.json")
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["$id"] == "runtime-benchmark-evidence.v1.1"
    assert "protocol_id" in payload["properties"]["protocol"]["required"]
    assert "protocol_sha256" in payload["properties"]["protocol"]["required"]
    assert "cooldown_seconds" in payload["properties"]["protocol"]["required"]
    assert payload["properties"]["measurements"]["minItems"] == 5
