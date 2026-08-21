#!/usr/bin/env python3
"""Connect the selected LLMFit candidate to a real local runtime benchmark.

LLMFit remains the provider-aware preselector. Runtime-specific runners are
responsible for physical measurements; a result is marked measured only when
that runner actually generated tokens for the selected model.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from automation.discovery.llmfit_adapter import recommend, select_candidate


def run_bench(runtime: str, model: str | None = None) -> dict:
    if runtime == "airllm":
        if not model:
            raise RuntimeError("AirLLM requires a Hugging Face model identifier")
        proc = subprocess.run(
            ["python3", "scripts/leones_airllm_benchmark.py", model],
            check=False, capture_output=True, text=True,
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or f"AirLLM benchmark exited {proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("AirLLM benchmark did not return valid JSON") from exc

    if not shutil.which("llmfit"):
        raise RuntimeError("llmfit executable not found")
    args = ["llmfit", "bench", "--json", "--provider", runtime]
    if model and runtime in {"ollama", "vllm"}:
        args.append(model)
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"llmfit bench exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("llmfit bench did not return valid JSON") from exc


def _rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("models", "results", "benchmarks"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


def match_result(payload: dict, selected: dict) -> dict | None:
    names = {selected.get("model_id"), selected.get("ollama_name")}
    names.discard(None)
    if payload.get("status") == "measured" and payload.get("model") in names:
        return payload
    for row in _rows(payload):
        row_names = {row.get("name"), row.get("model"), row.get("model_id"),
                     row.get("ollama_name"), row.get("model_name")}
        if names & row_names:
            return row
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-case", default="general")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--target-tps", type=float, default=10.0)
    parser.add_argument("--max-context", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    envelope = recommend(use_case=args.use_case, limit=args.limit, max_context=args.max_context)
    selected = select_candidate(envelope, target_tps=args.target_tps,
                                require_installed=True, require_runtime=True)
    result = {
        "schema_version": "leones.runtime-benchmark.v1",
        "recommendation": envelope,
        "selected": selected,
        "benchmark": {"status": "not_run", "evidence_status": "unknown"},
    }
    if selected is None:
        result["benchmark"]["reason"] = (
            "No candidate is simultaneously runnable, installed and backed by an available runtime."
        )
    else:
        runtime = selected.get("runtime")
        model = selected.get("ollama_name") or selected.get("model_id")
        try:
            payload = run_bench(runtime, model)
            matched = match_result(payload, selected)
            if matched is None:
                result["benchmark"].update({
                    "status": "no_matching_result",
                    "evidence_status": "unknown",
                    "raw": payload,
                })
            else:
                measured_tps = matched.get("tokens_per_second", matched.get("tok_s"))
                result["benchmark"].update({
                    "status": "measured",
                    "evidence_status": "measured",
                    "runtime": runtime,
                    "model": model,
                    "measured_tps": measured_tps,
                    "result": matched,
                })
        except RuntimeError as exc:
            result["benchmark"].update({
                "status": "failed",
                "evidence_status": "unknown",
                "error": str(exc),
            })

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["benchmark"]["status"] in {"measured", "not_run", "no_matching_result"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
