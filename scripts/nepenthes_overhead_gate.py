#!/usr/bin/env python3
"""Paired baseline/sink/Nsight overhead gate for NEPENTHES benchmark evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median


CONDITIONS = ("off", "jsonl", "nsys", "combined")
METRICS = (
    "tokens_per_second",
    "ttft_ms",
    "generation_time_ms",
    "total_time_ms",
    "peak_process_rss_mb",
    "peak_system_ram_used_mb",
    "peak_vram_mb_device_wide",
    "mean_power_w",
    "peak_power_w",
)
LOWER_IS_BETTER = set(METRICS) - {"tokens_per_second"}


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires values")
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def robust_summary(values: list[float]) -> dict:
    med = median(values)
    p25 = percentile(values, 0.25)
    p75 = percentile(values, 0.75)
    return {
        "n": len(values),
        "median": med,
        "p25": p25,
        "p75": p75,
        "iqr": p75 - p25,
        "mad": median([abs(value - med) for value in values]),
        "min": min(values),
        "max": max(values),
    }


def config_fingerprint(evidence: dict) -> dict:
    model = evidence.get("model", {})
    protocol = evidence.get("protocol", {})
    runtime = evidence.get("runtime", {})
    instrumentation = evidence.get("instrumentation", {})
    return {
        "model": {
            "id": model.get("id"),
            "revision": model.get("revision"),
            "quantization": model.get("quantization"),
            "context_length": model.get("context_length"),
            "artifact_sha256": evidence.get("artifact", {}).get("sha256"),
        },
        "protocol": {
            "prompt_protocol_id": protocol.get("prompt_protocol_id"),
            "prompt_sha256": protocol.get("prompt_sha256"),
            "context": protocol.get("context"),
            "warmup_iterations": protocol.get("warmup_iterations"),
            "measurement_iterations": protocol.get("measurement_iterations"),
            "input_tokens": protocol.get("input_tokens"),
            "output_token_limit": protocol.get("output_token_limit"),
            "temperature": protocol.get("temperature"),
            "top_p": protocol.get("top_p"),
            "seed": protocol.get("seed"),
        },
        "runtime": {
            "name": runtime.get("name"),
            "version": runtime.get("version"),
            "revision": runtime.get("revision"),
            "backend": runtime.get("backend"),
        },
        "hardware": evidence.get("hardware"),
        "instrumentation": {
            "profile": instrumentation.get("profile"),
            "dataset_sha256": instrumentation.get("dataset_sha256"),
            "hardware_id": instrumentation.get("hardware_id"),
            "sampling_config": instrumentation.get("sampling_config", {}),
            "host_sample_ms": instrumentation.get("host_sample_ms"),
            "gpu_sample_ms": instrumentation.get("gpu_sample_ms"),
        },
    }


def evidence_metrics(evidence: dict) -> dict[str, float]:
    measurements = evidence.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        raise ValueError("measurements must be a non-empty array")
    if evidence.get("process", {}).get("exit_code") != 0:
        raise ValueError("process exit_code is not zero")
    if any(item.get("exit_code") != 0 for item in measurements):
        raise ValueError("one or more measurement iterations failed")
    result = {}
    for metric in METRICS:
        values = [float(item[metric]) for item in measurements if item.get(metric) is not None]
        if values:
            result[metric] = median(values)
    if "tokens_per_second" not in result or result["tokens_per_second"] <= 0:
        raise ValueError("tokens_per_second missing or non-positive")
    return result


def load_evidence(paths: list[Path], profile: str) -> tuple[dict, list[str]]:
    groups = {condition: {} for condition in CONDITIONS}
    errors = []
    fingerprints = []
    for path in paths:
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        if evidence.get("schema") != "runtime-benchmark-evidence.v1.1":
            errors.append(f"{path}: unsupported evidence schema")
            continue
        metadata = evidence.get("instrumentation", {})
        condition = metadata.get("condition")
        pair_id = metadata.get("pair_id")
        evidence_profile = metadata.get("profile")
        if condition not in CONDITIONS:
            errors.append(f"{path}: invalid instrumentation.condition")
            continue
        if not isinstance(pair_id, str) or not pair_id.strip():
            errors.append(f"{path}: pair_id is required for paired overhead analysis")
            continue
        if evidence_profile != profile:
            errors.append(f"{path}: profile mismatch ({evidence_profile!r} != {profile!r})")
            continue
        if pair_id in groups[condition]:
            errors.append(f"{path}: duplicate pair_id {pair_id!r} for {condition}")
            continue
        try:
            metrics = evidence_metrics(evidence)
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        groups[condition][pair_id] = {
            "path": str(path),
            "execution_id": evidence.get("execution_id"),
            "metrics": metrics,
        }
        fingerprints.append((str(path), config_fingerprint(evidence)))
    if fingerprints:
        baseline = fingerprints[0][1]
        for path, fingerprint in fingerprints[1:]:
            if fingerprint != baseline:
                errors.append(f"{path}: benchmark configuration differs from the paired baseline")
    pair_sets = {condition: set(items) for condition, items in groups.items()}
    nonempty_sets = [items for items in pair_sets.values() if items]
    if len(nonempty_sets) != len(CONDITIONS):
        missing = [condition for condition, items in pair_sets.items() if not items]
        errors.append("missing measurement condition(s): " + ", ".join(missing))
    elif any(items != nonempty_sets[0] for items in nonempty_sets[1:]):
        errors.append("pair_id sets differ between baseline and instrumentation conditions")
    return groups, errors


def compare(groups: dict, profile: str, min_pairs: int,
            max_overhead: float, warn_overhead: float, errors: list[str]) -> dict:
    report = {
        "schema": "nepenthes-overhead-gate.v1",
        "profile": profile,
        "conditions": {},
        "errors": list(errors),
        "gate": {
            "minimum_paired_repetitions": min_pairs,
            "standard_decode_overhead_target_pct": max_overhead,
            "standard_decode_overhead_exception_limit_pct": warn_overhead,
            "standard_profile_only": True,
        },
    }
    pair_ids = sorted(set(groups.get("off", {})))
    if len(pair_ids) < min_pairs:
        report["errors"].append(
            f"only {len(pair_ids)} paired repetitions; at least {min_pairs} required"
        )
    baseline = groups.get("off", {})
    overall = "accepted"
    for condition in ("jsonl", "nsys", "combined"):
        entries = groups.get(condition, {})
        condition_report = {"paired_repetitions": len(entries), "metrics": {}}
        decode_deltas = []
        for pair_id in pair_ids:
            if pair_id not in baseline or pair_id not in entries:
                continue
            base_metrics = baseline[pair_id]["metrics"]
            test_metrics = entries[pair_id]["metrics"]
            for metric in METRICS:
                if metric not in base_metrics or metric not in test_metrics:
                    continue
                base_value = base_metrics[metric]
                test_value = test_metrics[metric]
                if base_value <= 0:
                    continue
                delta = ((base_value - test_value) / base_value * 100
                         if metric == "tokens_per_second"
                         else (test_value - base_value) / base_value * 100)
                condition_report["metrics"].setdefault(metric, []).append({
                    "pair_id": pair_id,
                    "baseline_median": base_value,
                    "condition_median": test_value,
                    "overhead_pct": delta,
                })
                if metric == "tokens_per_second":
                    decode_deltas.append(delta)
        for metric, records in list(condition_report["metrics"].items()):
            condition_report["metrics"][metric] = {
                "paired_deltas": records,
                "overhead_pct": robust_summary([item["overhead_pct"] for item in records]),
            }
        if profile != "standard":
            condition_report["gate_status"] = "informational_only"
        elif len(decode_deltas) < min_pairs:
            condition_report["gate_status"] = "blocked"
            report["errors"].append(f"{condition}: insufficient paired decode-throughput measurements")
            overall = "blocked"
        else:
            decode_stats = robust_summary(decode_deltas)
            condition_report["decode_overhead_median_pct"] = decode_stats["median"]
            if decode_stats["median"] > warn_overhead:
                condition_report["gate_status"] = "blocked"
                overall = "blocked"
            elif decode_stats["median"] > max_overhead:
                condition_report["gate_status"] = "exception_required"
                if overall != "blocked":
                    overall = "exception_required"
            else:
                condition_report["gate_status"] = "accepted"
        report["conditions"][condition] = condition_report
    if report["errors"]:
        overall = "blocked"
    if profile != "standard" and not report["errors"]:
        overall = "informational_only"
    report["overall_status"] = overall
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, nargs="+", required=True)
    parser.add_argument("--profile", choices=("smoke", "standard", "full", "moe-deep", "latency-critical"), default="standard")
    parser.add_argument("--min-pairs", type=int, default=3)
    parser.add_argument("--max-decode-overhead", type=float, default=5.0)
    parser.add_argument("--warn-decode-overhead", type=float, default=8.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.min_pairs < 3:
        raise SystemExit("--min-pairs cannot be lower than 3")
    if args.warn_decode_overhead < args.max_decode_overhead:
        raise SystemExit("warn-decode-overhead must be >= max-decode-overhead")
    groups, errors = load_evidence(args.evidence, args.profile)
    report = compare(groups, args.profile, args.min_pairs,
                     args.max_decode_overhead, args.warn_decode_overhead, errors)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    if report["overall_status"] == "accepted" or report["overall_status"] == "informational_only":
        return 0
    if report["overall_status"] == "exception_required":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
