from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from nepenthes_aiperf_run import parse_args, run


def test_runner_samples_inference_server_resources(tmp_path: Path):
    fake = tmp_path / "aiperf"
    fake.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "AIPerf 0.13.0"; exit 0; fi\n'
        "sleep 0.35\n"
        "echo profile-complete\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    artifact_dir = tmp_path / "aiperf-artifacts"
    args = parse_args([
        "--model", "model-q4",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(artifact_dir),
        "--aiperf-bin", str(fake),
        "--target-pid", str(os.getpid()),
        "--timeout-seconds", "10",
    ])
    assert run(args) == 0
    manifest = json.loads((artifact_dir / "nepenthes_aiperf_run.json").read_text(encoding="utf-8"))
    telemetry = manifest["resource_telemetry"]
    assert manifest["status"] == "completed"
    assert manifest["profile"]["warmup_request_count"] == 1
    assert "--warmup-request-count" in manifest["command"]
    warmup_index = manifest["command"].index("--warmup-request-count")
    assert manifest["command"][warmup_index + 1] == "1"
    assert len(manifest["workload_command_sha256"]) == 64
    assert str(artifact_dir) not in json.dumps(manifest["command"])
    assert "<artifact-dir>" in manifest["command"]
    assert manifest["exit_code"] == 0
    assert manifest["log_artifact"]["stored"] is False
    assert len(manifest["log_artifact"]["sha256"]) == 64
    assert not (artifact_dir / "aiperf.stdout.log").exists()
    assert telemetry["rss_target"] == "inference_server"
    assert telemetry["host_sample_ms"] == 100
    assert telemetry["gpu_sample_ms"] == 500
    assert telemetry["peak_process_rss_mb"] > 0
    assert telemetry["peak_system_ram_used_mb"] > 0
    assert "peak_vram_mb_device_wide" in telemetry


def test_runner_marks_client_rss_when_no_server_pid_is_supplied(tmp_path: Path):
    fake = tmp_path / "aiperf"
    fake.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "AIPerf 0.13.0"; exit 0; fi\n'
        "sleep 0.1\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    artifact_dir = tmp_path / "aiperf-artifacts"
    args = parse_args([
        "--model", "model-q4",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(artifact_dir),
        "--aiperf-bin", str(fake),
    ])
    assert run(args) == 0
    manifest = json.loads((artifact_dir / "nepenthes_aiperf_run.json").read_text(encoding="utf-8"))
    assert manifest["resource_telemetry"]["rss_target"] == "aiperf_client"


def test_workload_command_hash_ignores_artifact_output_directory(tmp_path: Path):
    fake = tmp_path / "aiperf"
    fake.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "AIPerf 0.13.0"; exit 0; fi\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    hashes = []
    for name in ("campaign-a", "campaign-b"):
        artifact_dir = tmp_path / name
        args = parse_args([
            "--model", "model-q4",
            "--url", "http://127.0.0.1:8080",
            "--artifact-dir", str(artifact_dir),
            "--aiperf-bin", str(fake),
            "--dry-run",
        ])
        assert run(args) == 0
        manifest = json.loads((artifact_dir / "nepenthes_aiperf_run.json").read_text(encoding="utf-8"))
        hashes.append(manifest["workload_command_sha256"])
    assert hashes[0] == hashes[1]


def test_raw_aiperf_log_retention_is_explicit_opt_in(tmp_path: Path):
    fake = tmp_path / "aiperf"
    fake.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "AIPerf 0.13.0"; exit 0; fi\n'
        "echo raw-debug-output\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    artifact_dir = tmp_path / "aiperf-artifacts"
    args = parse_args([
        "--model", "model-q4",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(artifact_dir),
        "--aiperf-bin", str(fake),
        "--store-aiperf-log",
    ])
    assert run(args) == 0
    manifest = json.loads((artifact_dir / "nepenthes_aiperf_run.json").read_text(encoding="utf-8"))
    log_path = artifact_dir / "aiperf.stdout.log"
    assert manifest["log_artifact"]["stored"] is True
    assert log_path.is_file()
    assert "raw-debug-output" in log_path.read_text(encoding="utf-8")
    assert manifest["log_artifact"]["size_bytes"] == log_path.stat().st_size



def test_runner_accepts_aiperf_014_when_explicitly_pinned(tmp_path: Path):
    fake = tmp_path / "aiperf"
    fake.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "AIPerf 0.14.0"; exit 0; fi\n'
        "sleep 0.2\n"
        "echo profile-complete\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    artifact_dir = tmp_path / "aiperf-014-artifacts"
    args = parse_args([
        "--model", "model-q4",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(artifact_dir),
        "--aiperf-bin", str(fake),
        "--expected-aiperf-version", "0.14.0",
        "--target-pid", str(os.getpid()),
        "--timeout-seconds", "10",
    ])
    assert run(args) == 0
    manifest = json.loads((artifact_dir / "nepenthes_aiperf_run.json").read_text(encoding="utf-8"))
    assert manifest["aiperf_version"] == "0.14.0"
    assert manifest["expected_aiperf_version"] == "0.14.0"
    assert manifest["status"] == "completed"
