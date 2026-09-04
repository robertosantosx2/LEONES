#!/usr/bin/env python3
"""Collect an observed, reproducible Linux hardware profile for LEONES.

This probe reports host facts only. It does not infer model fit and it does
not benchmark a model. Optional accelerator tools are detected when present;
missing tools are represented explicitly rather than guessed.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROBE_VERSION = "hardware-profile.v1"


def _run(*args: str) -> str:
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _num(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _lscpu() -> dict[str, str]:
    info: dict[str, str] = {}
    for line in _run("lscpu").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def cpu() -> dict[str, Any]:
    info = _lscpu()

    def integer(key: str) -> int | None:
        value = info.get(key, "")
        return int(value) if value.isdigit() else None

    return {
        "model": info.get("Model name", platform.processor()),
        "logical_cpus": integer("CPU(s)"),
        "physical_cores": integer("Core(s) per socket"),
        "threads_per_core": integer("Thread(s) per core"),
        "sockets": integer("Socket(s)"),
        "architecture": info.get("Architecture", platform.machine()),
        "mhz_current": _num(info.get("CPU MHz", "")),
        "mhz_min": _num(info.get("CPU min MHz", "")),
        "mhz_max": _num(info.get("CPU max MHz", "")),
        "cache_l3": info.get("L3 cache"),
        "flags": info.get("Flags", "").split() or info.get("Flags", "").split(","),
    }


def memory() -> dict[str, Any]:
    result: dict[str, Any] = {"source": "free -b"}
    for line in _run("free", "-b").splitlines():
        if line.startswith("Mem:"):
            fields = line.split()
            if len(fields) >= 7:
                result.update(
                    {
                        "total_bytes": int(fields[1]),
                        "available_bytes": int(fields[6]),
                    }
                )
            break
    return result


def _gpu_driver(bdf: str) -> str | None:
    driver_link = Path("/sys/bus/pci/devices") / bdf / "driver"
    try:
        return driver_link.resolve().name
    except (FileNotFoundError, OSError):
        return None


def gpu() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in _run("lspci", "-mm").splitlines():
        if not any(
            kind in line
            for kind in (
                "VGA compatible controller",
                "3D controller",
                "Display controller",
            )
        ):
            continue
        bdf = line.split()[0] if line.split() else ""
        result.append(
            {
                "pci_address": bdf or None,
                "description": line,
                "driver": _gpu_driver(bdf) if bdf else None,
            }
        )
    return result


def disks() -> list[dict[str, Any]]:
    raw = _run("lsblk", "-dn", "-o", "NAME,TYPE,SIZE,ROTA,MODEL")
    result: list[dict[str, Any]] = []
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
    result: dict[str, Any] = {}
    root = Path("/sys/class/net")
    if root.exists():
        for iface in root.iterdir():
            speed = iface / "speed"
            try:
                value = speed.read_text().strip()
            except (FileNotFoundError, OSError):
                continue
            if value.isdigit() and int(value) > 0:
                result[iface.name] = {"link_mbps": int(value)}
    return result


def tools() -> dict[str, Any]:
    names = (
        "lscpu",
        "free",
        "lspci",
        "lsblk",
        "nvidia-smi",
        "rocminfo",
        "vulkaninfo",
        "vainfo",
        "glxinfo",
    )
    return {name: bool(shutil.which(name)) for name in names}


def profile() -> dict[str, Any]:
    return {
        "schema": PROBE_VERSION,
        "probe": {
            "name": "LEONES-hardware-profile",
            "version": PROBE_VERSION,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        },
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
        "tools": tools(),
        "measurement": {
            "cpu_benchmark": False,
            "memory_bandwidth": False,
            "disk_benchmark": False,
            "gpu_benchmark": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    text = json.dumps(profile(), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
