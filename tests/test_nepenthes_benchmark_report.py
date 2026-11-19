from __future__ import annotations

import json

from scripts.nepenthes_benchmark_report import build_report, describe, markdown_report


def sample_events():
    events = []
    requests = [
        ("req-a", 100.0, 10.0, 4.0, 20, 22, 1_800_000_000_000_000_000),
        ("req-b", 200.0, 20.0, 6.0, 30, 32, 1_800_000_000_100_000_000),
    ]
    for request_id, latency, ttft, itl, output_tokens, sequence, start in requests:
        metadata = {"request_start_ns": start, "request_end_ns": start + 100_000_000}
        for name, value, unit in [
            ("request_latency", latency, "ms"),
            ("time_to_first_token", ttft, "ms"),
            ("inter_token_latency", itl, "ms"),
            ("output_token_count", output_tokens, "tokens"),
            ("output_sequence_length", sequence, "tokens"),
        ]:
            events.append({
                "event_kind": "aiperf_metric", "scope": "request",
                "run_id": "run-001", "request_id": request_id,
                "metric_name": name, "value": value, "unit": unit,
                "timestamp_unix_ns": start, "metadata": metadata,
            })
    events.append({
        "event_kind": "aiperf_request_error", "scope": "request",
        "run_id": "run-001", "request_id": "req-c",
        "error": {"code": 499, "message": "private"},
    })
    events.extend([
        {"event_kind": "aiperf_metric", "scope": "run_summary",
         "metric_name": "request_throughput", "value": 0.2, "unit": "requests/sec"},
        {"event_kind": "aiperf_server_metric_sample", "metric_name": "llama_active_slots"},
        {"event_kind": "aiperf_gpu_telemetry", "metric_name": "nvidia_power_usage"},
    ])
    return events


def write_energy(path, *, energy_j, duration, quality="measured_counter", gpu_uuid="GPU-1"):
    path.write_text(json.dumps({
        "duration_seconds": duration,
        "devices": [{"gpu_uuid": gpu_uuid, "energy": {
            "energy_j": energy_j, "quality": quality, "method": "nvml_total_energy_counter"
        }}],
    }), encoding="utf-8")


def test_describe_computes_dispersion_and_interpolated_percentiles():
    result = describe([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["count"] == 5
    assert result["mean"] == 3.0
    assert result["median"] == 3.0
    assert result["stddev_population"] == 2 ** 0.5
    assert result["mad"] == 1.0
    assert result["iqr"] == 2.0
    assert result["p95"] == 4.8
    assert result["p99"] == 4.96


def test_report_aggregates_aiperf_request_latency_tokens_and_failures():
    report = build_report(sample_events())
    assert report["request_count"] == 3
    assert report["successful_request_count"] == 2
    assert report["failed_request_count"] == 1
    assert report["content_output_tokens"] == 50.0
    assert report["completion_sequence_tokens"] == 54.0
    latency = report["request_metrics"]["request_latency"]
    assert latency["count"] == 2 and latency["mean"] == 150.0
    assert latency["p95"] == 195.0
    assert report["request_metrics"]["inter_token_latency"]["mean"] == 5.0
    assert report["server_metric_event_count"] == 1
    assert report["gpu_telemetry_event_count"] == 1


def test_energy_efficiency_uses_matching_device_and_duration_scaled_idle_baseline(tmp_path):
    run = tmp_path / "run-energy.json"
    baseline = tmp_path / "baseline-energy.json"
    write_energy(run, energy_j=100.0, duration=10.0)
    write_energy(baseline, energy_j=20.0, duration=5.0)
    report = build_report(sample_events(), run, baseline)
    energy = report["energy_efficiency"]
    assert energy["status"] == "available"
    assert energy["run_energy_j"] == 100.0
    assert energy["baseline_energy_scaled_j"] == 40.0
    assert energy["incremental_energy_j"] == 60.0
    assert round(energy["tokens_per_joule_content"], 6) == round(50 / 60, 6)
    assert round(energy["tokens_per_joule_sequence"], 6) == 0.9
    assert energy["device_attribution"] == "device_level_not_process_level"


def test_energy_efficiency_refuses_partial_energy_and_unmatched_devices(tmp_path):
    run = tmp_path / "run-energy.json"
    baseline = tmp_path / "baseline-energy.json"
    write_energy(run, energy_j=100.0, duration=10.0, quality="partial_estimate")
    write_energy(baseline, energy_j=20.0, duration=5.0)
    report = build_report(sample_events(), run, baseline)
    assert report["energy_efficiency"]["status"] == "energy_or_baseline_incomplete"
    assert report["energy_efficiency"]["tokens_per_joule_content"] is None
    write_energy(run, energy_j=100.0, duration=10.0)
    write_energy(baseline, energy_j=20.0, duration=5.0, gpu_uuid="GPU-other")
    report = build_report(sample_events(), run, baseline)
    assert report["energy_efficiency"]["status"] == "energy_or_baseline_incomplete"


def test_missing_baseline_keeps_gross_energy_but_no_tokens_per_joule(tmp_path):
    run = tmp_path / "run-energy.json"
    write_energy(run, energy_j=100.0, duration=10.0)
    report = build_report(sample_events(), run, None)
    assert report["energy_efficiency"]["status"] == "baseline_not_provided"
    assert report["energy_efficiency"]["tokens_per_joule_content"] is None


def test_markdown_report_does_not_include_request_ids_or_private_payloads():
    report = build_report(sample_events())
    markdown = markdown_report(report)
    assert "req-a" not in markdown and "req-b" not in markdown
    assert "private" not in markdown
    assert "device-level" in markdown