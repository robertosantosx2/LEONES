import json
from pathlib import Path

from scripts.nepenthes_overhead_gate import compare, load_evidence, robust_summary


def evidence(condition, pair_id, tps, ttft=100.0):
    measurements = []
    for iteration in range(1, 4):
        measurements.append({
            "iteration": iteration,
            "exit_code": 0,
            "tokens_per_second": tps,
            "ttft_ms": ttft,
            "generation_time_ms": 1000.0,
            "total_time_ms": 1100.0,
            "peak_process_rss_mb": 2048.0,
            "peak_system_ram_used_mb": 8192.0,
            "peak_vram_mb_device_wide": 3000.0,
            "mean_power_w": 65.0,
            "peak_power_w": 75.0,
        })
    return {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": f"{condition}-{pair_id}",
        "model": {
            "id": "model-q4",
            "revision": "immutable-model-revision",
            "quantization": "Q4_K_M",
            "context_length": 4096,
        },
        "artifact": {"sha256": "a" * 64},
        "protocol": {
            "prompt_protocol_id": "nepenthes-c08-v1",
            "prompt_sha256": "b" * 64,
            "context": 4096,
            "warmup_iterations": 1,
            "measurement_iterations": 3,
            "input_tokens": 512,
            "output_token_limit": 256,
            "temperature": 0,
            "top_p": 1,
            "seed": 42,
        },
        "runtime": {
            "name": "llama.cpp",
            "version": "test-build",
            "revision": "engine-sha",
            "backend": "cuda",
        },
        "hardware": {
            "os": "Ubuntu",
            "kernel": "test-kernel",
            "architecture": "x86_64",
            "cpu": "test-cpu",
            "ram_total_mb": 14336,
            "gpu": "RTX 3050 Laptop, 4096 MiB",
        },
        "instrumentation": {
            "condition": condition,
            "pair_id": pair_id,
            "profile": "standard",
            "dataset_sha256": "c" * 64,
            "hardware_id": "msi-test-rig",
            "sampling_config": {"host": False, "nvml": False},
            "host_sample_ms": 100,
            "gpu_sample_ms": 500,
        },
        "measurements": measurements,
        "process": {"exit_code": 0},
    }


def write_group(tmp_path: Path, rates):
    paths = []
    for condition, tps in rates.items():
        for pair_id in ("pair-1", "pair-2", "pair-3"):
            path = tmp_path / f"{condition}-{pair_id}.json"
            path.write_text(json.dumps(evidence(condition, pair_id, tps)), encoding="utf-8")
            paths.append(path)
    return paths


def test_robust_summary_reports_median_iqr_and_mad():
    result = robust_summary([1.0, 2.0, 3.0, 100.0])
    assert result["median"] == 2.5
    assert result["iqr"] == 25.5
    assert result["mad"] == 1.0


def test_standard_overhead_gate_accepts_decode_overhead_at_or_below_five_percent(tmp_path):
    paths = write_group(tmp_path, {"off": 100, "jsonl": 96, "nsys": 97, "combined": 95})
    groups, errors = load_evidence(paths, "standard")
    report = compare(groups, "standard", 3, 5.0, 8.0, errors)
    assert report["overall_status"] == "accepted"
    assert report["conditions"]["combined"]["decode_overhead_median_pct"] == 5.0
    assert report["conditions"]["jsonl"]["metrics"]["ttft_ms"]["overhead_pct"]["median"] == 0


def test_standard_overhead_gate_requires_exception_between_five_and_eight_percent(tmp_path):
    paths = write_group(tmp_path, {"off": 100, "jsonl": 96, "nsys": 94, "combined": 93})
    groups, errors = load_evidence(paths, "standard")
    report = compare(groups, "standard", 3, 5.0, 8.0, errors)
    assert report["overall_status"] == "exception_required"
    assert report["conditions"]["combined"]["gate_status"] == "exception_required"


def test_standard_overhead_gate_blocks_above_eight_percent(tmp_path):
    paths = write_group(tmp_path, {"off": 100, "jsonl": 96, "nsys": 94, "combined": 91})
    groups, errors = load_evidence(paths, "standard")
    report = compare(groups, "standard", 3, 5.0, 8.0, errors)
    assert report["overall_status"] == "blocked"
    assert report["conditions"]["combined"]["gate_status"] == "blocked"


def test_overhead_gate_rejects_unpaired_conditions(tmp_path):
    paths = write_group(tmp_path, {"off": 100, "jsonl": 96, "nsys": 97, "combined": 95})
    remove = tmp_path / "nsys-pair-3.json"
    remove.unlink()
    paths = [path for path in paths if path != remove]
    groups, errors = load_evidence(paths, "standard")
    report = compare(groups, "standard", 3, 5.0, 8.0, errors)
    assert errors
    assert report["overall_status"] == "blocked"


def test_non_standard_profile_is_informational_not_low_overhead_claim(tmp_path):
    paths = []
    for condition, tps in {"off": 100, "jsonl": 80, "nsys": 70, "combined": 60}.items():
        for pair_id in ("pair-1", "pair-2", "pair-3"):
            payload = evidence(condition, pair_id, tps)
            payload["instrumentation"]["profile"] = "full"
            path = tmp_path / f"full-{condition}-{pair_id}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths.append(path)
    groups, errors = load_evidence(paths, "full")
    report = compare(groups, "full", 3, 5.0, 8.0, errors)
    assert report["overall_status"] == "informational_only"


def test_overhead_gate_rejects_model_or_hardware_configuration_mismatch(tmp_path):
    paths = write_group(tmp_path, {"off": 100, "jsonl": 96, "nsys": 97, "combined": 95})
    changed = tmp_path / "combined-pair-2.json"
    payload = json.loads(changed.read_text(encoding="utf-8"))
    payload["hardware"]["gpu"] = "different GPU"
    changed.write_text(json.dumps(payload), encoding="utf-8")
    groups, errors = load_evidence(paths, "standard")
    report = compare(groups, "standard", 3, 5.0, 8.0, errors)
    assert any("configuration differs" in error for error in errors)
    assert report["overall_status"] == "blocked"


def test_overhead_gate_rejects_less_than_three_measurement_iterations(tmp_path):
    payload = evidence("off", "pair-1", 100)
    payload["measurements"] = payload["measurements"][:2]
    payload["protocol"]["measurement_iterations"] = 2
    path = tmp_path / "too-few.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    groups, errors = load_evidence([path], "standard")
    assert any("at least three measurement iterations" in error for error in errors)
