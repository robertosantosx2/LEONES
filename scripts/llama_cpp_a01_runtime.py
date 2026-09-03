#!/usr/bin/env python3
"""Trusted llama.cpp A01 launcher for GGUF Hugging Face model references.

The A01 executor supplies the prompt as the final argv element. This wrapper
therefore keeps the prompt positional and never invokes a shell. llama.cpp is
responsible for resolving/downloading the Hugging Face artifact when ``-hf``
is used.

A bounded context is part of the trusted launcher contract: llama.cpp otherwise
uses the model's native context, which can be physically impossible on a
workstation even when the quantized model itself fits in RAM. The default of
2048 is the validated workstation-safe A01 baseline; callers may override it
explicitly with ``--context``.

Conversation mode is disabled because A01 consumes structured model output
from a single completion. Interactive chat mode can otherwise keep the process
open after generation and contaminate the runner's completion contract.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess


DEFAULT_CONTEXT_TOKENS = 2048


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
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT_TOKENS,
                        help=f"maximum context tokens (default: {DEFAULT_CONTEXT_TOKENS})")
    parser.add_argument("--threads", type=int, default=None,
                        help="llama.cpp CPU threads; omit to use its runtime default")
    parser.add_argument("prompt")
    parser.add_argument("--predict", type=int, default=256)
    args = parser.parse_args(argv)
    if not args.model_ref.startswith("hf://") or ":" not in args.model_ref[5:]:
        raise SystemExit("--model-ref must be hf://repo:quantization")
    if args.context < 1:
        raise SystemExit("--context must be positive")
    if args.threads is not None and args.threads < 1:
        raise SystemExit("--threads must be positive")
    if args.predict < 1:
        raise SystemExit("--predict must be positive")
    hf_ref = args.model_ref[5:]
    command = [
        *find_llama_cli(),
        "-hf", hf_ref,
        "-c", str(args.context),
        "-p", args.prompt,
        "-n", str(args.predict),
        "--no-display-prompt",
        "-no-cnv",
    ]
    if args.threads is not None:
        command.extend(["-t", str(args.threads)])
    completed = subprocess.run(command, check=False, shell=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
