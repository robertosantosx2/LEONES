"""Common V1.1 runtime registry and adapter boundary."""
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
    aliases: tuple[str, ...]
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
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("runtimes"), list):
        raise ValueError("invalid runtime registry")
    return data


def _as_strings(raw: Any, field: str, runtime_id: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or any(not isinstance(value, str) or not value for value in raw):
        raise ValueError(f"runtime {runtime_id} has invalid {field}")
    return tuple(raw)


def registry_entries(path: Path = REGISTRY_PATH) -> dict[str, RuntimeEntry]:
    entries: dict[str, RuntimeEntry] = {}
    identities: dict[str, str] = {}
    required = {
        "id", "adapter", "version", "modes", "architectures", "formats", "backends",
        "capabilities", "entrypoint", "availability", "metrics", "physical_test_required",
    }
    for raw in load_registry(path)["runtimes"]:
        if not isinstance(raw, dict) or not required.issubset(raw):
            raise ValueError("runtime registry entry is missing required fields")
        runtime_id = raw["id"]
        if not isinstance(runtime_id, str) or not runtime_id:
            raise ValueError("runtime registry entry has invalid id")
        aliases = _as_strings(raw.get("aliases", []), "aliases", runtime_id)
        if runtime_id in identities or any(alias in identities for alias in aliases):
            raise ValueError(f"duplicate runtime registry identity: {runtime_id}")
        if runtime_id in aliases:
            raise ValueError(f"runtime {runtime_id} lists itself as an alias")
        entrypoint = raw["entrypoint"]
        if not isinstance(entrypoint, dict) or not isinstance(entrypoint.get("kind"), str) or not entrypoint["kind"]:
            raise ValueError(f"runtime {runtime_id} has an invalid entrypoint")
        argv = entrypoint.get("argv")
        if not isinstance(argv, list) or any(not isinstance(value, str) for value in argv):
            raise ValueError(f"runtime {runtime_id} has an invalid entrypoint argv")
        if not isinstance(raw["physical_test_required"], bool):
            raise ValueError(f"runtime {runtime_id} has invalid physical_test_required")
        entry = RuntimeEntry(
            id=runtime_id,
            adapter=raw["adapter"],
            version=raw["version"],
            aliases=aliases,
            modes=_as_strings(raw["modes"], "modes", runtime_id),
            architectures=_as_strings(raw["architectures"], "architectures", runtime_id),
            formats=_as_strings(raw["formats"], "formats", runtime_id),
            backends=_as_strings(raw["backends"], "backends", runtime_id),
            capabilities=_as_strings(raw["capabilities"], "capabilities", runtime_id),
            entrypoint=dict(entrypoint),
            availability=raw["availability"],
            metrics=raw["metrics"],
            physical_test_required=raw["physical_test_required"],
        )
        entries[entry.id] = entry
        identities[entry.id] = entry.id
        for alias in aliases:
            if alias in identities:
                raise ValueError(f"duplicate runtime registry alias: {alias}")
            identities[alias] = entry.id
    return entries


def capability_match(entry: RuntimeEntry, *, architecture: str | None = None, model_format: str | None = None,
                      mode: str | None = None, backend: str | None = None,
                      required_capabilities: set[str] | None = None) -> tuple[bool, list[str]]:
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
    argv = ep.get("argv") if isinstance(ep, Mapping) else None
    if not isinstance(ep, Mapping) or not ep.get("kind") or not isinstance(argv, list) or any(not isinstance(x, str) for x in argv):
        raise ValueError(f"runtime {entry.id} has an invalid trusted entrypoint")


def get_runtime(runtime_id: str, path: Path = REGISTRY_PATH) -> RuntimeEntry:
    entries = registry_entries(path)
    if runtime_id in entries:
        entry = entries[runtime_id]
    else:
        entry = next((item for item in entries.values() if runtime_id in item.aliases), None)
        if entry is None:
            raise ValueError(f"unknown runtime: {runtime_id}")
    validate_entrypoint(entry)
    return entry
