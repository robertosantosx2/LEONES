#!/usr/bin/env python3
"""Collect a reproducible Linux hardware profile for LEONES model selection.

The probe reports observed host facts only. It does not infer model fit and it
does not benchmark a model. Expensive measurements are opt-in; the default
profile is safe to run on a Linux workstation.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(*args: str) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _num(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def cpu() -> dict[str, Any]:
    info: dict[str, str] = {}
    raw = _run("lscpu")
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()

    model = info.get("Model name")
    if not model:
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.lower().startswith("model name"):
                    _, value = line.split(":", 1)
                    model = value.strip()
                    break
        except OSError:
            pass
    if not model:
        model = platform.processor()

    logical = int(info["CPU(s)"]) if info.get("CPU(s)", "").isdigit() else os.cpu_count()
    physical = int(info["Core(s) per socket"]) if info.get("Core(s) per socket", "").isdigit() else None
    sockets = int(info["Socket(s)"]) if info.get("Socket(s)", "").isdigit() else None
    threads_per_core = (
        int(info["Thread(s) per core"])
        if info.get("Thread(s) per core", "").isdigit()
        else None
    )

    return {
        "model": model or "unknown",
        "logical_cpus": logical,
        "physical_cores": physical,
        "threads_per_core": threads_per_core,
        "sockets": sockets,
        "architecture": info.get("Architecture", platform.machine()),
        "mhz": _num(info.get("CPU MHz", "")),
        "cache_l3": info.get("L3 cache"),
    }


def memory() -> dict[str, Any]:
    mem: dict[str, Any] = {}
    raw = _run("free", "-b")
    for line in raw.splitlines():
        if line.startswith("Mem:"):
            fields = line.split()
            if len(fields) >= 7:
                mem = {
                    "visible_to_os_bytes": int(fields[1]),
                    "available_bytes": int(fields[6]),
                }
    return mem


def _gpu_driver(pci_address: str) -> str | None:
    driver = Path(f"/sys/bus/pci/devices/{pci_address}/driver")
    try:
        return driver.resolve().name if driver.exists() else None
    except OSError:
        return None


def gpu() -> list[dict[str, Any]]:
    raw = _run("lspci", "-D", "-mm")
    result: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not any(kind in line for kind in ("VGA compatible controller", "3D controller", "Display controller")):
            continue
        pci_address = line.split()[0] if line.split() else ""
        result.append({
            "pci_address": pci_address,
            "description": line,
            "driver": _gpu_driver(pci_address) if pci_address else None,
            "vram_bytes": None,
            "vram_source": None,
        })
    return result


def disks() -> list[dict[str, Any]]:
    raw = _run("lsblk", "-dn", "-o", "NAME,TYPE,SIZE,ROTA,MODEL")
    result = []
    for line in raw.splitlines()[1:]:
        fields = line.split(None, 4)
        if len(fields) >= 4 and fields[1] == "disk":
            result.append({
                "name": fields[0],
                "size": fields[2],
                "rotational": fields[3] == "1",
                "model": fields[4] if len(fields) > 4 else "",
            })
    return result


def network_bandwidth() -> dict[str, Any]:
    """Return interface link speed where Linux exposes it; no traffic test."""
    result = {}
    root = Path("/sys/class/net")
    if root.exists():
        for iface in root.iterdir():
            speed = iface / "speed"
            if not speed.exists():
                continue
            try:
                value = speed.read_text().strip()
            except (OSError, ValueError):
                continue
            if value.isdigit() and int(value) > 0:
                result[iface.name] = {"link_mbps": int(value)}
    return result


def optional_tools() -> dict[str, bool]:
    return {
        name: bool(shutil.which(name))
        for name in ("nvidia-smi", "rocminfo", "vulkaninfo", "vainfo", "glxinfo")
    }


def profile() -> dict[str, Any]:
    return {
        "schema_version": "hardware-profile.v1",
        "probe": "LEONES-hardware-profile",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
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
        "accelerator_tools": optional_tools(),
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
