#!/usr/bin/env python3
"""Safe GGUF artifact acquisition with cache, provenance and checksum checks."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_path(cache_dir: Path, filename: str) -> Path:
    return cache_dir / f"{filename}.leones.json"


def acquire_artifact(*, url: str, cache_dir: str | Path, model_id: str,
                     quantization: str, revision: str | None = None,
                     expected_sha256: str | None = None, filename: str | None = None,
                     timeout: int = 120) -> dict[str, Any]:
    """Acquire one explicitly requested artifact atomically.

    The caller supplies the exact URL; this function never chooses a model or
    quantization. Verification happens before the final cache rename.
    """
    if not url or not model_id or not quantization:
        raise ValueError("url, model_id and quantization are required")
    if not url.startswith(("https://", "http://")):
        raise ValueError("artifact URL must be HTTP(S)")

    cache = Path(cache_dir).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    name = filename or Path(urlparse(url).path).name
    if not name:
        raise ValueError("artifact filename cannot be inferred")
    target = cache / name
    expected = expected_sha256.lower() if expected_sha256 else None

    if target.is_file():
        actual = _sha256(target)
        if expected and actual != expected:
            return {"status": "CHECKSUM_MISMATCH", "artifact": str(target), "sha256": actual}
        return {"status": "CACHE_HIT", "artifact": str(target), "sha256": actual,
                "provenance": str(_metadata_path(cache, name))}

    fd, tmp_name = tempfile.mkstemp(prefix=f".{name}.", dir=cache)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, tmp.open("wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
        actual = _sha256(tmp)
        if expected and actual != expected:
            return {"status": "CHECKSUM_MISMATCH", "artifact": None, "sha256": actual}
        os.replace(tmp, target)
        metadata = {
            "schema_version": "1.0", "model_id": model_id,
            "quantization": quantization,
            "source": "huggingface" if "huggingface.co" in url else "http",
            "url": url, "revision": revision, "filename": name,
            "size_bytes": target.stat().st_size, "sha256": actual,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path = _metadata_path(cache, name)
        meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"status": "ACQUIRED", "artifact": str(target), "sha256": actual,
                "provenance": str(meta_path)}
    finally:
        if tmp.exists():
            tmp.unlink()
