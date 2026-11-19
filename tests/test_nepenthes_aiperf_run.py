from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.nepenthes_aiperf_run import build_command, parse_aiperf_version, parse_args, run, safe_url


def test_aiperf_version_parser_and_release_pin():
    assert parse_aiperf_version("aiperf, version 0.13.0") == "0.13.0"
    assert parse_aiperf_version("0.14.0rc1") == "0.14.0rc1"
    assert parse_aiperf_version("unknown version") is None


def test_safe_url_rejects_embedded_secrets():
    with pytest.raises(Exception):
        safe_url("http://user:password@127.0.0.1:8080")
    with pytest.raises(Exception):
        safe_url("http://127.0.0.1:8080?token=secret")


def test_safe_url_accepts_local_openai_endpoint():
    assert safe_url("http://127.0.0.1:8080/v1/chat/completions") == "http://127.0.0.1:8080/v1/chat/completions"


def test_build_command_uses_conservative_reproducible_profile(tmp_path: Path):
    args = parse_args([
        "--model", "local-model",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(tmp_path / "run"),
    ])
    command = build_command("/usr/bin/aiperf", args, tmp_path / "run")
    assert command[:2] == ["/usr/bin/aiperf", "profile"]
    assert command[command.index("--concurrency") + 1] == "1"
    assert command[command.index("--request-count") + 1] == "5"
    assert command[command.index("--synthetic-input-tokens-mean") + 1] == "128"
    assert command[command.index("--output-tokens-mean") + 1] == "32"
    assert "--streaming" in command
    assert "--export-level" in command and command[command.index("--export-level") + 1] == "records"
    assert "--no-export-outputs-json" in command
    assert "--api-key" not in command


def test_no_server_metrics_flag_is_opt_in(tmp_path: Path):
    args = parse_args([
        "--model", "local-model", "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(tmp_path / "run"), "--no-server-metrics",
    ])
    command = build_command("aiperf", args, tmp_path / "run")
    assert "--no-server-metrics" in command


def test_dry_run_writes_manifest_without_launching_aiperf(tmp_path: Path, capsys):
    artifact_dir = tmp_path / "dry-run"
    args = parse_args([
        "--model", "local-model",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(artifact_dir),
        "--dry-run",
    ])
    assert run(args) == 0
    manifest = json.loads((artifact_dir / "nepenthes_aiperf_run.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "dry_run"
    assert manifest["aiperf_version"] is None
    assert manifest["expected_aiperf_version"] == "0.13.0"
    assert manifest["profile"]["concurrency"] == 1
    assert manifest["profile"]["export_generated_text"] is False
    assert "--streaming" in capsys.readouterr().out


def test_runner_refuses_nonempty_artifact_directory(tmp_path: Path):
    artifact_dir = tmp_path / "existing"
    artifact_dir.mkdir()
    (artifact_dir / "keep.txt").write_text("keep", encoding="utf-8")
    args = parse_args([
        "--model", "local-model",
        "--url", "http://127.0.0.1:8080",
        "--artifact-dir", str(artifact_dir),
        "--dry-run",
    ])
    with pytest.raises(ValueError, match="not empty"):
        run(args)


def test_positive_integer_arguments_reject_zero():
    with pytest.raises(SystemExit):
        parse_args([
            "--model", "local-model", "--url", "http://127.0.0.1:8080",
            "--artifact-dir", "/tmp/nepenthes-test", "--concurrency", "0",
        ])