#!/usr/bin/env python3
"""Validate an Agentic Benchmark result against the repository JSON schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "result.schema.json"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} RESULT.json", file=sys.stderr)
        return 2

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("jsonschema is required to validate benchmark results", file=sys.stderr)
        return 2

    result_path = Path(sys.argv[1])
    with result_path.open(encoding="utf-8") as handle:
        result = json.load(handle)
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(result), key=lambda error: list(error.path))
    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "$"
            print(f"{location}: {error.message}", file=sys.stderr)
        return 1

    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
