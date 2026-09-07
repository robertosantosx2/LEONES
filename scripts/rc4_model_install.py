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


def run_download(command: list[str]) -> tuple[int, str]:
    """Run hf while forwarding output and emitting a periodic heartbeat."""
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
    next_heartbeat = started + 1.0

    while True:
        now = time.monotonic()
        if now >= next_heartbeat and process.poll() is None:
            elapsed = int(now - started)
            print(f"HEARTBEAT=active ELAPSED={elapsed}s", flush=True)
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

    command = ["hf", "download", model_id, "--local-dir", str(target)]
    print(f"MODEL={model_id}", flush=True)
    print(f"TARGET={target}", flush=True)
    print("PHASE=downloading", flush=True)
    returncode, combined = run_download(command)

    if returncode == 0:
        marker.write_text(json.dumps({
            "schema": "leones.installed-model.v1",
            "model_id": model_id,
        }, indent=2) + "\n", encoding="utf-8")
        print("PHASE=completed", flush=True)
        print("STATUS=installed", flush=True)
    else:
        reason = classify_failure(combined)
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
