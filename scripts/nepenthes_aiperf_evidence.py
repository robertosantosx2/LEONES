#!/usr/bin/env python3
"""Convert an imported AIPerf run into canonical NEPENTHES paired-overhead evidence."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import sys
from pathlib import Path
from statistics import median
from typing import Any

try:
    from nepenthes_aiperf_import import import_aiperf
    from runtime_benchmark_evidence import hardware
    from nepenthes_privacy import assert_safe_metadata
except ModuleNotFoundError:
    from scripts.nepenthes_aiperf_import import import_aiperf
    from scripts.runtime_benchmark_evidence import hardware
    from scripts.nepenthes_privacy import assert_safe_metadata


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict]:
    result = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number}: expected object")
                result.append(value)
    return result


def scalar(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        values = [float(item) for item in value if isinstance(item, (int, float)) and not isinstance(item, bool)]
        return median(values) if values else None
    return None


def time_ms(value: Any, unit: str | None) -> float | None:
    number = scalar(value)
    if number is None:
        return None
    unit = (unit or "ms").strip().lower()
    factors = {"ms": 1.0, "millisecond": 1.0, "milliseconds": 1.0,
               "s": 1000.0, "sec": 1000.0, "seconds": 1000.0,
               "us": 0.001, "µs": 0.001, "microseconds": 0.001,
               "ns": 0.000001}
    if unit not in factors:
        raise ValueError(f"unsupported time unit: {unit}")
    return number * factors[unit]


def throughput_tps(value: Any, unit: str | None) -> float | None:
    number = scalar(value)
    if number is None:
        return None
    unit = (unit or "tokens/s").strip().lower().replace(" ", "")
    factors = {"tokens/s": 1.0, "token/s": 1.0, "tokens/sec": 1.0,
               "tok/s": 1.0, "ktokens/s": 1000.0, "k_tokens/s": 1000.0}
    if unit not in factors:
        raise ValueError(f"unsupported throughput unit: {unit}")
    return number * factors[unit]


def memory_mb(value: Any, unit: str | None) -> float | None:
    number = scalar(value)
    if number is None:
        return None
    unit = (unit or "MB").strip().lower()
    factors = {"mb": 1.0, "mib": 1.0, "gb": 1024.0, "gib": 1024.0}
    if unit not in factors:
        raise ValueError(f"unsupported memory unit: {unit}")
    return number * factors[unit]


def metric_map(events: list[dict], event_kind: str, scope: str) -> dict[str, dict]:
    result = {}
    for event in events:
        if event.get("event_kind") == event_kind and event.get("scope") == scope:
            name = event.get("metric_name")
            if isinstance(name, str):
                result[name] = event
    return result


def build_evidence(args: argparse.Namespace) -> dict:
    artifacts_dir = args.artifacts_dir.expanduser().resolve()
    import_dir = args.import_dir.expanduser().resolve()
    if import_dir.exists() and any(import_dir.iterdir()):
        raise ValueError(f"AIPerf import directory is not empty: {import_dir}")
    import_report = import_aiperf(artifacts_dir, import_dir)
    events = read_jsonl(import_dir / "aiperf_events.jsonl")
    run_manifest = read_json(artifacts_dir / "nepenthes_aiperf_run.json")
    if run_manifest.get("status") != "completed" or run_manifest.get("exit_code") != 0:
        raise ValueError("AIPerf run did not complete successfully")
    if import_report.get("status") != "imported":
        raise ValueError("AIPerf artifacts were not imported successfully")
    if import_report.get("failed_request_count", 0):
        raise ValueError("AIPerf import contains failed requests")
    if import_report.get("source_artifacts") is None:
        raise ValueError("AIPerf importer did not provide source artifact hashes")

    summary = metric_map(events, "aiperf_metric", "run_summary")
    request_metrics: dict[str, dict[str, dict]] = {}
    request_phases: dict[str, str] = {}
    warmup_ids = set()
    for event in events:
        if event.get("event_kind") == "aiperf_metric" and event.get("scope") == "request":
            request_id = str(event.get("request_id", ""))
            if not request_id:
                continue
            name = event.get("metric_name")
            if not isinstance(name, str):
                continue
            request_metrics.setdefault(request_id, {})[name] = event
            phase = (event.get("metadata") or {}).get("benchmark_phase")
            if phase:
                request_phases[request_id] = str(phase).lower()
                if str(phase).lower() == "warmup":
                    warmup_ids.add(request_id)
        if event.get("event_kind") == "aiperf_request_error":
            request_id = str(event.get("request_id", ""))
            if request_id:
                request_phases[request_id] = "failed"

    warmup_evidence = bool(warmup_ids) or any(
        event.get("event_kind") == "aiperf_server_metric_aggregate"
        and event.get("scope") == "server_warmup_aggregate"
        for event in events
    )
    if not warmup_evidence:
        raise ValueError("AIPerf warm-up phase is not present in exported evidence")

    measurements = []
    for request_id, metrics in sorted(request_metrics.items()):
        phase = request_phases.get(request_id, "profiling")
        if phase == "warmup":
            continue
        if phase == "failed":
            raise ValueError(f"AIPerf request failed: {request_id}")
        def value(name: str):
            item = metrics.get(name)
            return (item.get("value"), item.get("unit")) if item else (None, None)
        ttft_value, ttft_unit = value("time_to_first_token")
        itl_value, itl_unit = value("inter_token_latency")
        latency_value, latency_unit = value("request_latency")
        tps_value, tps_unit = value("output_token_throughput")
        input_value, _ = value("input_sequence_length")
        output_value, _ = value("output_sequence_length")
        ttft = time_ms(ttft_value, ttft_unit)
        itl = time_ms(itl_value, itl_unit)
        total = time_ms(latency_value, latency_unit)
        tps = throughput_tps(tps_value, tps_unit)
        measurement = {"request_id": request_id, "exit_code": 0}
        if ttft is not None:
            measurement["ttft_ms"] = ttft
        if itl is not None:
            measurement["inter_token_latency_ms"] = itl
        if total is not None:
            measurement["total_time_ms"] = total
        if total is not None and ttft is not None and total >= ttft:
            measurement["generation_time_ms"] = total - ttft
        if tps is not None:
            measurement["tokens_per_second"] = tps
        if input_value is not None:
            measurement["input_tokens"] = scalar(input_value)
        if output_value is not None:
            measurement["output_tokens"] = scalar(output_value)
        measurements.append(measurement)

    if len(measurements) < 3:
        raise ValueError(f"only {len(measurements)} profiling requests; at least three are required")
    if any("ttft_ms" not in item for item in measurements):
        raise ValueError("one or more profiling requests lack time_to_first_token")

    def summary_metric(names: tuple[str, ...], convert):
        for name in names:
            item = summary.get(name)
            if item:
                result = convert(item.get("value"), item.get("unit"))
                if result is not None:
                    return result
        return None

    run_metrics = {}
    tps = summary_metric(("output_token_throughput", "output_token_throughput_avg"), throughput_tps)
    if tps is None:
        values = [item["tokens_per_second"] for item in measurements if item.get("tokens_per_second") is not None]
        tps = median(values) if values else None
    if tps is None or tps <= 0:
        raise ValueError("AIPerf output_token_throughput is required; no derived throughput is substituted")
    run_metrics["tokens_per_second"] = tps

    ttft_summary = summary_metric(("time_to_first_token",), time_ms)
    if ttft_summary is None:
        ttft_values = [item["ttft_ms"] for item in measurements if item.get("ttft_ms") is not None]
        ttft_summary = median(ttft_values) if ttft_values else None
    if ttft_summary is not None:
        run_metrics["ttft_ms"] = ttft_summary
    latency_summary = summary_metric(("request_latency",), time_ms)
    if latency_summary is not None:
        run_metrics["request_latency_mean_ms"] = latency_summary
    started_at = run_manifest.get("started_at")
    finished_at = run_manifest.get("finished_at")
    if not isinstance(started_at, str) or not isinstance(finished_at, str):
        raise ValueError("AIPerf run manifest must contain started_at and finished_at for total campaign duration")
    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finish_time = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    if finish_time <= start_time:
        raise ValueError("AIPerf run finished_at must be later than started_at")
    run_metrics["total_time_ms"] = (finish_time - start_time).total_seconds() * 1000.0
    generation_values = [item["generation_time_ms"] for item in measurements if "generation_time_ms" in item]
    if generation_values:
        run_metrics["generation_time_ms"] = median(generation_values)

    resource = run_manifest.get("resource_telemetry", {})
    if resource.get("rss_target") != "inference_server":
        raise ValueError("AIPerf runner must monitor the inference server PID via --target-pid or --target-pid-file")
    for key in ("peak_process_rss_mb", "peak_system_ram_used_mb", "peak_vram_mb_device_wide"):
        value = resource.get(key)
        if value is None or float(value) <= 0:
            raise ValueError(f"inference-server resource telemetry missing: {key}")
        run_metrics[key] = float(value)
    for key in ("mean_power_w", "peak_power_w"):
        if resource.get(key) is not None:
            run_metrics[key] = float(resource[key])
    if resource.get("gpu_sample_count") is not None:
        run_metrics["gpu_sample_count"] = int(resource["gpu_sample_count"])

    profile = run_manifest.get("profile", {})
    target = run_manifest.get("target", {})
    if target.get("model") != args.model_id:
        raise ValueError("AIPerf target model does not match --model-id")
    if profile.get("request_count") is not None and int(profile["request_count"]) != len(measurements):
        raise ValueError("AIPerf profiling request count does not match exported request records")
    sampling_config = json.loads(args.sampling_config_json.read_text(encoding="utf-8")) if args.sampling_config_json else {}
    if not isinstance(sampling_config, dict):
        raise ValueError("--sampling-config-json must contain an object")
    assert_safe_metadata(sampling_config, "sampling_config")
    dataset_descriptor = {
        "aiperf_version": run_manifest.get("aiperf_version"),
        "profile": profile,
        "endpoint_type": target.get("endpoint_type"),
        "streaming": target.get("streaming"),
        "sampling_config": sampling_config,
    }
    dataset_sha = args.dataset_sha256 or hashlib.sha256(
        json.dumps(dataset_descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    workload_command_sha256 = run_manifest.get("workload_command_sha256")
    if not isinstance(workload_command_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", workload_command_sha256):
        raise ValueError("AIPerf run manifest lacks a valid normalized workload command SHA-256")
    model_sha = sha256_file(args.model_artifact.expanduser().resolve())
    hardware_info = hardware()
    host_sample_ms = resource.get("host_sample_ms")
    gpu_sample_ms = resource.get("gpu_sample_ms")
    if not isinstance(host_sample_ms, int) or not isinstance(gpu_sample_ms, int):
        raise ValueError("AIPerf resource sampling intervals are missing from run manifest")

    evidence = {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": run_manifest.get("run_id"),
        "created_at": run_manifest.get("finished_at"),
        "model": {
            "id": args.model_id,
            "name": args.model_name,
            "revision": args.model_revision,
            "quantization": args.quantization,
            "context_length": args.context,
        },
        "artifact": {"path": args.model_artifact.name, "sha256": model_sha},
        "runtime": {
            "name": args.engine_name,
            "version": args.engine_version,
            "revision": args.engine_revision,
            "backend": args.backend,
            "command_sha256": workload_command_sha256,
        },
        "hardware": hardware_info,
        "protocol": {
            "prompt_protocol_id": "aiperf-synthetic-v1",
            "dataset_sha256": dataset_sha,
            "context": args.context,
            "input_tokens": profile.get("input_tokens_mean"),
            "output_token_limit": profile.get("output_tokens_mean"),
            "temperature": sampling_config.get("temperature"),
            "top_p": sampling_config.get("top_p"),
            "seed": sampling_config.get("seed"),
            "dataset_seed": profile.get("random_seed"),
            "warmup_iterations": len(warmup_ids) if warmup_ids else 1,
            "warmup_count_exact": bool(warmup_ids),
            "warmup_evidence_source": "request_records" if warmup_ids else "server_warmup_aggregate",
            "measurement_iterations": len(measurements),
        },
        "instrumentation": {
            "condition": args.condition,
            "pair_id": args.pair_id,
            "profile": args.profile,
            "dataset_sha256": dataset_sha,
            "hardware_id": args.hardware_id,
            "rss_target": "inference_server",
            "sampling_config": sampling_config,
            "host_sample_ms": host_sample_ms,
            "gpu_sample_ms": gpu_sample_ms,
        },
        "run_metrics": run_metrics,
        "measurements": measurements,
        "process": {"exit_code": 0},
        "aiperf": {
            "version": run_manifest.get("aiperf_version"),
            "run_id": import_report.get("run_id"),
            "source_artifacts": import_report.get("source_artifacts"),
            "import_report": import_report,
        },
    }
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--import-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--quantization", required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--engine-name", default="llama.cpp")
    parser.add_argument("--engine-version", required=True)
    parser.add_argument("--engine-revision", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--hardware-id", required=True)
    parser.add_argument("--condition", choices=("off", "jsonl", "nsys", "combined"), required=True)
    parser.add_argument("--pair-id", required=True)
    parser.add_argument("--profile", choices=("smoke", "standard", "full", "moe-deep", "latency-critical"), default="standard")
    parser.add_argument("--dataset-sha256", default=None)
    parser.add_argument("--sampling-config-json", type=Path, default=None)
    args = parser.parse_args()
    evidence = build_evidence(args)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "execution_id": evidence.get("execution_id"),
        "measurement_iterations": evidence["protocol"]["measurement_iterations"],
        "condition": evidence["instrumentation"]["condition"],
        "pair_id": evidence["instrumentation"]["pair_id"],
        "dataset_sha256": evidence["instrumentation"]["dataset_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
