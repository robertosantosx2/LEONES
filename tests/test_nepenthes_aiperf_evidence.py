from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.nepenthes_aiperf_evidence import build_evidence


def write_aiperf_bundle(root: Path, include_warmup: bool = True, include_throughput: bool = True):
    root.mkdir(parents=True, exist_ok=True)
    summary_metrics = {
        "time_to_first_token": {"unit": "ms", "avg": 101.5, "count": 4},
        "request_latency": {"unit": "ms", "avg": 501.5, "count": 4},
    }
    if include_throughput:
        summary_metrics["output_token_throughput"] = {"unit": "tokens/s", "avg": 31.5, "count": 4}
    summary = {
        "schema_version": "1.7",
        "aiperf_version": "0.13.0",
        "benchmark_id": "bench-c08-001",
        "start_time": "2026-11-19T07:00:00Z",
        "end_time": "2026-11-19T07:00:10Z",
        **summary_metrics,
        "run_info": {"benchmark_id": "bench-c08-001", "random_seed": 42},
    }
    (root / "profile_export_aiperf.json").write_text(json.dumps(summary), encoding="utf-8")

    records = []
    for index in range(4):
        metrics = {
            "time_to_first_token": {"value": 100.0 + index, "unit": "ms"},
            "inter_token_latency": {"value": 10.0 + index, "unit": "ms"},
            "request_latency": {"value": 500.0 + index, "unit": "ms"},
            "input_sequence_length": {"value": 128, "unit": "tokens"},
            "output_sequence_length": {"value": 32, "unit": "tokens"},
        }
        if include_throughput:
            metrics["output_token_throughput"] = {"value": 31.0 + index, "unit": "tokens/s"}
        records.append({
            "metadata": {
                "session_num": index + 1,
                "x_request_id": f"req-{index + 1}",
                "benchmark_phase": "profiling",
            },
            "metrics": metrics,
            "error": None,
        })
    (root / "profile_export.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )

    aggregate = {
        "schema_version": "1.1",
        "aiperf_version": "0.13.0",
        "benchmark_id": "bench-c08-001",
        "summary": {"phase_time_ranges": {
            "profiling": {"start_ns": 1000, "end_ns": 5000},
            "warmup": {"start_ns": 100, "end_ns": 900},
        }},
        "metrics": {},
    }
    if include_warmup:
        aggregate["warmup_metrics"] = {
            "llama_active_slots": {
                "type": "gauge", "description": "Active slots", "unit": "requests",
                "series": [{"labels": {"model": "model-q4"}, "stats": {"avg": 0.0}}],
            }
        }
    (root / "server_metrics_export.json").write_text(json.dumps(aggregate), encoding="utf-8")


def make_args(tmp_path: Path, include_warmup: bool = True, include_throughput: bool = True):
    artifacts = tmp_path / "artifacts"
    write_aiperf_bundle(artifacts, include_warmup, include_throughput)
    import_dir = tmp_path / "imported"
    model_artifact = tmp_path / "model.gguf"
    model_artifact.write_bytes(b"synthetic model artifact for test")
    sampling = tmp_path / "sampling.json"
    sampling.write_text(json.dumps({"temperature": 0, "top_p": 1, "seed": 42}), encoding="utf-8")
    run_manifest = {
        "status": "completed",
        "run_id": "aiperf-execution-001",
        "exit_code": 0,
        "started_at": "2026-11-19T07:00:00Z",
        "finished_at": "2026-11-19T07:00:10Z",
        "workload_command_sha256": "c" * 64,
        "aiperf_version": "0.13.0",
        "target": {"model": "model-q4", "url": "http://127.0.0.1:8080", "endpoint_type": "chat", "streaming": True},
        "profile": {
            "concurrency": 1, "request_count": 4,
            "warmup_request_count": 1,
            "input_tokens_mean": 128, "output_tokens_mean": 32,
            "random_seed": 42, "server_metrics_enabled": True,
        },
        "resource_telemetry": {
            "rss_target": "inference_server",
            "host_sample_ms": 100, "gpu_sample_ms": 500,
            "peak_process_rss_mb": 2400,
            "peak_system_ram_used_mb": 9000,
            "peak_vram_mb_device_wide": 3100,
            "mean_power_w": 55.0, "peak_power_w": 70.0,
            "gpu_sample_count": 10,
        },
    }
    (artifacts / "nepenthes_aiperf_run.json").write_text(json.dumps(run_manifest), encoding="utf-8")
    from argparse import Namespace
    return Namespace(
        artifacts_dir=artifacts, import_dir=import_dir, output=tmp_path / "evidence.json",
        model_artifact=model_artifact, model_id="model-q4", model_name="Test Q4",
        model_revision="immutable-model-rev", quantization="Q4_K_M", context=4096,
        engine_name="llama.cpp", engine_version="test-build", engine_revision="engine-sha",
        backend="cuda", hardware_id="test-msi-rtx3050", condition="off", pair_id="pair-1",
        profile="standard", dataset_sha256=None, sampling_config_json=sampling,
    )


def test_aiperf_adapter_emits_canonical_paired_evidence(tmp_path: Path):
    from scripts.nepenthes_aiperf_evidence import build_evidence
    evidence = build_evidence(make_args(tmp_path))
    assert evidence["schema"] == "runtime-benchmark-evidence.v1.1"
    assert evidence["protocol"]["warmup_iterations"] == 1
    assert evidence["protocol"]["measurement_iterations"] == 4
    assert evidence["instrumentation"]["rss_target"] == "inference_server"
    assert evidence["runtime"]["command_sha256"] == "c" * 64
    assert evidence["run_metrics"]["tokens_per_second"] == 31.5
    assert evidence["run_metrics"]["ttft_ms"] == 101.5
    assert evidence["run_metrics"]["total_time_ms"] == 10000.0
    assert evidence["run_metrics"]["request_latency_mean_ms"] == 501.5
    assert evidence["run_metrics"]["peak_process_rss_mb"] == 2400
    assert evidence["run_metrics"]["peak_vram_mb_device_wide"] == 3100
    assert all("ttft_ms" in item for item in evidence["measurements"])
    assert "response_text" not in json.dumps(evidence)
    from scripts.nepenthes_overhead_gate import evidence_metrics
    normalized = evidence_metrics(evidence)
    assert normalized["tokens_per_second"] == 31.5
    assert normalized["peak_system_ram_used_mb"] == 9000


def test_aiperf_adapter_rejects_missing_warmup_evidence(tmp_path: Path):
    with pytest.raises(ValueError, match="warm-up phase"):
        build_evidence(make_args(tmp_path, include_warmup=False))


def test_aiperf_adapter_rejects_missing_decode_throughput_instead_of_estimating(tmp_path: Path):
    with pytest.raises(ValueError, match="output_token_throughput is required"):
        build_evidence(make_args(tmp_path, include_throughput=False))


def test_aiperf_adapter_rejects_missing_or_invalid_workload_fingerprint(tmp_path: Path):
    args = make_args(tmp_path)
    manifest_path = args.artifacts_dir / "nepenthes_aiperf_run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["workload_command_sha256"] = "not-a-sha256"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="valid normalized workload command SHA-256"):
        build_evidence(args)


def test_aiperf_adapter_rejects_non_positive_campaign_duration(tmp_path: Path):
    args = make_args(tmp_path)
    manifest_path = args.artifacts_dir / "nepenthes_aiperf_run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["finished_at"] = manifest["started_at"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="finished_at must be later"):
        build_evidence(args)
