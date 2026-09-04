#!/usr/bin/env python3
"""RC3 physical hardware discovery.

The RC3 contract never treats Hermes' model-fit UI as authoritative hardware
telemetry.  Hermes currently has local-runtime hardware logic, but its public
CLI exposes no stable machine-readable hardware command.  Therefore this
adapter collects the physical facts directly from the Ubuntu host and emits a
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
    text = _run("lscpu")
    logical = _first(r"^CPU\(s\):\s+(\d+)", text)
    cores = _first(r"^Core\(s\) per socket:\s+(\d+)", text)
    sockets = _first(r"^Socket\(s\):\s+(\d+)", text)
    threads = int(logical) if logical else None
    return {
        "model": _first(r"^Model name:\s+(.+)$", text),
        "architecture": _first(r"^Architecture:\s+(.+)$", text),
        "logical_cpus": threads,
        "cores_per_socket": int(cores) if cores else None,
        "sockets": int(sockets) if sockets else None,
        "flags": (_first(r"^Flags:\s+(.+)$", text)
                  or _first(r"^Features:\s+(.+)$", text) or "").split(),
    }


def _gpus() -> list[dict[str, Any]]:
    text = _run("lspci", "-nnk")
    result: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if re.search(r"VGA compatible controller|3D controller|Display controller", line, re.I):
            if current:
                result.append(current)
            m = re.match(r"([^ ]+)\s+(.+?)\s+\[(?:[0-9a-f]{4}):([0-9a-f]{4})\]", line, re.I)
            current = {
                "pci_address": (m.group(1) if m else line.split()[0]),
                "description": (m.group(2).strip() if m else line.strip()),
                "vendor_device_id": (m.group(3) if m else None),
                "driver": None,
            }
        elif current:
            driver = _first(r"Kernel driver in use:\s+(.+)$", line)
            if driver:
                current["driver"] = driver
    if current:
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
            rows.append({"name": parts[0], "vram_gb": float(parts[1]) / 1024,
                         "free_vram_gb": float(parts[2]) / 1024, "driver": parts[3]})
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
