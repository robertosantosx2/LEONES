#!/usr/bin/env python3
"""Capture llama-server /metrics and /slots locally into NEPENTHES events.

Raw endpoint snapshots are preserved with SHA-256. The /slots normalizer
exports only slot id and is_processing; prompt/token payloads are never copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from scripts.nepenthes_llama_server_metrics import parse_prometheus, parse_slots


def validate_server_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("llama-server URL must be an absolute http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("llama-server URL must not embed credentials, query parameters or fragments")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("remote llama-server endpoints must use HTTPS")
    return value.rstrip("/")


def fetch(url: str, *, timeout_seconds: float, opener: Callable[..., Any] = urlopen) -> tuple[int, bytes]:
    request = Request(url, headers={"Accept": "application/json, text/plain"}, method="GET")
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            return int(status), response.read()
    except HTTPError as exc:
        if exc.code in {404, 501}:
            return exc.code, exc.read()
        raise RuntimeError(f"llama-server endpoint returned HTTP {exc.code}") from exc


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def capture(*, url: str, output_dir: Path, duration_seconds: float = 30.0,
            interval_ms: int = 1000, timeout_seconds: float = 3.0,
            require_metrics: bool = False, metrics_path: str = "/metrics",
            slots_path: str = "/slots", run_id: str | None = None,
            opener: Callable[..., Any] = urlopen,
            monotonic_clock_ns: Callable[[], int] = time.monotonic_ns,
            wall_clock_ns: Callable[[], int] = time.time_ns,
            sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    base = validate_server_url(url)
    if duration_seconds <= 0 or interval_ms < 50 or timeout_seconds <= 0:
        raise ValueError("duration/timeout must be positive and interval_ms must be >= 50")
    if not metrics_path.startswith("/") or not slots_path.startswith("/"):
        raise ValueError("endpoint paths must start with '/' ")
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"capture output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    run_id = run_id or str(uuid.uuid4())
    metrics_url = base + metrics_path
    slots_url = base + slots_path
    started_wall = wall_clock_ns()
    started_mono = monotonic_clock_ns()
    raw_files: list[dict[str, Any]] = []
    warnings: list[str] = []
    metrics_scrapes = 0
    slots_snapshots = 0
    event_count = 0
    metrics_status: int | None = None
    slots_status: int | None = None
    sequence = 0
    events_path = output_dir / "llama_server_events.jsonl"
    with events_path.open("x", encoding="utf-8") as event_stream:
        while True:
            sequence += 1
            wall_ns = wall_clock_ns()
            mono_ns = monotonic_clock_ns()
            metrics_status, metrics_body = fetch(metrics_url, timeout_seconds=timeout_seconds, opener=opener)
            if metrics_status == 200:
                raw_path = raw_dir / f"metrics-{sequence:06d}.prom"
                raw_path.write_bytes(metrics_body)
                raw_files.append({"path": raw_path.relative_to(output_dir).as_posix(),
                                  "size_bytes": len(metrics_body),
                                  "sha256": hashlib.sha256(metrics_body).hexdigest()})
                events = parse_prometheus(metrics_body.decode("utf-8"),
                                           scrape_timestamp_unix_ns=wall_ns,
                                           scrape_id=f"{run_id}:{sequence}:metrics")
                for event in events:
                    event["run_id"] = run_id
                    event["monotonic_ns"] = mono_ns
                    event["capture_sequence"] = sequence
                    event_stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
                    event_count += 1
                metrics_scrapes += 1
            elif metrics_status in {404, 501}:
                if "llama-server /metrics endpoint is unavailable; start llama-server with --metrics" not in warnings:
                    warnings.append("llama-server /metrics endpoint is unavailable; start llama-server with --metrics")
                if require_metrics:
                    raise RuntimeError("/metrics is unavailable; --require-metrics was specified")
            else:
                raise RuntimeError(f"unexpected /metrics HTTP status {metrics_status}")

            slots_status, slots_body = fetch(slots_url, timeout_seconds=timeout_seconds, opener=opener)
            if slots_status == 200:
                raw_path = raw_dir / f"slots-{sequence:06d}.json"
                raw_path.write_bytes(slots_body)
                raw_files.append({"path": raw_path.relative_to(output_dir).as_posix(),
                                  "size_bytes": len(slots_body),
                                  "sha256": hashlib.sha256(slots_body).hexdigest()})
                try:
                    slots_payload = json.loads(slots_body)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid /slots JSON at capture sequence {sequence}: {exc}") from exc
                events = parse_slots(slots_payload, timestamp_unix_ns=wall_ns,
                                     snapshot_id=f"{run_id}:{sequence}:slots")
                for event in events:
                    event["run_id"] = run_id
                    event["monotonic_ns"] = mono_ns
                    event["capture_sequence"] = sequence
                    event_stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
                    event_count += 1
                slots_snapshots += 1
            elif slots_status == 404:
                if "llama-server /slots endpoint is unavailable" not in warnings:
                    warnings.append("llama-server /slots endpoint is unavailable")
            else:
                raise RuntimeError(f"unexpected /slots HTTP status {slots_status}")

            event_stream.flush()
            elapsed = (monotonic_clock_ns() - started_mono) / 1_000_000_000.0
            if elapsed >= duration_seconds:
                break
            sleeper(min(interval_ms / 1000.0, max(0.0, duration_seconds - elapsed)))
    finished_wall = wall_clock_ns()
    finished_mono = monotonic_clock_ns()
    parsed = urlsplit(base)
    manifest = {
        "schema_version": "1.0", "run_id": run_id,
        "source_tool": "llama.cpp", "endpoint_origin": f"{parsed.scheme}://{parsed.netloc}",
        "metrics_endpoint_path": metrics_path, "slots_endpoint_path": slots_path,
        "metrics_endpoint_status": metrics_status, "slots_endpoint_status": slots_status,
        "metrics_enabled": metrics_scrapes > 0, "slots_available": slots_snapshots > 0,
        "metrics_scrape_count": metrics_scrapes, "slots_snapshot_count": slots_snapshots,
        "event_count": event_count, "started_at_unix_ns": started_wall,
        "finished_at_unix_ns": finished_wall, "started_monotonic_ns": started_mono,
        "finished_monotonic_ns": finished_mono,
        "duration_seconds": (finished_mono - started_mono) / 1_000_000_000.0,
        "events_file": events_path.name, "raw_artifacts": raw_files, "warnings": warnings,
        "privacy": {"prompt_values_exported": False, "token_values_exported": False,
                    "unknown_slot_values_exported": False},
    }
    atomic_json(output_dir / "llama_server_capture_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--interval-ms", type=int, default=1000)
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--require-metrics", action="store_true")
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    try:
        manifest = capture(url=args.url, output_dir=args.output_dir,
                           duration_seconds=args.duration_seconds,
                           interval_ms=args.interval_ms, timeout_seconds=args.timeout_seconds,
                           require_metrics=args.require_metrics, run_id=args.run_id)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"run_id": manifest["run_id"], "event_count": manifest["event_count"],
                      "metrics_scrapes": manifest["metrics_scrape_count"],
                      "slots_snapshots": manifest["slots_snapshot_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())