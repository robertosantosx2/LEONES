#!/usr/bin/env python3
"""Promote a measured runtime benchmark into LEONES evidence without conflating estimates."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path


def hardware_fingerprint() -> str:
    raw = "|".join((platform.system(), platform.machine(), platform.processor(), platform.release()))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def promote(payload: dict) -> dict:
    benchmark = payload.get("benchmark", payload)
    status = benchmark.get("evidence_status", benchmark.get("status", "unknown"))
    measured = status == "measured"
    result = benchmark.get("result", benchmark)
    model = benchmark.get("model") or result.get("model")
    runtime = benchmark.get("runtime") or result.get("runtime")
    output = {
        "schema_version": "leones.runtime-benchmark.v1",
        "evidence_status": "measured" if measured else ("failed" if status == "failed" else "unknown"),
        "runtime": runtime or "unknown",
        "model": model or "unknown",
        "quantization": (payload.get("selected") or {}).get("best_quant"),
        "hardware_fingerprint": hardware_fingerprint(),
        "observed_at": result.get("observed_at") or datetime.now(timezone.utc).isoformat(),
        "tokens_per_second": result.get("tokens_per_second", benchmark.get("measured_tps")),
        "prompt_tokens": result.get("prompt_tokens"),
        "generated_tokens": result.get("generated_tokens"),
        "generation_seconds": result.get("generation_seconds"),
        "load_seconds": result.get("load_seconds"),
        "measurement_scope": result.get("measurement_scope", "local runtime benchmark"),
        "source": "LEONES",
        "provenance": {
            "input_schema": payload.get("schema_version"),
            "llmfit_estimate": (payload.get("selected") or {}).get("estimated_tps"),
            "promotion_rule": "only a matching physical generation may become measured"
        }
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    output = promote(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
