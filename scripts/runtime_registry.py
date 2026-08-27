"""Common V1.1 runtime registry and adapter boundary.

The selector consumes declarative capabilities. It never imports a concrete
runtime adapter and never constructs runtime commands.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "runtime_registry.v1.1.json"
SCHEMA_VERSION = "runtime-registry.v1.1"


@dataclass(frozen=True)
class RuntimeEntry:
    id: str
    adapter: str
    version: str
    modes: tuple[str, ...]
    architectures: tuple[str, ...]
    formats: tuple[str, ...]
    backends: tuple[str, ...]
    capabilities: tuple[str, ...]
    entrypoint: Mapping[str, Any]
    availability: str
    metrics: str
    physical_test_required: bool


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported runtime registry schema")
    if not isinstance(data.get("runtimes"), list):
        raise ValueError("runtime registry must contain a runtimes list")
    return data


def registry_entries(path: Path = REGISTRY_PATH) -> dict[str, RuntimeEntry]:
    data = load_registry(path)
    entries: dict[str, RuntimeEntry] = {}
    for raw in data["runtimes"]:
        entry = RuntimeEntry(
            id=raw["id"], adapter=raw["adapter"], version=raw["version"],
            modes=tuple(raw["modes"]), architectures=tuple(raw["architectures"]),
            formats=tuple(raw["formats"]), backends=tuple(raw["backends"]),
            capabilities=tuple(raw["capabilities"]), entrypoint=dict(raw["entrypoint"]),
            availability=raw["availability"], metrics=raw["metrics"],
            physical_test_required=bool(raw["physical_test_required"]),
        )
        if entry.id in entries:
            raise ValueError(f"duplicate runtime id: {entry.id}")
        entries[entry.id] = entry
    return entries


def capability_match(entry: RuntimeEntry, *, architecture: str | None = None,
                      model_format: str | None = None, mode: str | None = None,
                      backend: str | None = None, required_capabilities: set[str] | None = None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if architecture and architecture not in entry.architectures:
        reasons.append(f"architecture unsupported: {architecture}")
    if model_format and model_format not in entry.formats:
        reasons.append(f"format unsupported: {model_format}")
    if mode and mode not in entry.modes:
        reasons.append(f"execution mode unsupported: {mode}")
    if backend and backend not in entry.backends:
        reasons.append(f"backend unsupported: {backend}")
    missing = sorted((required_capabilities or set()) - set(entry.capabilities))
    if missing:
        reasons.append("missing capabilities: " + ", ".join(missing))
    return not reasons, reasons


def validate_entrypoint(entry: RuntimeEntry) -> None:
    ep = entry.entrypoint
    if not isinstance(ep, Mapping) or not ep.get("kind"):
        raise ValueError(f"runtime {entry.id} has no trusted entrypoint")
    argv = ep.get("argv")
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        raise ValueError(f"runtime {entry.id} has an invalid trusted entrypoint")


def get_runtime(runtime_id: str, path: Path = REGISTRY_PATH) -> RuntimeEntry:
    entries = registry_entries(path)
    try:
        entry = entries[runtime_id]
    except KeyError as exc:
        raise ValueError(f"unknown runtime: {runtime_id}") from exc
    validate_entrypoint(entry)
    return entry
