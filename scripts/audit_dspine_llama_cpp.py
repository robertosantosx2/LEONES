#!/usr/bin/env python3
"""Static capability gate for the DSpine llama.cpp fork; stdlib only."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def git_value(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def audit(root: Path) -> dict:
    common_h = root / "common/common.h"
    speculative_cpp = root / "common/speculative.cpp"
    if not common_h.is_file() or not speculative_cpp.is_file():
        raise FileNotFoundError("expected common/common.h and common/speculative.cpp")

    enum_text = common_h.read_text(encoding="utf-8", errors="replace")
    impl_text = speculative_cpp.read_text(encoding="utf-8", errors="replace")

    source_files = list(root.rglob("*.cpp")) + list(root.rglob("*.h")) + list(root.rglob("*.cu")) + list(root.rglob("*.cuh"))
    bridge_support = any(
        "selected_prefix_bridge" in p.read_text(encoding="utf-8", errors="replace")
        or "DSpineCodeBridge" in p.read_text(encoding="utf-8", errors="replace")
        for p in source_files
    )
    checks = {
        "algorithm_enum": bool(re.search(r"COMMON_SPECULATIVE_TYPE_DSPINE", enum_text)),
        "algorithm_name": bool(re.search(r'\{\s*"draft-dspine"\s*,', impl_text)),
        "runtime_implementation": bool(
            re.search(r"common_speculative_impl_draft_dspine", impl_text)
        ),
        "code_bridge_support": bridge_support,
    }
    implemented = all(checks.values())
    return {
        "repository": git_value(root, "remote", "get-url", "origin"),
        "commit": git_value(root, "rev-parse", "HEAD"),
        "branch": git_value(root, "branch", "--show-current"),
        "status": "IMPLEMENTATION_MARKERS_PRESENT" if implemented else "NOT_IMPLEMENTED",
        "checks": checks,
        "interpretation": (
            "Static markers are present; this is not proof of numerical correctness."
            if implemented
            else "DSpine is not registered as a distinct speculative algorithm in this source tree."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="path to a llama.cpp checkout")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    result = audit(args.source.resolve())
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
