#!/usr/bin/env python3
"""Run a minimal llama.cpp test and emit normalized JSON.

The adapter is intentionally thin: llama.cpp remains an external local runtime.
No model is downloaded and no LEONES infrastructure is imported.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "0.1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LEONES llama.cpp local smoke test")
    parser.add_argument("--model", required=True, help="Path to a local GGUF model")
    parser.add_argument("--prompt", default="Say hello in one short sentence.")
    parser.add_argument("--new-tokens", type=int, default=32)
    parser.add_argument("--context", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--llama-cli", default="llama-cli", help="llama.cpp CLI executable")
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def first_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return float(match.group(1)) if match else None


def first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return int(match.group(1)) if match else None


def parse_timing(stdout: str, stderr: str) -> dict[str, float | int | None]:
    """Extract only explicit llama.cpp timing counters when present.

    Output formats can change between llama.cpp releases, so unknown values
    remain null rather than being inferred from unrelated timings.
    """

    text = f"{stdout}\n{stderr}"
    prompt_tokens = first_int(r"prompt\s+(?:eval|tokens?)\s*[:=]\s*(\d+)", text)
    generated_tokens = first_int(r"(?:generated|predicted|sampled)\s+(?:tokens?)\s*[:=]\s*(\d+)", text)
    generation_ms = first_float(r"(?:eval|generation)\s+time\s*[:=]\s*([0-9.]+)\s*ms", text)
    tokens_per_second = first_float(r"(?:tokens?/s|t/s|tokens per second)\s*[:=]\s*([0-9.]+)", text)
    ttft_ms = first_float(r"(?:ttft|time to first token)\s*[:=]\s*([0-9.]+)\s*ms", text)

    return {
        "prompt_tokens": prompt_tokens,
        "generated_tokens": generated_tokens,
        "generation_ms": generation_ms,
        "tokens_per_second": tokens_per_second,
        "ttft_ms": ttft_ms,
    }


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    model = Path(args.model).expanduser().resolve()
    executable = shutil.which(args.llama_cli)

    result = {
        "schema_version": SCHEMA_VERSION,
        "test": {"name": "llm-smoke-test", "mode": "experimental"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": {
            "id": model.name,
            "revision": None,
            "parameter_count": None,
            "quantization": "GGUF" if model.suffix.lower() == ".gguf" else None,
            "context_length": args.context,
        },
        "runtime": {
            "name": "llama.cpp",
            "version": None,
            "adapter": "llama-cpp",
        },
        "hardware": {
            "os": platform.platform(),
            "architecture": platform.machine(),
            "cpu": platform.processor() or None,
            "ram_bytes": None,
            "gpu": None,
            "vram_bytes": None,
        },
        "configuration": {
            "prompt_tokens": None,
            "requested_new_tokens": args.new_tokens,
            "temperature": None,
            "seed": args.seed,
            "batch_size": None,
            "context_tokens": args.context,
        },
        "warmup": {"enabled": False, "runs": 0},
        "repetitions": 1,
        "metrics": {
            "ttft_ms": None,
            "generation_ms": None,
            "total_ms": None,
            "prompt_tokens": None,
            "generated_tokens": None,
            "tokens_per_second": None,
            "peak_ram_bytes": None,
            "peak_vram_bytes": None,
        },
        "result": {"status": "error", "error": None},
    }

    if executable is None:
        result["result"]["error"] = f"Runtime not found: {args.llama_cli}"
    elif not model.is_file():
        result["result"]["error"] = f"Model file not found: {model}"
    else:
        command = [
            executable,
            "-m",
            str(model),
            "-p",
            args.prompt,
            "-n",
            str(args.new_tokens),
            "-c",
            str(args.context),
        ]
        if args.seed is not None:
            command.extend(["-s", str(args.seed)])

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            timing = parse_timing(completed.stdout, completed.stderr)
            result["metrics"]["total_ms"] = round(elapsed_ms, 3)
            for key in (
                "ttft_ms",
                "generation_ms",
                "prompt_tokens",
                "generated_tokens",
                "tokens_per_second",
            ):
                result["metrics"][key] = timing[key]

            result["configuration"]["prompt_tokens"] = timing["prompt_tokens"]
            result["result"]["status"] = "ok" if completed.returncode == 0 else "error"
            if completed.returncode != 0:
                result["result"]["error"] = completed.stderr.strip() or f"llama.cpp exited with {completed.returncode}"
        except OSError as exc:
            result["result"]["error"] = str(exc)

    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

    return 0 if result["result"]["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
