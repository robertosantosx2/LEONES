#!/usr/bin/env python3
"""Small, dependency-free host hardware snapshot for runtime evidence."""
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
    cpuinfo = _command_output(["lscpu"])
    if cpuinfo:
        for line in cpuinfo.splitlines():
            if line.lower().startswith("model name:"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or None


def _ram_gb() -> float | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    kib = int(re.search(r"\d+", line).group())
                    return round(kib / 1024 / 1024, 2)
    except (OSError, AttributeError, ValueError):
        return None
    return None


def _gpu() -> tuple[str | None, float | None]:
    output = _command_output(["lspci", "-mm"]) if shutil.which("lspci") else None
    if not output:
        return None, None
    names: list[str] = []
    for line in output.splitlines():
        if "VGA compatible controller" in line or "3D controller" in line:
            parts = re.findall(r'"([^"]+)"', line)
            if len(parts) >= 3:
                names.append(parts[-1])
            elif line:
                names.append(line)
    return (names[0] if names else None), None


def collect_runtime_hardware() -> dict[str, Any]:
    """Return only facts available on the current host; never invent values."""
    gpu, vram_gb = _gpu()
    return {
        "ram_gb": _ram_gb(),
        "os": f"{platform.system()} {platform.release()}" if platform.system() else None,
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
