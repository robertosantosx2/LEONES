#!/usr/bin/env python3
"""Safe GGUF artifact acquisition/removal with provenance, checksums and progress."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from runtime_selection.operation_progress import OperationPhase, OperationProgress, terminal_progress

ProgressCallback = Callable[[OperationProgress], None]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_path(cache_dir: Path, filename: str) -> Path:
    return cache_dir / f"{filename}.leones.json"


def _emit(callback: ProgressCallback | None, progress: OperationProgress) -> None:
    if callback is not None:
        callback(progress)


def acquire_artifact(
    *,
    url: str,
    cache_dir: str | Path,
    model_id: str,
    quantization: str,
    revision: str | None = None,
    expected_sha256: str | None = None,
    filename: str | None = None,
    timeout: int = 120,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Acquire one explicitly requested artifact atomically.

    ``progress_callback`` receives visible operation state for TUI/CLI use.
    Download progress is determinate when Content-Length is available;
    otherwise activity is still emitted so the UI never looks frozen.
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

    _emit(progress_callback, OperationProgress("install", OperationPhase.PREPARING, detail=name))

    if target.is_file():
        actual = _sha256(target)
        if expected and actual != expected:
            _emit(progress_callback, terminal_progress("install", False, "checksum mismatch"))
            return {"status": "CHECKSUM_MISMATCH", "artifact": str(target), "sha256": actual}
        _emit(progress_callback, terminal_progress("install", True, "cache hit"))
        return {
            "status": "CACHE_HIT",
            "artifact": str(target),
            "sha256": actual,
            "provenance": str(_metadata_path(cache, name)),
        }

    fd, tmp_name = tempfile.mkstemp(prefix=f".{name}.", dir=cache)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, tmp.open("wb") as out:
            total_header = response.headers.get("Content-Length")
            total_bytes = int(total_header) if total_header and total_header.isdigit() else None
            current_bytes = 0
            started = time.monotonic()
            _emit(
                progress_callback,
                OperationProgress(
                    "install", OperationPhase.DOWNLOADING,
                    current_bytes=0 if total_bytes is not None else None,
                    total_bytes=total_bytes,
                    detail=name,
                ),
            )
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
                current_bytes += len(block)
                elapsed = max(time.monotonic() - started, 1e-9)
                rate = current_bytes / elapsed
                eta = ((total_bytes - current_bytes) / rate) if total_bytes and rate > 0 else None
                _emit(
                    progress_callback,
                    OperationProgress(
                        "install", OperationPhase.DOWNLOADING,
                        current_bytes=current_bytes if total_bytes is not None else None,
                        total_bytes=total_bytes,
                        rate_bytes_per_second=rate,
                        eta_seconds=eta,
                        detail=name,
                    ),
                )

        _emit(progress_callback, OperationProgress("install", OperationPhase.VERIFYING, detail=name))
        actual = _sha256(tmp)
        if expected and actual != expected:
            _emit(progress_callback, terminal_progress("install", False, "checksum mismatch"))
            return {"status": "CHECKSUM_MISMATCH", "artifact": None, "sha256": actual}
        os.replace(tmp, target)
        metadata = {
            "schema_version": "1.0",
            "model_id": model_id,
            "quantization": quantization,
            "source": "huggingface" if "huggingface.co" in url else "http",
            "url": url,
            "revision": revision,
            "filename": name,
            "size_bytes": target.stat().st_size,
            "sha256": actual,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path = _metadata_path(cache, name)
        meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _emit(progress_callback, terminal_progress("install", True, "artifact acquired"))
        return {"status": "ACQUIRED", "artifact": str(target), "sha256": actual, "provenance": str(meta_path)}
    except Exception as exc:
        _emit(progress_callback, terminal_progress("install", False, str(exc)))
        raise
    finally:
        if tmp.exists():
            tmp.unlink()


def remove_artifact(
    *,
    cache_dir: str | Path,
    filename: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Remove one cached artifact and its LEONES provenance sidecar.

    The operation is deliberately explicit: the caller supplies the exact
    filename. It never performs broad cache cleanup or model selection.
    """
    if not filename or Path(filename).name != filename:
        raise ValueError("filename must name one artifact in cache_dir")
    cache = Path(cache_dir).expanduser()
    target = cache / filename
    metadata = _metadata_path(cache, filename)
    _emit(progress_callback, OperationProgress("uninstall", OperationPhase.PREPARING, detail=filename))
    if not target.exists() and not metadata.exists():
        _emit(progress_callback, terminal_progress("uninstall", True, "already absent"))
        return {"status": "ABSENT", "artifact": str(target), "provenance": str(metadata)}
    try:
        _emit(progress_callback, OperationProgress("uninstall", OperationPhase.REMOVING, detail=filename))
        if target.exists():
            target.unlink()
        if metadata.exists():
            metadata.unlink()
        _emit(progress_callback, terminal_progress("uninstall", True, "artifact removed"))
        return {"status": "REMOVED", "artifact": str(target), "provenance": str(metadata)}
    except Exception as exc:
        _emit(progress_callback, terminal_progress("uninstall", False, str(exc)))
        raise
