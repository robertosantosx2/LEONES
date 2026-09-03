#!/usr/bin/env python3
"""Trusted llama.cpp A01 launcher for GGUF Hugging Face model references.

The A01 executor supplies the prompt as the final argv element. This wrapper
therefore keeps the prompt positional and never invokes a shell. llama.cpp is
responsible for resolving/downloading the Hugging Face artifact when ``-hf``
is used.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess


def find_llama_cli() -> list[str]:
    binary = shutil.which("llama-cli")
    if binary:
        return [binary]
    llama = shutil.which("llama")
    if llama:
        return [llama, "cli"]
    raise RuntimeError("llama.cpp CLI not found: expected llama-cli or llama")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-ref", required=True, help="HF model ref, e.g. repo:Q4_1")
    parser.add_argument("prompt")
    parser.add_argument("--predict", type=int, default=256)
    args = parser.parse_args(argv)
    if not args.model_ref.startswith("hf://") or ":" not in args.model_ref[5:]:
        raise SystemExit("--model-ref must be hf://repo:quantization")
    hf_ref = args.model_ref[5:]
    command = [
        *find_llama_cli(),
        "-hf", hf_ref,
        "-p", args.prompt,
        "-n", str(args.predict),
        "--no-display-prompt",
    ]
    completed = subprocess.run(command, check=False, shell=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
