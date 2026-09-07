#!/usr/bin/env python3
"""RC4 measured chain — human selection → stack → runtime → A01 → MEASURED.

ESTIMATED recommendations never auto-execute. MEASURED requires physical run
with --execute + --authorize-execution + --authorize-measurement.
Hermes/OMH are not selectors. Runtime argv is trusted only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "leones.rc4.measured_chain.v1"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_recommendation(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_ids(recommendation: dict[str, Any] | None) -> list[str]:
    if not recommendation:
        return []
    ids: list[str] = []
    for row in recommendation.get("recommendations") or []:
        mid = row.get("model_id") or row.get("id") or row.get("name")
        if mid and str(mid) not in ids:
            ids.append(str(mid))
    return ids


def choose_interactive(candidates: list[str]) -> tuple[str, str]:
    print("\nRC4 · SELECCIÓN HUMANA (ESTIMATED ≠ MEASURED)")
    if candidates:
        for i, mid in enumerate(candidates, 1):
            print(f"  [{i}] {mid}")
        print("  [0] model_id manual")
        while True:
            ans = input("LEONES> ").strip()
            if ans == "0":
                mid = input("model_id> ").strip()
                if mid:
                    break
            try:
                n = int(ans)
                if 1 <= n <= len(candidates):
                    mid = candidates[n - 1]
                    break
            except ValueError:
                pass
            print("  ! inválido")
    else:
        mid = input("model_id> ").strip()
        if not mid:
            raise SystemExit("RC4 MEASURED CHAIN: model_id required")
    print("\nRC4 · STACK  [1] magnitude  [2] ods  [3] none")
    while True:
        ans = input("LEONES> ").strip()
        if ans in {"1", "magnitude"}:
            return mid, "magnitude"
        if ans in {"2", "ods"}:
            return mid, "ods"
        if ans in {"3", "none"}:
            return mid, "none"
        print("  ! elige 1/2/3")


def runtime_preflight(model_id: str) -> dict[str, Any]:
    try:
        from scripts.a01_runtime_preflight import check_ollama_model
    except Exception as exc:  # noqa: BLE001
        return {
            "runtime": "unknown",
            "available": False,
            "model_id": model_id,
            "model_available": False,
            "reason": f"import_error:{exc}",
            "installed_models": [],
        }
    pf = check_ollama_model(model_id)
    return {
        "runtime": pf.runtime,
        "available": pf.available,
        "model_id": pf.model_id,
        "model_available": pf.model_available,
        "reason": pf.reason,
        "installed_models": list(pf.installed_models),
    }


def try_execute_a01(model_id: str, prompt: str, workspace: Path) -> dict[str, Any]:
    try:
        from scripts.a01_runtime_preflight import check_ollama_model
        from scripts.run_a01_selected import run_selected
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"import:{exc}"}
    pf = check_ollama_model(model_id)
    if not pf.available or not pf.model_available:
        return {
            "ok": False,
            "error": "runtime_or_model_unavailable",
            "preflight": {
                "available": pf.available,
                "model_available": pf.model_available,
                "reason": pf.reason,
            },
        }
    selection = {
        "schema": "leones.runtime-selection.v1",
        "model_id": model_id,
        "model": {"id": model_id, "name": model_id},
        "runtime": "ollama",
    }
    runtime_commands = {model_id: ["ollama", "run", model_id]}
    try:
        result = run_selected(
            selection,
            runtime_commands=runtime_commands,
            workspace=workspace,
            prompt=prompt,
            output_path=str(workspace / "report.txt"),
            timeout_seconds=120.0,
        )
        return {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def build_envelope(
    *,
    model_id: str,
    stack: str,
    recommendation_path: str | None,
    runtime: dict[str, Any],
    execute: bool,
    authorize_execution: bool,
    authorize_measurement: bool,
    execution_result: dict[str, Any] | None,
) -> dict[str, Any]:
    measured = bool(
        execute
        and authorize_execution
        and authorize_measurement
        and execution_result
        and execution_result.get("ok") is True
    )
    return {
        "schema": SCHEMA,
        "observed_at_utc": _utc(),
        "chain": [
            "human_selection",
            "stack",
            "runtime_preflight",
            "execution_authorization",
            "measurement",
            "evidence",
        ],
        "human_selection": {
            "model_id": model_id,
            "kind": "DECLARED",
            "source_recommendation": recommendation_path,
        },
        "stack": {"choice": stack, "kind": "DECLARED"},
        "runtime_preflight": {**runtime, "kind": "OBSERVED"},
        "execution_authorized": bool(authorize_execution and execute),
        "measurement_authorized": bool(authorize_measurement and execute),
        "measured": measured,
        "execution_result": execution_result,
        "rules": {
            "estimated_not_measured": True,
            "no_auto_execute_from_recommendation": True,
            "hermes_omh_not_selectors": True,
            "physical_host_required_for_measured": True,
        },
        "next_gate": (
            "none"
            if measured
            else (
                "provide --execute --authorize-execution --authorize-measurement "
                "on a physical host with runtime+model available"
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recommendation", type=Path)
    p.add_argument("--model-id")
    p.add_argument("--stack", choices=["magnitude", "ods", "none"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--authorize-execution", action="store_true")
    p.add_argument("--authorize-measurement", action="store_true")
    p.add_argument("--prompt", default="Responde en una frase: ¿qué es LEONES?")
    p.add_argument(
        "--workspace",
        type=Path,
        default=ROOT / "results" / "physical-rc4-measured",
    )
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)

    rec = load_recommendation(args.recommendation)
    candidates = candidate_ids(rec)
    if args.model_id and args.stack:
        model_id, stack = args.model_id, args.stack
    elif args.model_id:
        model_id, stack = args.model_id, "none"
    else:
        model_id, stack = choose_interactive(candidates)

    runtime = runtime_preflight(model_id)
    execution_result = None
    if args.execute:
        if not (args.authorize_execution and args.authorize_measurement):
            print(
                "RC4 MEASURED CHAIN: --execute requires "
                "--authorize-execution and --authorize-measurement",
                file=sys.stderr,
            )
            return 2
        args.workspace.mkdir(parents=True, exist_ok=True)
        execution_result = try_execute_a01(model_id, args.prompt, args.workspace)

    envelope = build_envelope(
        model_id=model_id,
        stack=stack,
        recommendation_path=str(args.recommendation) if args.recommendation else None,
        runtime=runtime,
        execute=args.execute,
        authorize_execution=args.authorize_execution,
        authorize_measurement=args.authorize_measurement,
        execution_result=execution_result,
    )
    text = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    if args.json or args.out:
        print(text, end="")
    else:
        print(
            f"RC4 MEASURED CHAIN  model={model_id} stack={stack} "
            f"measured={envelope['measured']}"
        )
        if not envelope["measured"]:
            print("next_gate:", envelope["next_gate"])
    if args.execute and not envelope["measured"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
