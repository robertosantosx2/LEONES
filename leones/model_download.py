"""Download one model file and optionally verify its SHA-256.

One responsibility: download a single explicitly supplied URL to a single
explicit destination. It does not choose models, inspect licenses, execute
models, or modify the Atlas catalog.
"""

import hashlib
from pathlib import Path
from urllib.request import urlopen

from .model_source import ModelSource


def download(source: ModelSource, destination: str | Path, chunk_size: int = 1024 * 1024) -> Path:
    """Download *source* and return the destination after optional hash check."""
    source.validate()
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    with urlopen(source.url) as response, target.open("wb") as output:
        while chunk := response.read(chunk_size):
            digest.update(chunk)
            output.write(chunk)

    if source.sha256 and digest.hexdigest().lower() != source.sha256.lower():
        target.unlink(missing_ok=True)
        raise ValueError("SHA-256 verification failed; downloaded file was removed")

    return target
