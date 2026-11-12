#!/usr/bin/env python3
"""Static audit for DSpine support embedded in llama.cpp's DFlash draft path."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git_value(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def read(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def audit(root: Path) -> dict:
    constants = read(root, "gguf-py/gguf/constants.py")
    mapping = read(root, "gguf-py/gguf/tensor_mapping.py")
    model = read(root, "src/models/dflash.cpp")
    converter = read(root, "conversion/qwen.py")
    speculative = read(root, "common/speculative.cpp")
    common_h = read(root, "common/common.h")

    checks = {
        "gguf_tensor_schema": all(
            marker in constants
            for marker in (
                "DSPINE_CODEBOOK", "DSPINE_GATE", "DSPINE_PRED_GATE",
                "DSPINE_PREV", "DSPINE_READ", "DSPINE_WRITE",
            )
        ),
        "hf_tensor_name_mapping": all(
            marker in mapping
            for marker in (
                "selected_prefix_bridge.codebook",
                "selected_prefix_bridge.gate",
                "selected_prefix_bridge.read",
                "selected_prefix_bridge.write",
            )
        ),
        "hf_checkpoint_conversion": all(
            marker in converter
            for marker in (
                "class DFlashModel", "_is_dspine", "_modify_dspine_tensors",
                "selected_prefix_code_bridge", "target_model_dir",
            )
        ),
        "model_loader": all(
            marker in model
            for marker in (
                "dspine_codebook", "dspine_gate", "dspine_pred_gate",
                "dspine_prev", "dspine_read", "dspine_write",
            )
        ),
        "dspine_graph": all(
            marker in model
            for marker in (
                "build_dspine_write", "build_dspine_lattice",
                "cur = build_dspine_write", "build_dspine_lattice(*this",
            )
        ),
        "speculative_runtime": all(
            marker in speculative
            for marker in (
                "common_speculative_impl_draft_dflash",
                "llama_get_embeddings_nextn",
                "is_dflash2",
            )
        ),
        "draft_dflash_dispatch": (
            "COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH" in common_h
            and '"draft-dflash"' in speculative
        ),
    }
    supported = all(checks.values())
    return {
        "repository": git_value(root, "remote", "get-url", "origin"),
        "commit": git_value(root, "rev-parse", "HEAD"),
        "branch": git_value(root, "branch", "--show-current"),
        "status": (
            "DSPINE_STATIC_INTEGRATION_FOUND_VIA_DRAFT_DFLASH"
            if supported else "INCOMPLETE_OR_UNCONFIRMED"
        ),
        "dispatch": "draft-dflash (DSpine GGUF is detected by its DSpine tensors/graph path)",
        "checks": checks,
        "interpretation": (
            "The source contains the GGUF schema, tensor mapping, model graph and speculative lattice path. "
            "This is static source evidence, not a successful build or runtime test."
            if supported else
            "One or more required DSpine source integration markers are missing; inspect the failed checks."
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
