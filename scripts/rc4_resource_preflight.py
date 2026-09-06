#!/usr/bin/env python3
"""RC4 non-invasive resource and software preflight.

Reports current RAM/swap/disk occupancy and detects ODS, Magnitude,
FitLLM/LLMFit, Hermes, OMH and Ollama installations. It never installs, updates or downloads.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "leones.rc4.resource-state.v1"
GIB = 1024 ** 3


def read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if not parts:
            continue
        try:
            n = int(parts[0])
        except ValueError:
            continue
        out[key] = n * 1024 if len(parts) > 1 and parts[1].lower() == "kb" else n
    return out


def memory_state() -> dict[str, Any]:
    m = read_meminfo()
    total = m.get("MemTotal", 0)
    available = m.get("MemAvailable", m.get("MemFree", 0))
    free = m.get("MemFree", 0)
    used = max(0, total - available)
    return {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "free_bytes": free,
        "total_gb": round(total / GIB, 3),
        "used_gb": round(used / GIB, 3),
        "available_gb": round(available / GIB, 3),
        "free_gb": round(free / GIB, 3),
        "source": "/proc/meminfo",
    }


def swap_state() -> dict[str, Any]:
    m = read_meminfo()
    total = m.get("SwapTotal", 0)
    free = m.get("SwapFree", 0)
    used = max(0, total - free)
    return {
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "total_gb": round(total / GIB, 3),
        "used_gb": round(used / GIB, 3),
        "free_gb": round(free / GIB, 3),
        "source": "/proc/meminfo",
    }


def disk_state(path: str) -> dict[str, Any]:
    d = shutil.disk_usage(path)
    return {
        "path": str(Path(path).resolve()),
        "total_bytes": d.total,
        "used_bytes": d.used,
        "free_bytes": d.free,
        "total_gb": round(d.total / GIB, 3),
        "used_gb": round(d.used / GIB, 3),
        "free_gb": round(d.free / GIB, 3),
    }


def command_version(command: str) -> dict[str, Any]:
    path = shutil.which(command)
    if path is None:
        return {"installed": False, "version": None, "path": None, "detected_via": None}
    try:
        proc = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        text = (proc.stdout or proc.stderr or "").strip().splitlines()
        version = text[0] if text else None
        return {
            "installed": True,
            "version": version,
            "path": path,
            "detected_via": "command",
        }
    except (OSError, subprocess.TimeoutExpired):
        return {
            "installed": True,
            "version": None,
            "path": path,
            "detected_via": "command",
        }


def detect_target(
    name: str,
    commands: list[str],
    packages: list[str],
    paths: list[str],
) -> dict[str, Any]:
    for command in commands:
        result = command_version(command)
        if result["installed"]:
            return {
                "name": name,
                **result,
                "size_bytes": None,
                "update_required": None,
                "install_required": False,
                "required_disk_bytes": None,
            }
    for package in packages:
        try:
            proc = subprocess.run(
                ["python3", "-m", "pip", "show", package],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                values = {}
                for line in proc.stdout.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        values[k.strip()] = v.strip()
                return {
                    "name": name,
                    "installed": True,
                    "version": values.get("Version"),
                    "path": values.get("Location"),
                    "detected_via": "python_package",
                    "size_bytes": None,
                    "update_required": None,
                    "install_required": False,
                    "required_disk_bytes": None,
                }
        except (OSError, subprocess.TimeoutExpired):
            pass
    for raw in paths:
        path = Path(raw).expanduser()
        if path.exists():
            return {
                "name": name,
                "installed": True,
                "version": None,
                "path": str(path.resolve()),
                "detected_via": "filesystem",
                "size_bytes": None,
                "update_required": None,
                "install_required": False,
                "required_disk_bytes": None,
            }
    return {
        "name": name,
        "installed": False,
        "version": None,
        "path": None,
        "detected_via": None,
        "size_bytes": None,
        "update_required": None,
        "install_required": True,
        "required_disk_bytes": None,
    }


def collect(root: str = ".") -> dict[str, Any]:
    disk = disk_state(root)
    software = [
        detect_target("ODS", ["ods"], ["ods"], ["~/ods", "~/leones-work/ODS"]),
        detect_target(
            "Magnitude",
            ["magnitude"],
            ["magnitude"],
            ["~/magnitude", "~/leones-work/Magnitude"],
        ),
        detect_target("FitLLM / LLMFit", ["llmfit", "fitllm"], ["llmfit", "fitllm"], []),
        detect_target("Hermes", ["hermes"], ["hermes"], ["~/.hermes", "~/hermes"]),
        detect_target("Oh My Hermes", ["omh"], ["omh"], ["~/.omh"]),
        detect_target("Ollama", ["ollama"], ["ollama"], ["~/.ollama"]),
    ]
    return {
        "schema": SCHEMA,
        "memory": memory_state(),
        "swap": swap_state(),
        "disk": disk,
        "software": software,
        "installation_budget": {
            "disk_free_bytes": disk["free_bytes"],
            "reserved_bytes": 0,
            "available_for_install_bytes": disk["free_bytes"],
            "ods_required_disk_bytes": next(
                x["required_disk_bytes"] for x in software if x["name"] == "ODS"
            ),
            "magnitude_required_disk_bytes": next(
                x["required_disk_bytes"] for x in software if x["name"] == "Magnitude"
            ),
            "fitllm_required_disk_bytes": next(
                x["required_disk_bytes"] for x in software if x["name"] == "FitLLM / LLMFit"
            ),
            "model_artifact_required_disk_bytes": None,
            "runtime_required_disk_bytes": None,
            "safety_margin_bytes": None,
            "status": (
                "requires_sizing_before_install"
                if any(x["install_required"] or x["update_required"] for x in software)
                else "ready_for_next_gate"
            ),
        },
        "rules": {
            "swap_counts_as_ram": False,
            "installation_is_non_invasive": True,
            "unknown_sizes_are_null": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--path", default=".", help="Filesystem to measure for disk budget")
    p.add_argument("--output", default="-", help="JSON output path, or - for stdout")
    args = p.parse_args(argv)
    result = collect(args.path)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output == "-":
        print(text, end="")
    else:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
