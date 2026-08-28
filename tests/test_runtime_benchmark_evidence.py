import json
from pathlib import Path

from scripts.runtime_benchmark_evidence import (
    command_output_token_limit,
    hardware,
    infer_backend,
    run_once,
    runtime_revision,
    sha256_file,
    summary,
)


def test_run_once_captures_output_and_timing_without_faking_ttft():
    result = run_once(["python3", "-c", "print('generation speed: 12.5 tok/s')"])
    assert result["exit_code"] == 0
    assert "12.5 tok/s" in result["stdout"]
    assert result["first_output_ms"] is not None
    assert result["ttft_ms"] is None
    assert result["tokens_per_second"] == 12.5


def test_run_once_preserves_nonzero_exit_and_output():
    result = run_once(["python3", "-c", "print('failed run'); raise SystemExit(7)"])
    assert result["exit_code"] == 7
    assert "failed run" in result["stdout"]


def test_sha256_is_stable(tmp_path: Path):
    p = tmp_path / "artifact.gguf"
    p.write_bytes(b"LEONES")
    assert len(sha256_file(p)) == 64
    assert sha256_file(p) == sha256_file(p)


def test_summary_contains_median_and_stdev():
    measurements = [
        {"ttft_ms": None, "generation_time_ms": 100, "tokens_per_second": 10, "total_time_ms": 110, "peak_memory_mb": 100, "peak_vram_mb": None, "power_w": None},
        {"ttft_ms": None, "generation_time_ms": 120, "tokens_per_second": 12, "total_time_ms": 140, "peak_memory_mb": 110, "peak_vram_mb": None, "power_w": None},
    ]
    out = summary(measurements)
    assert "ttft_ms" not in out
    assert out["tokens_per_second"]["median"] == 11
    assert "stdev" in out["generation_time_ms"]


def test_command_output_limit_is_read_from_llama_cli_command():
    command = ["llama-cli", "-m", "model.gguf", "-p", "hello", "--single-turn", "-n", "128"]
    assert command_output_token_limit(command) == 128


def test_cpu_backend_is_inferred_when_no_gpu_layers_are_requested():
    assert infer_backend(["llama-cli", "-m", "model.gguf", "-n", "128"], None) == "cpu"
    assert infer_backend(["llama-cli", "-ngl", "0"], None) == "cpu"
    assert infer_backend(["llama-cli", "-ngl", "12"], None) == "gpu"


def test_runtime_revision_is_extracted_from_version():
    assert runtime_revision("version: 0.3.0-dev (build 10655, commit cb300598d)") == "cb300598d"


def test_hardware_has_a_nonempty_cpu_identity():
    assert hardware()["cpu"]


def test_schema_example_is_json():
    schema = Path("schemas/runtime-benchmark-evidence.v1.1.json")
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["$id"] == "runtime-benchmark-evidence.v1.1"
    assert "protocol_id" in payload["properties"]["protocol"]["required"]
    assert "protocol_sha256" in payload["properties"]["protocol"]["required"]
    assert "cooldown_seconds" in payload["properties"]["protocol"]["required"]
    assert payload["properties"]["measurements"]["minItems"] == 5
