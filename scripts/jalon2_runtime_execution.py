#!/usr/bin/env python3
"""Physical llama.cpp execution runner for LEONES runtime-execution.v1.

The runner captures provenance and raw execution evidence.
It does not interpret benchmark results; the dedicated evidence bridge does that.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import time
import pty
import select
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "runtime-execution.v1"


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def first_line(command: list[str]) -> str:
    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[0] if lines else "unknown"
    except (OSError, subprocess.CalledProcessError, IndexError):
        return "unknown"


def detect_cpu_model() -> str:
    try:
        output = subprocess.check_output(
            ["lscpu"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in output.splitlines():
            if line.startswith("Model name:"):
                return line.split(":", 1)[1].strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    return platform.processor() or "unknown"


def detect_ram_mb() -> float | None:
    try:
        text = Path("/proc/meminfo").read_text()
        for line in text.splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return kb / 1024
    except (OSError, ValueError):
        pass
    return None


def detect_cores() -> tuple[int | None, int | None]:
    threads = os.cpu_count()

    physical = None
    try:
        output = subprocess.check_output(
            ["lscpu", "-p=CPU,Core"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        cores = {
            line.split(",")[1]
            for line in output.splitlines()
            if line and not line.startswith("#") and "," in line
        }
        physical = len(cores) or None
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass

    return threads, physical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--ctx-size", type=int, default=2048)
    parser.add_argument("--n-predict", type=int, default=128)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--threads-batch", type=int, default=4)
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/runtime-executions"))
    args = parser.parse_args()

    binary = args.binary.resolve()
    model = args.model.resolve()

    if not binary.is_file():
        raise SystemExit(f"runtime binary not found: {binary}")
    if not model.is_file():
        raise SystemExit(f"model not found: {model}")

    execution_id = (
        "jalon2-llama-cpp-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )

    execution_dir = args.out_dir / execution_id
    execution_dir.mkdir(parents=True, exist_ok=True)

    raw_log = execution_dir / "execution.log"
    execution_json = execution_dir / "runtime-execution.json"
    evidence_json = execution_dir / "runtime-benchmark-evidence.json"

    timestamp_start = utc_now()

    model_sha256 = sha256_file(model)
    binary_sha256 = sha256_file(binary)
    prompt_sha256 = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest()

    threads, physical_cores = detect_cores()

    runtime_version = first_line([str(binary), "--version"])

    command = [
        str(binary),
        "-m",
        str(model),
        "-t",
        str(args.threads),
        "-tb",
        str(args.threads_batch),
        "-c",
        str(args.ctx_size),
        "-n",
        str(args.n_predict),
        "--perf",
        "--single-turn",
    ]

    if args.warmup:
        command.append("--warmup")

    command.extend(["-p", args.prompt])

    env = os.environ.copy()

    provenance = [
        f"execution_id={execution_id}",
        f"timestamp_utc={timestamp_start}",
        f"host={socket.gethostname()}",
        f"os={platform.platform()}",
        f"kernel={platform.release()}",
        f"cpu={detect_cpu_model()}",
        f"cpu_threads={threads or ''}",
        f"physical_cores={physical_cores or ''}",
        f"ram_total_mb={detect_ram_mb() or ''}",
        "runtime=llama.cpp",
        f"runtime_version={runtime_version}",
        f"runtime_binary={binary}",
        f"runtime_binary_sha256={binary_sha256}",
        f"model={model.name}",
        f"model_size_bytes={model.stat().st_size}",
        f"model_sha256={model_sha256}",
        f"threads={args.threads}",
        f"threads_batch={args.threads_batch}",
        f"ctx_size={args.ctx_size}",
        f"n_predict={args.n_predict}",
        f"warmup={'enabled' if args.warmup else 'disabled'}",
        "perf=enabled",
        "single_turn=enabled",
        f"prompt_sha256={prompt_sha256}",
        "",
        "===== COMMAND =====",
        shlex.join(command),
        "",
        "===== EXECUTION =====",
    ]

    start_monotonic = time.monotonic()

    # llama-cli emits --perf through a real terminal path. util-linux
    # `script` creates the controlling PTY and records the complete
    # terminal transcript, including Prompt/Generation throughput.
    transcript = execution_dir / "terminal.transcript"

    script_command = [
        "/usr/bin/script",
        "-qefc",
        shlex.join(command),
        str(transcript),
    ]

    completed = subprocess.run(
        [
            "/usr/bin/time",
            "-v",
            *script_command,
        ],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    wall_seconds = time.monotonic() - start_monotonic
    timestamp_end = utc_now()

    if transcript.is_file():
        completed_stdout = transcript.read_text(
            encoding="utf-8",
            errors="replace",
        )
    else:
        completed_stdout = ""

    # A physical benchmark without the llama.cpp --perf summary is invalid.
    if "Prompt:" not in completed_stdout or "Generation:" not in completed_stdout:
        raw_log.write_text(
            "\n".join(provenance)
            + "\n===== SCRIPT COMMAND =====\n"
            + shlex.join(script_command)
            + "\n===== TERMINAL TRANSCRIPT =====\n"
            + completed_stdout
            + "\n===== /usr/bin/time =====\n"
            + (completed.stdout or ""),
            encoding="utf-8",
        )
        raise SystemExit(
            "ERROR: terminal transcript does not contain "
            "Prompt/Generation performance metrics"
        )

    # /usr/bin/time -v writes resource diagnostics to the wrapper output,
    # not to the terminal transcript recorded by `script`.
    maximum_rss_kb = None
    for line in (completed.stdout or "").splitlines():
        if line.strip().startswith("Maximum resident set size (kbytes):"):
            try:
                maximum_rss_kb = int(line.rsplit(":", 1)[1].strip())
            except ValueError:
                maximum_rss_kb = None
            break

    raw_text = "\n".join(provenance) + "\n"
    raw_text += "===== SCRIPT COMMAND =====\n"
    raw_text += shlex.join(script_command) + "\n"
    raw_text += "===== TERMINAL TRANSCRIPT =====\n"
    raw_text += completed_stdout.replace("\r\n", "\n").replace("\r", "\n")
    raw_text += "\n===== /usr/bin/time =====\n"
    raw_text += completed.stdout or ""
    raw_text += f"\nexit_status={completed.returncode}\n"
    raw_text += f"timestamp_end_utc={timestamp_end}\n"

    raw_log.write_text(raw_text, encoding="utf-8")

    execution: dict[str, Any] = {
        "schema": SCHEMA,
        "execution_id": execution_id,
        "timestamp_start": timestamp_start,
        "timestamp_end": timestamp_end,
        "model": {
            "path": str(model),
            "sha256": model_sha256,
        },
        "protocol": {
            "prompt_protocol_id": "leones-local-v1",
            "prompt_sha256": prompt_sha256,
            "context": args.ctx_size,
            "output_token_limit": args.n_predict,
            "temperature": 0,
            "top_p": None,
            "seed": None,
            "warmup_iterations": 1 if args.warmup else 0,
            "measurement_iterations": 1,
        },
        "runtime": {
            "name": "llama.cpp",
            "version": runtime_version,
            "binary": str(binary),
            "binary_sha256": binary_sha256,
        },
        "hardware": {
            "host": socket.gethostname(),
            "os": platform.platform(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "cpu": platform.processor() or "unknown",
            "cpu_threads": threads,
            "physical_cores": physical_cores,
            "ram_total_mb": detect_ram_mb(),
        },
        "command": command,
        "result": {
            "exit_code": completed.returncode,
            "wall_seconds": wall_seconds,
            "maximum_rss_kb": maximum_rss_kb,
        },
        "artifacts": {
            "raw_log": str(raw_log),
            "evidence": str(evidence_json),
        },
    }

    execution_json.write_text(
        json.dumps(execution, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "schema": SCHEMA,
        "execution_id": execution_id,
        "exit_code": completed.returncode,
        "raw_log": str(raw_log),
        "execution": str(execution_json),
        "next_evidence": str(evidence_json),
    }))

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
