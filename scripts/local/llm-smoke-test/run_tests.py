#!/usr/bin/env python3
"""Run the complete dependency-free test suite for llm-smoke-test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = sorted((ROOT / "tests").glob("test_*.py"))


def main() -> int:
    if not TESTS:
        print("ERROR: no tests found")
        return 1

    failures = 0
    for test in TESTS:
        print(f"\n==> {test.relative_to(ROOT)}")
        completed = subprocess.run([sys.executable, str(test)], check=False)
        if completed.returncode != 0:
            failures += 1

    if failures:
        print(f"\nFAIL: {failures} test module(s) failed")
        return 1

    print(f"\nPASS: {len(TESTS)} test module(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
