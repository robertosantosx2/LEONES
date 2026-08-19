"""Environment manifest generation for reproducible adapter runs."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
from typing import Any


def _version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if text else None


def build_manifest(adapter: str, target: str, version: str, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture reproducibility metadata without collecting secrets."""
    config = config or {}
    safe_config = json.loads(json.dumps(config))
    canonical = json.dumps(safe_config, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema_version": "1.0",
        "adapter": adapter,
        "target": target,
        "version": version,
        "platform": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "kernel": platform.release(),
            "python": platform.python_version(),
            "node": _version(["node", "--version"]) if shutil.which("node") else None,
            "docker": _version(["docker", "--version"]) if shutil.which("docker") else None,
        },
        "model": config.get("model"),
        "runtime": config.get("runtime"),
        "hardware": config.get("hardware"),
        "config_digest": digest,
    }


def write_manifest(manifest: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
