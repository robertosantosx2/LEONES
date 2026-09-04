#!/usr/bin/env python3
"""Collect the canonical LEONES Linux hardware profile.

This module is the single low-level physical probe used by RC3. It reports
observed host facts only: no model-fit inference and no benchmarking.
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


def _run(*args: str, timeout: float = 5.0) -> str:
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL, timeout=timeout
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def _num(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cpuinfo() -> tuple[str | None, list[str]]:
    try:
        raw = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, []
    model = None
    flags: list[str] = []
    for line in raw.splitlines():
        if model is None and re.match(r"^model name\s*:", line, re.I):
            model = line.split(":", 1)[1].strip()
        if not flags and re.match(r"^(?:flags|Features)\s*:", line, re.I):
            flags = line.split(":", 1)[1].split()
    return model, sorted(set(flags))


def _topology() -> tuple[int | None, int | None, int | None, int | None]:
    raw = _run("lscpu", "-p=CPU,Core,Socket")
    rows: list[tuple[int, int, int]] = []
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) >= 3:
            try:
                rows.append((int(parts[0]), int(parts[1]), int(parts[2])))
            except ValueError:
                continue
    if not rows:
        return None, None, None, None
    logical = len({r[0] for r in rows})
    sockets = len({r[2] for r in rows})
    physical = len({(r[1], r[2]) for r in rows})
    per_socket = physical // sockets if sockets else None
    return logical, physical, sockets, per_socket


def cpu() -> dict[str, Any]:
    model, flags = _cpuinfo()
    logical, physical, sockets, cores_per_socket = _topology()
    raw = _run("lscpu")
    info: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return {
        "model": model or platform.processor() or "unknown",
        "logical_cpus": logical or os.cpu_count(),
        "physical_cores": physical,
        "threads_per_core": (
            logical // physical if logical and physical else None
        ),
        "sockets": sockets,
        "architecture": platform.machine(),
        "mhz": _num(info.get("CPU MHz", "")),
        "cache_l3": info.get("L3 cache") or info.get("L3 Cache"),
        "flags": flags,
    }


def memory() -> dict[str, Any]:
    raw = _run("free", "-b")
    for line in raw.splitlines():
        if line.startswith("Mem:"):
            fields = line.split()
            if len(fields) >= 7:
                return {
                    "visible_to_os_bytes": int(fields[1]),
                    "available_bytes": int(fields[6]),
                }
    return {}


def _gpu_driver(pci_address: str) -> str | None:
    driver = Path(f"/sys/bus/pci/devices/{pci_address}/driver")
    try:
        return driver.resolve().name if driver.exists() else None
    except OSError:
        return None


def gpu() -> list[dict[str, Any]]:
    raw = _run("lspci", "-D", "-nn")
    result: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not re.search(r"VGA compatible controller|3D controller|Display controller", line, re.I):
            continue
        pci_address = line.split()[0] if line.split() else ""
        match = re.search(r"\[([0-9a-f]{4}):([0-9a-f]{4})\]", line, re.I)
        result.append({
            "pci_address": pci_address,
            "description": line,
            "vendor_device_id": f"{match.group(1)}:{match.group(2)}" if match else None,
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
                "name": fields[0], "size": fields[2],
                "rotational": fields[3] == "1",
                "model": fields[4] if len(fields) > 4 else "",
            })
    return result


def network_bandwidth() -> dict[str, Any]:
    result = {}
    root = Path("/sys/class/net")
    if root.exists():
        for iface in root.iterdir():
            speed = iface / "speed"
            try:
                value = speed.read_text().strip() if speed.exists() else ""
            except OSError:
                continue
            if value.isdigit() and int(value) > 0:
                result[iface.name] = {"link_mbps": int(value)}
    return result


def optional_tools() -> dict[str, bool]:
    return {name: bool(shutil.which(name)) for name in (
        "nvidia-smi", "rocminfo", "vulkaninfo", "vainfo", "glxinfo"
    )}


def profile() -> dict[str, Any]:
    """Return the canonical physical ``hardware-profile.v1`` source."""
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
        "tools": {name: bool(shutil.which(name)) for name in (
            "lscpu", "free", "lspci", "lsblk"
        )},
        "accelerator_tools": optional_tools(),
        "measurement": {
            "cpu_benchmark": False, "memory_bandwidth": False,
            "disk_benchmark": False, "gpu_benchmark": False,
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
