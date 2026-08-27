#!/usr/bin/env python3
"""Dependency-free host hardware snapshot for runtime evidence."""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from typing import Any


def _command_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _cpu_name() -> str | None:
    output = _command_output(["lscpu"])
    if output:
        for line in output.splitlines():
            if line.lower().startswith("model name:"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or None


def _ram_gb() -> float | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    match = re.search(r"\d+", line)
                    if match:
                        return round(int(match.group()) / 1024 / 1024, 2)
    except (OSError, ValueError):
        pass
    return None


def _gpu() -> tuple[str | None, float | None]:
    if not shutil.which("lspci"):
        return None, None
    output = _command_output(["lspci", "-mm"])
    if not output:
        return None, None
    for line in output.splitlines():
        if "VGA compatible controller" in line or "3D controller" in line:
            parts = re.findall(r'"([^"]+)"', line)
            return (parts[-1] if parts else line), None
    return None, None


def collect_runtime_hardware() -> dict[str, Any]:
    """Return only facts available on the current host; never invent values."""
    gpu, vram_gb = _gpu()
    system = platform.system()
    return {
        "ram_gb": _ram_gb(),
        "os": f"{system} {platform.release()}" if system else None,
        "architecture": platform.machine() or None,
        "cpu": _cpu_name(),
        "cpu_logical_cores": os.cpu_count(),
        "gpu": gpu,
        "vram_gb": vram_gb,
        "host_memory_bandwidth_gbps": None,
        "pcie_h2d_bandwidth_gbps": None,
        "cpu_moe_bandwidth_gbps": None,
        "source": "local-host-runtime",
    }
