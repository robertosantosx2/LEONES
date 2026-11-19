#!/usr/bin/env python3
"""Run a conservative, reproducible AIPerf profile for NEPENTHES.

The wrapper never invokes a shell, stores credentials, or exports generated text.
It records the exact non-secret command and execution environment in a manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit

try:
    from runtime_benchmark_evidence import TelemetrySampler
except ModuleNotFoundError:
    from scripts.runtime_benchmark_evidence import TelemetrySampler


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return number


def safe_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be an absolute http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise argparse.ArgumentTypeError("do not embed credentials, query tokens, or fragments in --url")
    return value.rstrip("/")


def build_command(executable: str, args: argparse.Namespace, artifact_dir: Path) -> list[str]:
    command = [
        executable, "profile",
        "--model", args.model,
        "--url", args.url,
        "--endpoint-type", "chat",
        "--streaming",
        "--concurrency", str(args.concurrency),
        "--request-count", str(args.request_count),
        "--synthetic-input-tokens-mean", str(args.input_tokens),
        "--synthetic-input-tokens-stddev", "0",
        "--output-tokens-mean", str(args.output_tokens),
        "--output-tokens-stddev", "0",
        "--random-seed", str(args.random_seed),
        "--export-level", "records",
        "--server-metrics-formats", "json", "jsonl",
        "--gpu-telemetry", "pynvml",
        "--artifact-dir", str(artifact_dir),
    ]
    if args.no_server_metrics:
        command.append("--no-server-metrics")
    return command


def parse_aiperf_version(value: str) -> str | None:
    match = re.search(r"(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+(?:[-+.]?[A-Za-z][0-9A-Za-z.-]*)?)(?![0-9])", value)
    return match.group(1) if match else None


def resolve_executable(value: str) -> str:
    candidate = shutil.which(value)
    if candidate:
        return str(Path(candidate).resolve())
    path = Path(value).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return str(path.resolve())
    raise FileNotFoundError(f"AIPerf executable not found or not executable: {value}")


def write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", required=True, type=safe_url)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--aiperf-bin", default="aiperf")
    parser.add_argument("--expected-aiperf-version", default="0.13.0",
                        help="exact AIPerf version required for a reproducible run (default: 0.13.0)")
    parser.add_argument("--concurrency", type=positive_int, default=1)
    parser.add_argument("--request-count", type=positive_int, default=5)
    parser.add_argument("--input-tokens", type=positive_int, default=128)
    parser.add_argument("--output-tokens", type=positive_int, default=32)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--timeout-seconds", type=positive_int, default=900)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--target-pid", type=positive_int, default=None,
                        help="PID of the inference server to monitor for process RSS")
    target.add_argument("--target-pid-file", type=Path, default=None,
                        help="file containing the inference server PID")
    parser.add_argument("--host-sample-ms", type=positive_int, default=100)
    parser.add_argument("--gpu-sample-ms", type=positive_int, default=500)
    parser.add_argument("--no-server-metrics", action="store_true",
                        help="disable AIPerf scraping of endpoint /metrics")
    parser.add_argument("--dry-run", action="store_true", help="write manifest and print command without launching AIPerf")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    if args.host_sample_ms < 20 or args.gpu_sample_ms < 100:
        raise ValueError("resource sampling intervals must be host>=20ms and GPU>=100ms")
    target_pid = args.target_pid
    if args.target_pid_file is not None:
        pid_text = args.target_pid_file.expanduser().read_text(encoding="utf-8").strip()
        target_pid = positive_int(pid_text)
    if target_pid is not None and not Path(f"/proc/{target_pid}").exists():
        raise ValueError(f"inference server PID does not exist in procfs: {target_pid}")
    artifact_dir = args.artifact_dir.expanduser().resolve()
    if artifact_dir.exists() and any(artifact_dir.iterdir()):
        raise ValueError(f"artifact directory is not empty: {artifact_dir}")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    executable = args.aiperf_bin
    version = None
    if not args.dry_run:
        executable = resolve_executable(args.aiperf_bin)
        version_result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True,
            timeout=15, check=False,
        )
        version_text = (version_result.stdout or version_result.stderr).strip()
        version = parse_aiperf_version(version_text)
        if version_result.returncode != 0 or version is None:
            raise RuntimeError("could not establish AIPerf semantic version; refusing an unpinned benchmark")
        if version != args.expected_aiperf_version:
            raise RuntimeError(f"AIPerf version mismatch: expected {args.expected_aiperf_version}, found {version}")

    command = build_command(executable, args, artifact_dir)
    normalized_command = []
    skip_artifact_dir = False
    for argument in command:
        if skip_artifact_dir:
            skip_artifact_dir = False
            continue
        if argument == "--artifact-dir":
            skip_artifact_dir = True
            continue
        normalized_command.append(argument)
    workload_command_sha256 = hashlib.sha256(
        json.dumps(normalized_command, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "status": "dry_run" if args.dry_run else "prepared",
        "created_at": utc_now(),
        "aiperf_version": version,
        "expected_aiperf_version": args.expected_aiperf_version,
        "command": command,
        "command_display": shlex.join(command),
        "workload_command_sha256": workload_command_sha256,
        "target": {"model": args.model, "url": args.url, "endpoint_type": "chat", "streaming": True},
        "profile": {
            "concurrency": args.concurrency, "request_count": args.request_count,
            "input_tokens_mean": args.input_tokens, "output_tokens_mean": args.output_tokens,
            "random_seed": args.random_seed, "export_level": "records",
            "export_generated_text": False, "server_metrics_enabled": not args.no_server_metrics,
        },
        "environment": {
            "platform": platform.platform(), "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "artifact_dir": str(artifact_dir),
        "resource_sampling": {
            "rss_target": "inference_server" if target_pid is not None else "aiperf_client",
            "host_sample_ms": args.host_sample_ms,
            "gpu_sample_ms": args.gpu_sample_ms,
            "target_pid_supplied": target_pid is not None,
        },
        "started_at": None, "finished_at": None, "exit_code": None,
    }
    manifest_path = artifact_dir / "nepenthes_aiperf_run.json"
    write_manifest(manifest_path, manifest)
    print(shlex.join(command))
    if args.dry_run:
        return 0

    log_path = artifact_dir / "aiperf.stdout.log"
    manifest["status"] = "running"
    manifest["started_at"] = utc_now()
    write_manifest(manifest_path, manifest)
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        sampler = TelemetrySampler(target_pid if target_pid is not None else process.pid,
                                   args.host_sample_ms, args.gpu_sample_ms)
        timed_out = False
        try:
            code = process.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            code = 124
        resource_telemetry = sampler.close()
    manifest["resource_telemetry"] = {
        **resource_telemetry,
        **manifest["resource_sampling"],
    }
    manifest["exit_code"] = code
    manifest["status"] = "timed_out" if timed_out else ("completed" if code == 0 else "failed")
    manifest["finished_at"] = utc_now()
    write_manifest(manifest_path, manifest)
    return code


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())