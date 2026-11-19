import json
from pathlib import Path

from scripts.runtime_benchmark_evidence import run_once, sha256_file, summary


def test_run_once_captures_output_and_timing():
    result = run_once(["python3", "-c", "print('TTFT: 17.5 ms\\ngeneration speed: 12.5 tok/s')"])
    assert result["exit_code"] == 0
    assert "12.5 tok/s" in result["stdout"]
    assert result["first_output_ms"] is not None
    assert result["tokens_per_second"] == 12.5
    assert result["ttft_ms"] == 17.5
    assert result["ttft_source"] == "llama_cpp_prompt_eval_time_or_explicit_ttft"
    assert "peak_process_rss_mb" in result
    assert "peak_system_ram_used_mb" in result
    assert "peak_vram_mb_device_wide" in result
    assert "gpu_sample_count" in result


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
    assert out["tokens_per_second"]["iqr"] == 1
    assert out["tokens_per_second"]["mad"] == 1
    assert "p25" in out["ttft_ms"] and "p75" in out["ttft_ms"]
    assert "stdev" in out["ttft_ms"]


def test_schema_example_is_json():
    schema = Path("schemas/runtime-benchmark-evidence.v1.1.json")
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["$id"] == "runtime-benchmark-evidence.v1.1"



def test_first_stdout_byte_is_not_mislabeled_as_ttft():
    result = run_once(["python3", "-c", "import sys,time; sys.stdout.write('partial'); sys.stdout.flush(); time.sleep(0.2)"])
    assert result["first_output_ms"] is not None
    assert result["ttft_ms"] is None
    assert result["first_output_semantics"] == "time_to_first_stdout_byte_not_ttft"


def test_custom_ttft_regex_is_supported():
    result = run_once(
        ["python3", "-c", "print('first token latency = 23.75 ms')"],
        ttft_regex=r"first token latency\s*=\s*([0-9.]+)\s*ms",
    )
    assert result["ttft_ms"] == 23.75
    assert result["ttft_source"] == "custom_regex"
