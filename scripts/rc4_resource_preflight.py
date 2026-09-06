#!/usr/bin/env python3
"""RC4 non-invasive resource and software preflight.

Reports current RAM/swap/disk occupancy and detects ODS, Magnitude and
FitLLM/LLMFit installations. It never installs, updates or downloads.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "leones.rc4.resource-state.v1"
GIB = 1024 ** 3


def _num(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def read_meminfo(path: str = "/proc/meminfo") -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            value = _num(parts[1])
            unit = parts[2].lower() if len(parts) >= 3 else "kb"
            if unit == "kb":
                value *= 1024
            elif unit == "mb":
                value *= 1024 ** 2
            elif unit == "gb":
                value *= GIB
            out[parts[0][:-1]] = value
    return out


def memory_state(meminfo: dict[str, int]) -> dict[str, Any]:
    total = meminfo.get("MemTotal", 0)
    available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    free = meminfo.get("MemFree", 0)
    return {
        "total_bytes": total,
        "used_bytes": max(0, total - available),
        "free_bytes": free,
        "available_bytes": available,
        "total_gib": round(total / GIB, 3),
        "used_gib": round(max(0, total - available) / GIB, 3),
        "available_gib": round(available / GIB, 3),
    }


def swap_state(meminfo: dict[str, int]) -> dict[str, Any]:
    total = meminfo.get("SwapTotal", 0)
    free = meminfo.get("SwapFree", 0)
    used = max(0, total - free)
    return {
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "total_gib": round(total / GIB, 3),
        "used_gib": round(used / GIB, 3),
        "free_gib": round(free / GIB, 3),
    }


def disk_state(path: str = ".") -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "path": str(Path(path).resolve()),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "total_gib": round(usage.total / GIB, 3),
        "used_gib": round(usage.used / GIB, 3),
        "free_gib": round(usage.free / GIB, 3),
    }


def run_version(command: str, timeout: float = 3.0) -> str | None:
    try:
        proc = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (proc.stdout or proc.stderr).strip()
    return text.splitlines()[0][:500] if text else None


def directory_size(path: Path) -> int | None:
    if not path.exists():
        return None
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return None
    total = 0
    try:
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
            except OSError:
                continue
    except OSError:
        return None
    return total


def detect_python_package(names: Iterable[str]) -> dict[str, Any] | None:
    for name in names:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "show", name],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            continue
        fields: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        return {
            "package": name,
            "version": fields.get("Version"),
            "path": fields.get("Location"),
            "detected_via": "python-pip-show",
        }
    return None


def detect_software(
    name: str,
    commands: Iterable[str],
    packages: Iterable[str],
    paths: Iterable[Path],
) -> dict[str, Any]:
    for command in commands:
        path = shutil.which(command)
        if path:
            return {
                "name": name,
                "installed": True,
                "version": run_version(path),
                "detected_via": "command",
                "path": path,
                "size_bytes": None,
                "update_required": None,
                "install_required": False,
                "required_disk_bytes": None,
            }

    package = detect_python_package(packages)
    if package:
        return {
            "name": name,
            "installed": True,
            "version": package.get("version"),
            "detected_via": package.get("detected_via"),
            "path": package.get("path"),
            "size_bytes": None,
            "update_required": None,
            "install_required": False,
            "required_disk_bytes": None,
        }

    for candidate in paths:
        if candidate.exists():
            return {
                "name": name,
                "installed": True,
                "version": None,
                "detected_via": "path",
                "path": str(candidate),
                "size_bytes": directory_size(candidate),
                "update_required": None,
                "install_required": False,
                "required_disk_bytes": None,
            }

    return {
        "name": name,
        "installed": False,
        "version": None,
        "detected_via": None,
        "path": None,
        "size_bytes": None,
        "update_required": None,
        "install_required": True,
        "required_disk_bytes": None,
    }


def collect_resource_state(root: str = ".") -> dict[str, Any]:
    meminfo = read_meminfo()
    root_path = Path(root).resolve()
    home = Path.home()
    software = [
        detect_software(
            "ODS",
            ("ods",),
            ("ods",),
            (home / "ods", home / "leones-work" / "ODS"),
        ),
        detect_software(
            "Magnitude",
            ("magnitude",),
            ("magnitude",),
            (home / "magnitude", home / "leones-work" / "magnitude"),
        ),
        detect_software(
            "FitLLM / LLMFit",
            ("llmfit", "fitllm"),
            ("llmfit", "fitllm"),
            (home / "llmfit", home / "fitllm", home / "leones-work" / "llmfit", home / "leones-work" / "fitllm"),
        ),
    ]
    disk = disk_state(str(root_path))
    return {
        "schema": SCHEMA,
        "resource_state": {
            "memory": memory_state(meminfo),
            "swap": swap_state(meminfo),
            "disk": disk,
            "software": software,
        },
        "disk_budget": {
            "free_bytes": disk["free_bytes"],
            "reserved_bytes": 0,
            "available_for_install_bytes": disk["free_bytes"],
            "required_bytes_known": False,
            "note": "Install/update/model artifact sizes are not invented; they must be resolved before mutation.",
        },
        "policy": {
            "swap_counts_as_ram": False,
            "external_evidence_is_measured": False,
            "automatic_install_or_update": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=".", help="filesystem path whose disk is evaluated")
    parser.add_argument("--output", default="-", help="JSON output path, or - for stdout")
    args = parser.parse_args(argv)
    state = collect_resource_state(args.path)
    payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        print(payload, end="")
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
