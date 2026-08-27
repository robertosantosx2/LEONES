#!/usr/bin/env python3
"""Read-only ODS preflight for LEONES.

The script deliberately does not install anything and does not contact ODS.
It reports facts that are useful before an ODS installation.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess


def command_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or result.stderr).strip().splitlines()
    return text[0] if text else None


def ram_gb() -> float | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / (1024**3), 2)
    except (AttributeError, OSError, ValueError):
        return None


def main() -> None:
    docker = command_version(["docker", "--version"])
    compose = command_version(["docker", "compose", "version"])
    payload = {
        "profile": "ods-server",
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or "unknown",
        "ram_gb": ram_gb(),
        "docker": docker,
        "docker_compose": compose,
        "nvidia_smi": command_version(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]
        ),
        "git": shutil.which("git") is not None,
        "curl": shutil.which("curl") is not None,
        "ready": bool(docker and compose),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
