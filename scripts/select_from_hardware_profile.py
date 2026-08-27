#!/usr/bin/env python3
"""Run the canonical model selector from an observed LEONES hardware profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.model_selector import DEFAULT_FEED, select


def available_memory_gb(profile: dict) -> float:
    available = profile.get("memory", {}).get("available_bytes")
    total = profile.get("memory", {}).get("total_bytes")
    value = available if available is not None else total
    if value is None:
        raise ValueError("hardware profile contains no memory measurement")
    return float(value) / (1024 ** 3)


def hardware_label(profile: dict) -> str:
    model = profile.get("cpu", {}).get("model") or "unknown-cpu"
    return str(model)


def select_from_profile(profile: dict, rows: list[dict[str, str]], *, workload: str,
                        required_runtime: str, context_tokens: int = 4096, top_n: int = 10,
                        llmfit: dict | None = None) -> dict:
    memory_gb = available_memory_gb(profile)
    # The profile reports currently available RAM, not installed capacity. This
    # conservative value prevents selection based on memory that is not usable
    # at selection time. GPU VRAM is not guessed from lspci text.
    return select(rows, workload=workload, hardware=hardware_label(profile),
                  ram_gb=memory_gb, vram_gb=0, context_tokens=context_tokens,
                  top_n=top_n, llmfit=llmfit, required_runtime=required_runtime)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--llmfit", type=Path)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    rows = list(__import__("csv").DictReader(args.feed.open(encoding="utf-8-sig", newline="")))
    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8")) if args.llmfit else None
    result = select_from_profile(profile, rows, workload=args.workload, required_runtime=args.runtime,
                                  context_tokens=args.context, top_n=args.top_n, llmfit=llmfit)
    result["hardware_profile"] = {
        "cpu_model": profile.get("cpu", {}).get("model"),
        "available_memory_gb": available_memory_gb(profile),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"eligible={result['counts']['eligible']} top_n={result['counts']['top_n']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
