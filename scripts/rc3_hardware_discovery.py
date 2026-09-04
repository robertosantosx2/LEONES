#!/usr/bin/env python3
"""RC3 physical hardware discovery.

The RC3 contract never treats Hermes' model-fit UI as authoritative hardware
telemetry. Hermes currently has local-runtime hardware logic, but its public
CLI exposes no stable machine-readable hardware command. Therefore this
adapter collects physical facts directly from the Ubuntu host and emits a
stable ``hardware-profile.v1`` artifact with explicit provenance.

This is discovery, not benchmarking: no performance number is inferred here.
Optional vendor tools are used only when present. Missing tools become explicit
``null``/empty fields rather than fabricated values.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
from typing import Any

SCHEMA = "hardware-profile.v1"


def _run(*argv: str, timeout: float = 5.0) -> str:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return p.stdout


def _first(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.I | re.M)
    return m.group(1).strip() if m else None


def _ram() -> tuple[float | None, float | None]:
    text = _run("free", "-b")
    m = re.search(r"^Mem:\s+(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)", text, re.M)
    if not m:
        return None, None
    return int(m.group(1)) / (1024**3), int(m.group(2)) / (1024**3)


def _cpu() -> dict[str, Any]:
    # lscpu is locale-sensitive; use /proc/cpuinfo for model/flags and the
    # machine-readable CSV mode of lscpu for topology.
    cpuinfo = _run("cat", "/proc/cpuinfo")
    model = _first(r"^model name\s*:\s*(.+)$", cpuinfo)
    flags_text = _first(r"^(?:flags|Features)\s*:\s*(.+)$", cpuinfo) or ""

    topology = _run("lscpu", "-p=CPU,Core,Socket")
    rows: list[tuple[int, int, int]] = []
    for line in topology.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) >= 3:
            try:
                rows.append((int(parts[0]), int(parts[1]), int(parts[2])))
            except ValueError:
                pass

    logical = len({r[0] for r in rows}) or None
    cores = len({(r[1], r[2]) for r in rows}) or None
    sockets = len({r[2] for r in rows}) or None
    cores_per_socket = None
    if sockets:
        cores_per_socket = cores // sockets if cores is not None else None

    return {
        "model": model,
        "architecture": platform.machine(),
        "logical_cpus": logical,
        "cores_per_socket": cores_per_socket,
        "sockets": sockets,
        "flags": sorted(set(flags_text.split())),
    }


def _gpus() -> list[dict[str, Any]]:
    text = _run("lspci", "-nnk")
    result: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if re.search(r"VGA compatible controller|3D controller|Display controller", line, re.I):
            if current:
                result.append(current)
            m = re.match(r"([^ ]+)\s+(.+?)\s+\[([0-9a-f]{4}):([0-9a-f]{4})\]", line, re.I)
            current = {
                "pci_address": (m.group(1) if m else line.split()[0]),
                "description": (m.group(2).strip() if m else line.strip()),
                "vendor_device_id": (f"{m.group(3)}:{m.group(4)}" if m else None),
                "driver": None,
            }
        elif current:
            m_driver = re.search(r"^\s*Kernel driver in use:\s*(\S+)\s*$", line, re.I)
            if m_driver:
                current["driver"] = m_driver.group(1)
            # A new unrelated PCI function ends the current device's metadata.
            if re.match(r"^[0-9a-f]+:[0-9a-f]+\.[0-9a-f]+\s", line, re.I):
                if current and current not in result:
                    result.append(current)
                current = None
    if current and current not in result:
        result.append(current)
    return result


def _nvidia() -> dict[str, Any] | None:
    if not shutil.which("nvidia-smi"):
        return None
    out = _run("nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
               "--format=csv,noheader,nounits", timeout=10)
    rows = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            try:
                rows.append({"name": parts[0], "vram_gb": float(parts[1]) / 1024,
                             "free_vram_gb": float(parts[2]) / 1024, "driver": parts[3]})
            except ValueError:
                continue
    return {"tool": "nvidia-smi", "gpus": rows} if rows else None


def _memory_modules() -> list[dict[str, Any]]:
    if not shutil.which("dmidecode") or os.geteuid() != 0:
        return []
    text = _run("dmidecode", "-t", "memory", timeout=10)
    modules = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        size = _first(r"^\s*Size:\s+(.+)$", block)
        if not size or size.lower().startswith("no module"):
            continue
        modules.append({
            "size": size,
            "type": _first(r"^\s*Type:\s+(.+)$", block),
            "speed": _first(r"^\s*Speed:\s+(.+)$", block),
            "manufacturer": _first(r"^\s*Manufacturer:\s+(.+)$", block),
            "part_number": _first(r"^\s*Part Number:\s+(.+)$", block),
        })
    return modules


def discover() -> dict[str, Any]:
    ram_total, ram_available = _ram()
    cpu = _cpu()
    gpus = _gpus()
    nvidia = _nvidia()
    accelerators = []
    flags = set(cpu.get("flags", []))
    for flag in ("avx", "avx2", "avx512f", "avx512_vnni"):
        if flag in flags:
            accelerators.append(flag)
    return {
        "schema": SCHEMA,
        "source": "leones-native-ubuntu",
        "source_version": "rc3",
        "verification": "detected",
        "discovery_timestamp": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": cpu,
        "ram": {"total_gb": ram_total, "available_gb": ram_available},
        "gpu": gpus,
        "vram_gb": (nvidia["gpus"][0]["vram_gb"] if nvidia and nvidia["gpus"] else None),
        "backend": [g.get("driver") for g in gpus if g.get("driver")],
        "accelerators": accelerators,
        "memory_modules": _memory_modules(),
        "vendor_probe": nvidia,
        "hermes": {
            "discovery_cli": "not-exposed",
            "reason": "Hermes 0.21.0 public CLI exposes no stable machine-readable hardware command; native probes are authoritative.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit an RC3 hardware-profile.v1 from the local Ubuntu host")
    parser.add_argument("-o", "--output", type=Path, help="write JSON artifact to this path")
    args = parser.parse_args()
    artifact = discover()
    payload = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
