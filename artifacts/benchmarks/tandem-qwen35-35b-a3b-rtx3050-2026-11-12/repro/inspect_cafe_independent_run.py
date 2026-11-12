#!/usr/bin/env python3
"""Inspect an existing cafe-llama.cpp independent run without contacting the model."""
from __future__ import annotations

import argparse
import json
import pathlib


RESOURCE_KEYS = (
    "cpu_system_pct_avg_over_interval",
    "process_cpu_pct_avg_over_interval",
    "gpu_util_pct",
    "gpu_memory_util_pct",
    "vram_used_mib",
    "gpu_temperature_c",
    "gpu_power_w",
    "swap_in_bytes_delta_system_wide",
    "swap_out_bytes_delta_system_wide",
    "gpu_sample_count",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=pathlib.Path)
    parser.add_argument("--show-content", action="store_true")
    args = parser.parse_args()

    root = args.run_dir.expanduser().resolve()
    manifest_path = root / "manifest.json"
    response_path = root / "responses/independent-two-sum.json"
    samples_path = root / "resources/resource_samples.jsonl"
    for path in (manifest_path, response_path, samples_path):
        if not path.is_file():
            raise SystemExit(f"Required evidence file missing: {path}")

    manifest = json.loads(manifest_path.read_text())
    record = json.loads(response_path.read_text())
    resource = record.get("resource_metrics") or {}
    response = record.get("response") or {}
    choices = response.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}

    print("=== RUN IDENTITY ===")
    print(json.dumps({
        "experiment": manifest.get("experiment"),
        "methodology": manifest.get("methodology"),
        "engine": manifest.get("engine"),
        "build": manifest.get("build"),
        "model": manifest.get("model"),
        "server_pid": manifest.get("server_pid"),
        "created_at": manifest.get("created_at"),
        "started_at": record.get("started_at"),
        "finished_at": record.get("finished_at"),
    }, ensure_ascii=False, indent=2))

    print("\n=== RESPONSE METRICS ===")
    print(json.dumps({
        "error": record.get("error"),
        "finish_reason": choice.get("finish_reason"),
        "usage": response.get("usage"),
        "timings": response.get("timings"),
        "recorded_metrics": record.get("metrics"),
        "reasoning_chars": len(message.get("reasoning_content") or ""),
        "content_chars": len(message.get("content") or ""),
    }, ensure_ascii=False, indent=2))

    print("\n=== RESOURCE METRICS ===")
    print(json.dumps({key: resource.get(key) for key in RESOURCE_KEYS},
                     ensure_ascii=False, indent=2))
    print(f"\nResource samples: {sum(1 for _ in samples_path.open(encoding='utf-8'))}")
    print("Note: disk and swap deltas from resource_monitor are system-wide.")

    if args.show_content:
        print("\n=== FINAL CONTENT ===")
        print(message.get("content") or "(no final content)")
        print("\n=== REASONING CONTENT ===")
        print(message.get("reasoning_content") or "(not separately exposed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
