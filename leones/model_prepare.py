"""Validate one already-downloaded model file.

One responsibility: check that a local file exists, has a supported extension,
and optionally matches an expected SHA-256. It does not download, convert,
quantize or execute models.

Example:
    python -m leones.model_prepare models/model.gguf --sha256 <64-hex>
"""

import argparse
import hashlib
from pathlib import Path

SUPPORTED_FORMATS = {".gguf", ".safetensors", ".bin", ".onnx"}


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate SHA-256 without loading the whole model into RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate(path: Path, expected_sha256: str | None = None) -> None:
    """Raise ValueError when the local model file is not acceptable."""
    if not path.is_file():
        raise ValueError(f"Model file does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported model extension: {path.suffix}")
    if expected_sha256 and sha256(path).lower() != expected_sha256.lower():
        raise ValueError("SHA-256 verification failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a local LEONES model file.")
    parser.add_argument("path")
    parser.add_argument("--sha256")
    args = parser.parse_args()
    validate(Path(args.path), args.sha256)
    print(f"valid: {args.path}")


if __name__ == "__main__":
    main()
