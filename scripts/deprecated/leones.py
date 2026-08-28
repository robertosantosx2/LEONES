#!/usr/bin/env python3
"""Historical thin orchestrator retained for provenance.

RC1 exposes the individual canonical boundaries directly instead of keeping a
second orchestration interface. This file also referenced the removed LOTB
entry point, so it is not part of the active command surface.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def run(script: str, args: list[str]) -> int:
    """Run one historical script with the current Python interpreter."""
    return subprocess.call([sys.executable, str(SCRIPTS / script), *args])


def main() -> int:
    """Expose the historical command dispatcher."""
    parser = argparse.ArgumentParser(description="Historical LEONES dispatcher")
    parser.add_argument("command", choices=["hardware", "model", "infer", "lotb"])
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    mapping = {
        "hardware": "leones-hardware.py",
        "model": "leones-model.py",
        "infer": "leones-infer.py",
        "lotb": "leones-lotb.py",
    }
    return run(mapping[args.command], args.arguments)


if __name__ == "__main__":
    raise SystemExit(main())
