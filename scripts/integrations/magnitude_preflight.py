#!/usr/bin/env python3
"""Read-only Magnitude preflight for LEONES."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess


def run(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if lines else None


def ram_gb() -> float | None:
    try:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024**3), 2)
    except (AttributeError, OSError, ValueError):
        return None


def main() -> None:
    node = run(["node", "--version"])
    npm = run(["npm", "--version"])
    magnitude = run(["magnitude", "--version"])
    payload = {
        "profile": "magnitude-assistant",
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or "unknown",
        "ram_gb": ram_gb(),
        "node": node,
        "npm": npm,
        "magnitude": magnitude,
        "git": shutil.which("git") is not None,
        "ready": bool(node and npm),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
