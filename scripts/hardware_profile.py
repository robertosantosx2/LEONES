#!/usr/bin/env python3
"""Observe the local Linux hardware needed by the RC1 decision path.

Inputs
------
No model, prompt or external service is required. The script reads standard
Linux interfaces and commands when they are available.

Output
------
A JSON profile containing observed platform, CPU, memory, GPU, disks, network
link speeds and tool availability. With ``--out`` the same JSON is written to
that path; otherwise it is printed to stdout.

Boundary
--------
This script **observes** hardware. It does not estimate model fit, download or
run models, benchmark hardware, install software, or publish anything.
Optional/unsupported measurements are represented as missing values rather
than invented values. That distinction is important because this profile is
the evidence boundary between the user's machine and later selection logic.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(*args: str) -> str:
    """Run one read-only probe and return empty text when it is unavailable."""
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        # A missing Linux utility is not proof that the corresponding hardware
        # is absent. Returning empty data preserves that uncertainty honestly.
        return ""


def _num(value: str) -> float | None:
    """Convert a numeric probe value without manufacturing a fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def cpu() -> dict[str, Any]:
    """Return CPU facts exposed by ``lscpu`` or portable Python fallbacks."""
    info = {}
    raw = _run("lscpu")
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()

    return {
        "model": info.get("Model name", platform.processor()),
        "cores": int(info["CPU(s)"])
        if info.get("CPU(s)", "").isdigit()
        else os.cpu_count(),
        "architecture": info.get("Architecture", platform.machine()),
        "mhz": _num(info.get("CPU MHz", "")),
        "cache_l3": info.get("L3 cache"),
    }


def memory() -> dict[str, Any]:
    """Return total and available memory as observed by ``free -b``."""
    mem = {}
    raw = _run("free", "-b")
    for line in raw.splitlines():
        if line.startswith("Mem:"):
            fields = line.split()
            if len(fields) >= 7:
                mem = {
                    "total_bytes": int(fields[1]),
                    "available_bytes": int(fields[6]),
                }
    return mem


def gpu() -> list[dict[str, str]]:
    """Return display controllers visible to PCI enumeration."""
    raw = _run("lspci", "-mm")
    result = []
    for line in raw.splitlines():
        if (
            "VGA compatible controller" in line
            or "3D controller" in line
            or "Display controller" in line
        ):
            result.append({"description": line})
    return result


def disks() -> list[dict[str, Any]]:
    """Return block-device facts exposed by ``lsblk`` without benchmarking."""
    raw = _run("lsblk", "-dn", "-o", "NAME,TYPE,SIZE,ROTA,MODEL")
    result = []
    for line in raw.splitlines()[1:]:
        fields = line.split(None, 4)
        if len(fields) >= 4 and fields[1] == "disk":
            result.append(
                {
                    "name": fields[0],
                    "size": fields[2],
                    "rotational": fields[3] == "1",
                    "model": fields[4] if len(fields) > 4 else "",
                }
            )
    return result


def network_bandwidth() -> dict[str, Any]:
    """Return interface link speed where Linux exposes it; no traffic test."""
    result = {}
    root = Path("/sys/class/net")
    if root.exists():
        for iface in root.iterdir():
            speed = iface / "speed"
            if speed.exists():
                value = speed.read_text().strip()
                if value.isdigit() and int(value) > 0:
                    result[iface.name] = {"link_mbps": int(value)}
    return result


def profile() -> dict[str, Any]:
    """Build the complete observation-only profile consumed by selection."""
    return {
        "schema_version": "1.0",
        "probe": "LEONES-hardware-profile",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cpu": cpu(),
        "memory": memory(),
        "gpu": gpu(),
        "disks": disks(),
        "network": network_bandwidth(),
        "tools": {
            name: bool(shutil.which(name))
            for name in ("lscpu", "free", "lspci", "lsblk")
        },
        "measurement": {
            "cpu_benchmark": False,
            "memory_bandwidth": False,
            "disk_benchmark": False,
        },
    }


def main() -> int:
    """Print or save the observed profile; never performs a physical benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = profile()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
