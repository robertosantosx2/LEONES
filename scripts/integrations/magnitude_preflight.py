#!/usr/bin/env python3
"""Read-only Magnitude preflight for LEONES."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess


def run(command: list[str]) -> str | None:
    """Run a read-only probe and return its first output line, if available."""
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


def gpu_info() -> dict[str, str | None]:
    """Report common GPU tooling without treating missing tooling as failure."""
    nvidia = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    if nvidia:
        return {"backend": "nvidia", "device": nvidia}
    amd = run(["rocm-smi", "--showproductname"])
    if amd:
        return {"backend": "rocm", "device": amd}
    vulkan = run(["vulkaninfo", "--summary"])
    if vulkan:
        return {"backend": "vulkan", "device": vulkan}
    return {"backend": None, "device": None}


def main() -> None:
    node = run(["node", "--version"])
    npm = run(["npm", "--version"])
    magnitude = run(["magnitude", "--version"])
    try:
        disk_free_gb = round(shutil.disk_usage(".").free / (1024**3), 2)
    except OSError:
        disk_free_gb = None

    payload = {
        "profile": "magnitude-assistant",
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or "unknown",
        "ram_gb": ram_gb(),
        "disk_free_gb_at_working_directory": disk_free_gb,
        "gpu": gpu_info(),
        "node": node,
        "npm": npm,
        "magnitude": magnitude,
        "git": shutil.which("git") is not None,
        "ready": bool(node and npm),
        "network_checked": False,
        "note": "Read-only host preflight; does not prove model fit or runtime functionality.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
