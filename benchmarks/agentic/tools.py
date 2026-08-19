"""Explicit, sandbox-oriented tool adapters for Agentic Benchmark V1.

The benchmark never exposes an unrestricted subprocess or filesystem to a
model. Callers construct a Sandbox and register only the operations required
by a task.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence


class SandboxViolation(PermissionError):
    """Raised when an operation escapes the configured sandbox."""


@dataclass(frozen=True)
class Sandbox:
    root: Path
    allow_shell: bool = False
    allow_network: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, relative: str) -> Path:
        """Resolve a relative sandbox path and reject traversal."""
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise SandboxViolation(f"path outside sandbox: {relative}") from exc
        return candidate

    def read_text(self, relative: str) -> str:
        return self.path(relative).read_text(encoding="utf-8")

    def write_text(self, relative: str, content: str) -> None:
        destination = self.path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def list_files(self, relative: str = ".") -> list[str]:
        directory = self.path(relative)
        return sorted(
            str(item.relative_to(self.root))
            for item in directory.rglob("*")
            if item.is_file()
        )

    def shell(self, argv: Sequence[str], *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
        """Run an explicitly supplied argv inside the sandbox.

        No shell=True, network policy is deliberately not emulated here, and
        commands must be approved by the task adapter before calling this.
        """
        if not self.allow_shell:
            raise SandboxViolation("shell is disabled for this task")
        if not argv:
            raise ValueError("argv must not be empty")
        return subprocess.run(
            list(argv),
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
