"""Deterministic graders for the first Agentic Benchmark tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Grade:
    status: str
    score: float | None
    checks: tuple[str, ...]


def grade_file_exists(root: Path, relative: str) -> Grade:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return Grade("failed", 0.0, ("path_outside_root",))
    if not path.is_file():
        return Grade("failed", 0.0, ("file_missing",))
    return Grade("success", 1.0, ("file_exists",))


def grade_text_equals(root: Path, relative: str, expected: str) -> Grade:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
        actual = path.read_text(encoding="utf-8")
    except (ValueError, OSError, UnicodeError):
        return Grade("failed", 0.0, ("artifact_unreadable",))
    if actual != expected:
        return Grade("failed", 0.0, ("content_mismatch",))
    return Grade("success", 1.0, ("content_matches",))


def grade_required_files(root: Path, required: Iterable[str]) -> Grade:
    missing = []
    root = root.resolve()
    for relative in required:
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            missing.append(relative)
            continue
        if not path.is_file():
            missing.append(relative)
    if missing:
        return Grade("failed", 0.0, tuple(f"missing:{item}" for item in missing))
    return Grade("success", 1.0, tuple(f"present:{item}" for item in required))
