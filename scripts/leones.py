#!/usr/bin/env python3
"""Thin entry point for the LEONES measurement pipeline.

The orchestrator intentionally contains almost no domain logic. It documents
and invokes the small scripts that do the actual work.

Pipeline
--------
    hardware -> model -> infer -> lotb -> report -> publish -> stats

At this stage the command supports explicit steps so users can run only the
part they need. The individual scripts remain the canonical implementation
units.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT


def run(script: str, args: list[str]) -> int:
    command = [sys.executable, str(SCRIPTS / script), *args]
    return subprocess.call(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="LEONES thin script orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hardware", help="collect machine information")

    model = sub.add_parser("model", help="inspect a model file")
    model.add_argument("path")

    infer = sub.add_parser("infer", help="measure a local inference endpoint")
    infer.add_argument("--url", required=True)
    infer.add_argument("--model", required=True)

    lotb = sub.add_parser("lotb", help="run LOTB")
    lotb.add_argument("--endpoint", required=True)
    lotb.add_argument("--task", default="all")

    args, remainder = parser.parse_known_args()

    if args.command == "hardware":
        return run("leones-hardware.py", [])
    if args.command == "model":
        return run("leones-model.py", [args.path])
    if args.command == "infer":
        return run("leones-infer.py", ["--url", args.url, "--model", args.model, *remainder])
    if args.command == "lotb":
        return run("leones-lotb.py", ["--endpoint", args.endpoint, "--task", args.task, *remainder])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
