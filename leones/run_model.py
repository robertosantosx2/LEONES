"""Run one already-prepared local model with llama.cpp.

One responsibility: execute an explicit model path and prompt through
`llama-cli`. It does not download, select, prepare, quantize or benchmark.

Example:
    python -m leones.run_model models/model.gguf "Explain recursion simply"
"""

import argparse
import subprocess
from pathlib import Path

from .runtime_check import check


def run(model: Path, prompt: str, executable: str = "llama-cli", max_tokens: int = 128) -> str:
    """Run one prompt against one local model and return its output."""
    if not model.is_file():
        raise ValueError(f"Model file does not exist: {model}")
    check(executable)
    result = subprocess.run(
        [executable, "-m", str(model), "-p", prompt, "-n", str(max_tokens)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one local model with llama.cpp.")
    parser.add_argument("model")
    parser.add_argument("prompt")
    parser.add_argument("--executable", default="llama-cli")
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()
    print(run(Path(args.model), args.prompt, args.executable, args.max_tokens), end="")


if __name__ == "__main__":
    main()
