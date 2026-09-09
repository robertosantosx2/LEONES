#!/usr/bin/env python3
"""RC4 explicit model-installation boundary.

A model is installed only after the TUI obtains explicit user consent. This
script performs no recommendation and no measurement; it only materializes a
selected Hugging Face model into the LEONES local-model directory.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "models"
MODEL_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MARKER = ".leones-installed.json"


def classify_failure(output: str) -> str:
    text = output.lower()
    if "requires approval" in text or "access denied" in text or "gated" in text:
        return "REQUIRES_APPROVAL_HF"
    if "authentication" in text or "not authenticated" in text or "401" in text or ("token" in text and "permission" in text):
        return "REQUIRES_AUTH_HF"
    return "DOWNLOAD_FAILED"


def size_to_bytes(value: str, unit: str) -> int:
    multipliers = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    return int(float(value) * multipliers[unit.upper()])


def parse_size(text: str) -> int | None:
    """Return the total final local size from the HF dry-run file table."""
    total = 0
    in_table = False
    found = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("File") and "Bytes to download" in line:
            in_table = True
            continue
        if not in_table or not line or line.startswith("-"):
            continue
        match = re.search(r"\s([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?)i?B?\s*$", line, re.I)
        if match:
            total += size_to_bytes(match.group(1), match.group(2))
            found = True
    if found:
        return total

    match = re.search(r"totalling\s+([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?)(?:i?B)?", text, re.I)
    if match:
        return size_to_bytes(match.group(1), match.group(2))
    return None


def download_plan(model_id: str) -> tuple[int | None, str]:
    """Ask HF for the download plan so the TUI can display a real percentage."""
    command = ["hf", "download", model_id, "--dry-run"]
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return parse_size(output), output


def run_download(command: list[str], target: Path, total_bytes: int | None) -> tuple[int, str]:
    """Run hf while forwarding output and emitting live progress telemetry."""
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output: list[str] = []
    started = time.monotonic()
    last_bytes = directory_bytes(target)
    last_time = started
    next_heartbeat = started + 1.0

    while True:
        now = time.monotonic()
        if now >= next_heartbeat and process.poll() is None:
            current = directory_bytes(target)
            elapsed = max(now - started, 0.001)
            delta = max(0, current - last_bytes)
            interval = max(now - last_time, 0.001)
            rate = delta / interval
            if total_bytes:
                percent = min(100.0, current * 100.0 / total_bytes)
                print(
                    f"PROGRESS={percent:5.1f}% DOWNLOADED={current} TOTAL={total_bytes} RATE={rate:.1f}B/s",
                    flush=True,
                )
            else:
                print(f"PROGRESS=unknown DOWNLOADED={current} RATE={rate:.1f}B/s", flush=True)
            print(f"HEARTBEAT=active ELAPSED={int(elapsed)}s", flush=True)
            last_bytes = current
            last_time = now
            next_heartbeat = now + 1.0

        line = None
        if process.stdout is not None:
            import select
            ready, _, _ = select.select([process.stdout], [], [], 0.2)
            if ready:
                line = process.stdout.readline()

        if line:
            output.append(line)
            print(line, end="", flush=True)
        elif process.poll() is not None:
            break

    if process.stdout is not None:
        remainder = process.stdout.read()
        if remainder:
            output.append(remainder)
            print(remainder, end="", flush=True)

    return process.wait(), "".join(output)


def directory_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def install(model_id: str, output_dir: Path) -> int:
    if not MODEL_RE.fullmatch(model_id):
        print(f"ERROR: model_id no válido para Hugging Face: {model_id}", file=sys.stderr)
        return 2
    if shutil.which("hf") is None:
        print("ERROR: no se encontró 'hf' en PATH. Instala huggingface_hub/hf antes de continuar.", file=sys.stderr)
        return 3

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / model_id.replace("/", "--")
    marker = target / MARKER
    if marker.is_file():
        print(f"MODEL={model_id}", flush=True)
        print(f"TARGET={target}", flush=True)
        print("PHASE=completed", flush=True)
        print("STATUS=already_installed", flush=True)
        return 0

    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)

    print(f"MODEL={model_id}", flush=True)
    print(f"TARGET={target}", flush=True)
    print("PHASE=planning", flush=True)
    total_bytes, plan_output = download_plan(model_id)
    if total_bytes is not None:
        print(f"TOTAL_BYTES={total_bytes}", flush=True)
    else:
        print("TOTAL_BYTES=unknown", flush=True)
    print("PHASE=downloading", flush=True)

    command = ["hf", "download", model_id, "--local-dir", str(target)]
    returncode, combined = run_download(command, target, total_bytes)

    if returncode == 0:
        marker.write_text(json.dumps({
            "schema": "leones.installed-model.v1",
            "model_id": model_id,
        }, indent=2) + "\n", encoding="utf-8")
        print("PROGRESS=100.0%", flush=True)
        print("PHASE=completed", flush=True)
        print("STATUS=installed", flush=True)
    else:
        reason = classify_failure(combined + "\n" + plan_output)
        shutil.rmtree(target, ignore_errors=True)
        print("PHASE=failed", flush=True)
        print(f"STATUS={reason}", flush=True)
    return returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RC4 install selected Hugging Face model")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args(argv)
    return install(args.model_id, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
