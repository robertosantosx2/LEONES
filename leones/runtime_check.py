"""Check whether a llama.cpp CLI is available.

One responsibility: find the requested executable and print its version.
This script does not install llama.cpp, download models, or run inference.

Example:
    python -m leones.runtime_check
    python -m leones.runtime_check --executable llama-cli
"""

import argparse
import shutil
import subprocess


def check(executable: str) -> str:
    """Return the executable version or raise RuntimeError."""
    path = shutil.which(executable)
    if not path:
        raise RuntimeError(f"Runtime not found: {executable}")
    result = subprocess.run(
        [path, "--version"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip() or result.stderr.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Check llama.cpp availability.")
    parser.add_argument("--executable", default="llama-cli")
    args = parser.parse_args()
    print(check(args.executable))


if __name__ == "__main__":
    main()
