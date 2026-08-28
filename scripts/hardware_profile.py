#!/usr/bin/env python3
"""Collect a reproducible Linux hardware profile for LEONES model selection.

The probe reports observed host facts only. It does not infer model fit and it
does not benchmark a model. Expensive measurements are opt-in; the default
profile is safe to run on a Debian/Ubuntu workstation.
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


def cpu() -> dict[str, Any]:
    """Return CPU facts using locale-independent Linux sources."""
    raw = _run("lscpu")
    info = {}

    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()

    model = None
    proc_cpuinfo = Path("/proc/cpuinfo")
    if proc_cpuinfo.exists():
        try:
            for line in proc_cpuinfo.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                if line.lower().startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    if model:
                        break
        except OSError:
            pass

    if not model:
        for key in (
            "Model name",
            "Nombre del modelo",
            "Nom du modèle",
            "Modellname",
        ):
            if info.get(key):
                model = info[key]
                break

    if not model:
        model = platform.processor() or None

    threads_value = info.get("CPU(s)")
    threads = (
        int(threads_value)
        if threads_value and threads_value.isdigit()
        else os.cpu_count()
    )

    # Physical cores: /proc/cpuinfo is locale-independent and works even
    # when lscpu is translated.
    physical_cores = set()
    if proc_cpuinfo.exists():
        try:
            blocks = proc_cpuinfo.read_text(
                encoding="utf-8", errors="ignore"
            ).split("\n\n")
            for block in blocks:
                values = {}
                for line in block.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        values[key.strip()] = value.strip()

                processor = values.get("processor")
                if processor is None:
                    continue

                physical_id = values.get("physical id", "0")
                core_id = values.get("core id", processor)
                physical_cores.add((physical_id, core_id))
        except OSError:
            pass

    cores = len(physical_cores) or None

    return {
        "model": model,
        "cores": cores,
        "threads": threads,
        "architecture": info.get("Architecture", platform.machine()),
        "mhz": _num(info.get("CPU MHz", "")),
        "cache_l3": info.get("L3 cache"),
    }


def memory() -> dict[str, Any]:
    mem = {}
    raw = _run("free", "-b")
    for line in raw.splitlines():
        if line.startswith("Mem:"):
            fields = line.split()
            if len(fields) >= 7:
                mem = {"total_bytes": int(fields[1]), "available_bytes": int(fields[6])}
    return mem


def gpu() -> list[dict[str, str]]:
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
    """Return interface link speed where Linux exposes it; no traffic test.

    Sysfs entries under /sys/class/net are not uniformly readable across
    physical, virtual and container/host interfaces. A single unreadable
    interface must never invalidate the complete hardware profile.
    """
    result = {}
    root = Path("/sys/class/net")

    try:
        interfaces = list(root.iterdir())
    except (OSError, PermissionError):
        return result

    for iface in interfaces:
        speed = iface / "speed"

        try:
            if not speed.exists():
                continue
            value = speed.read_text(encoding="utf-8").strip()
        except (OSError, PermissionError, ValueError):
            continue

        try:
            link_mbps = int(value)
        except (TypeError, ValueError):
            continue

        if link_mbps > 0:
            result[iface.name] = {"link_mbps": link_mbps}

    return result


def profile() -> dict[str, Any]:
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
