#!/usr/bin/env python3
"""Non-invasive JALÓN 5 physical-host preflight.

This script detects capabilities only. It never installs software, launches a
model, or labels anything as measured evidence.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone


def command_version(command: str) -> str | None:
    path = shutil.which(command)
    if not path:
        return None
    try:
        proc = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (proc.stdout or proc.stderr).strip().splitlines()
    return text[0] if text else "installed"


def build_preflight() -> dict:
    runtimes = {
        name: {"available": shutil.which(command) is not None, "version": command_version(command)}
        for name, command in (("llama.cpp", "llama-cli"), ("vllm", "vllm"), ("sglang", "sglang"))
    }
    return {
        "schema": "jalon5-physical-preflight.v1",
        "status": "observed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "runtimes": runtimes,
        "physical_execution_required": True,
        "measurement_status": "not_measured",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args()
    payload = build_preflight()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
