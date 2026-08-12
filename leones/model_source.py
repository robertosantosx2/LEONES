"""Describe a model source without downloading it.

One responsibility: represent a source URL and an optional expected SHA-256.
This module performs no network access and no file operations.
"""

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ModelSource:
    url: str
    sha256: str | None = None

    def validate(self) -> None:
        """Reject obviously invalid source metadata."""
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid model source URL: {self.url}")
        if self.sha256 is not None and len(self.sha256) != 64:
            raise ValueError("SHA-256 must contain 64 hexadecimal characters")
        if self.sha256 is not None:
            int(self.sha256, 16)
