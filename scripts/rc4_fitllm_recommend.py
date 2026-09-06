#!/usr/bin/env python3
"""RC4 — FitLLM/LLMFit optional model recommender.

FitLLM proposes exactly three ESTIMATED candidates. It never authorizes
execution or MEASURED results. LEONES starts without FitLLM; a missing binary
only degrades this recommendation step.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_selection import llmfit as llmfit_mod  # noqa: E402


SCHEMA = "leones.rc4.fitllm_recommendation.v1"
CANDIDATE_COUNT = 3


def recommend(
    *,
    use_case: str | None = None,
    max_context: int | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Return exactly three proposals when FitLLM can supply three.

    This envelope is proposal-only: execution and measurement remain false.
    """
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "phase": "RC4",
        "provider": "fitllm_llmfit",
        "kind": "ESTIMATED",
        "candidate_count": CANDIDATE_COUNT,
        "execution_authorized": False,
        "measurement_authorized": False,
        "measured": False,
        "user_choice_required": True,
        "fitllm_required_for_boot": False,
        "recommendations": [],
        "status": "ok",
        "message": None,
    }

    if llmfit_mod.executable() is None:
        base["status"] = "unavailable"
        base["candidate_count"] = 0
        base["message"] = (
            "FitLLM/LLMFit no está en PATH. LEONES puede continuar: "
            "elige el modelo a mano. La preselección automática queda omitida."
        )
        return base

    try:
        result = llmfit_mod.run_recommend(
            limit=CANDIDATE_COUNT,
            use_case=use_case,
            max_context=max_context,
            timeout_seconds=timeout_seconds,
        )
    except llmfit_mod.LLMFitError as exc:
        base["status"] = "error"
        base["candidate_count"] = 0
        base["message"] = f"FitLLM falló en preselección: {exc}"
        return base

    models: Sequence[Mapping[str, Any]] = result.models
    rows = []
    for item in models:
        if not isinstance(item, Mapping):
            continue
        model_id = item.get("id") or item.get("model") or item.get("name")
        if not model_id:
            continue
        rows.append({
            "model_id": model_id,
            "raw": dict(item),
            "kind": "ESTIMATED",
        })
        if len(rows) == CANDIDATE_COUNT:
            break

    base["recommendations"] = rows
    base["candidate_count"] = len(rows)
    base["provider_version"] = result.version
    base["command"] = list(result.command)

    if len(rows) != CANDIDATE_COUNT:
        base["status"] = "insufficient"
        base["message"] = (
            f"FitLLM no proporcionó {CANDIDATE_COUNT} candidatos válidos "
            f"({len(rows)} disponibles); no se fabrica una tercera opción."
        )
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RC4 FitLLM optional recommender")
    parser.add_argument("--use-case", default=None)
    parser.add_argument("--max-context", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args(argv)

    envelope = recommend(
        use_case=args.use_case,
        max_context=args.max_context,
    )
    if args.json:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return 0 if envelope["status"] in {"ok", "unavailable"} else 1

    print(f"RC4 FitLLM recommendation: {envelope['status']}")
    print(f"  candidates: {envelope['candidate_count']}/{CANDIDATE_COUNT}")
    print(f"  kind: {envelope['kind']}  execution_authorized: {envelope['execution_authorized']}")
    if envelope.get("message"):
        print(f"  {envelope['message']}")
    for i, row in enumerate(envelope.get("recommendations") or [], 1):
        print(f"  [{i}] {row.get('model_id')}")
    if envelope["status"] == "unavailable":
        return 0
    return 0 if envelope["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
