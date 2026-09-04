#!/usr/bin/env python3
"""RC3 hardware discovery adapter.

``scripts.hardware_profile`` is the single canonical low-level physical probe.
This RC3 adapter only maps that observed profile into the RC3 discovery
contract; it must not maintain a second hardware parser.

Hermes model-fit information is deliberately not treated as hardware
telemetry. Missing optional vendor data remains null/empty rather than guessed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

try:
    # Package import: ``from scripts import rc3_hardware_discovery``.
    from scripts.hardware_profile import profile
except ModuleNotFoundError:
    # Direct execution: ``python scripts/rc3_hardware_discovery.py``.
    from hardware_profile import profile

SCHEMA = "hardware-profile.v1"


def discover() -> dict[str, Any]:
    """Adapt the canonical physical probe to the RC3 discovery contract."""
    source = profile()
    cpu = source.get("cpu") or {}
    memory = source.get("memory") or {}
    gpus = source.get("gpu") or []
    total = memory.get("visible_to_os_bytes")
    available = memory.get("available_bytes")
    nvidia = None
    if source.get("accelerator_tools", {}).get("nvidia-smi"):
        # Vendor probing is intentionally represented by the canonical probe
        # only when it is implemented there; do not synthesize VRAM here.
        nvidia = None

    accelerators = [flag for flag in ("avx", "avx2", "avx512f", "avx512_vnni")
                    if flag in set(cpu.get("flags", []))]
    return {
        "schema": SCHEMA,
        "source": "leones-native-ubuntu",
        "source_version": "rc3",
        "verification": "detected",
        "discovery_timestamp": source.get("observed_at_utc") or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "os": source.get("platform", {}).get("system"),
        "os_release": source.get("platform", {}).get("release"),
        "architecture": source.get("platform", {}).get("machine"),
        "cpu": {
            "model": cpu.get("model"),
            "architecture": cpu.get("architecture"),
            "logical_cpus": cpu.get("logical_cpus"),
            "physical_cores": cpu.get("physical_cores"),
            "cores_per_socket": (
                cpu.get("physical_cores") // cpu.get("sockets")
                if cpu.get("physical_cores") and cpu.get("sockets") else None
            ),
            "sockets": cpu.get("sockets"),
            "threads_per_core": cpu.get("threads_per_core"),
            "flags": cpu.get("flags", []),
        },
        "ram": {
            "total_gb": total / (1024 ** 3) if total is not None else None,
            "available_gb": available / (1024 ** 3) if available is not None else None,
        },
        "gpu": [
            {
                "pci_address": gpu.get("pci_address"),
                "description": gpu.get("description"),
                "vendor_device_id": gpu.get("vendor_device_id"),
                "driver": gpu.get("driver"),
            }
            for gpu in gpus
        ],
        "vram_gb": None,
        "backend": [gpu.get("driver") for gpu in gpus if gpu.get("driver")],
        "accelerators": accelerators,
        "memory_modules": [],
        "vendor_probe": nvidia,
        "hermes": {
            "discovery_cli": "not-exposed",
            "reason": "Hermes 0.21.0 public CLI exposes no stable machine-readable hardware command; native LEONES probe is authoritative.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit an RC3 hardware-profile.v1 from the canonical LEONES physical probe")
    parser.add_argument("-o", "--output", type=Path, help="write JSON artifact to this path")
    args = parser.parse_args()
    payload = json.dumps(discover(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
