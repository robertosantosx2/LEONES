#!/usr/bin/env python3
"""RC4 explicit model-installation boundary.

A model is installed only after the TUI obtains explicit user consent. This
script performs no recommendation and no measurement; it only materializes a
selected Hugging Face model into the LEONES local-model directory.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "models"
MODEL_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def install(model_id: str, output_dir: Path) -> int:
    if not MODEL_RE.fullmatch(model_id):
        print(f"ERROR: model_id no válido para Hugging Face: {model_id}", file=sys.stderr)
        return 2
    if shutil.which("hf") is None:
        print("ERROR: no se encontró 'hf' en PATH. Instala huggingface_hub/hf antes de continuar.", file=sys.stderr)
        return 3
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / model_id.replace("/", "--")
    target.mkdir(parents=True, exist_ok=True)
    command = ["hf", "download", model_id, "--local-dir", str(target)]
    print(f"MODEL={model_id}", flush=True)
    print(f"TARGET={target}", flush=True)
    print("PHASE=downloading", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode == 0:
        print("PHASE=completed", flush=True)
    else:
        print("PHASE=failed", flush=True)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RC4 install selected Hugging Face model")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args(argv)
    return install(args.model_id, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
