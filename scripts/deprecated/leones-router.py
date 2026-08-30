#!/usr/bin/env python3
"""Historical LEONES heuristic router retained for provenance.

RC1 does not use this parallel recommendation path. Selection and runtime
authorization now have explicit boundaries in the minimal pipeline.
"""

from __future__ import annotations
import argparse, json, sys

SAFETY_FACTOR = 1.35


def load_json(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def route(hw, model, task=None, atlas=None, evidence=None):
    h, m = hw.get("hardware", {}), model.get("model", {})
    ram, size = h.get("ram_gb"), m.get("size_bytes")
    fmt = (m.get("format") or "").lower()
    required = None if size is None else size / 1024**3 * SAFETY_FACTOR
    fits = None if ram is None or required is None else required <= ram
    task_name = (task or {}).get("task")
    capabilities = set((task or {}).get("capabilities", []))
    records = (atlas or {}).get("records", [])
    evidence = evidence or {}
    candidates = []
    for r in records:
        if r.get("kind") != "model":
            continue
        score = 0
        if r.get("name") == m.get("name"):
            score += 5
        execution = r.get("execution") or {}
        if fmt and execution.get("format") == m.get("format"):
            score += 2
        if r.get("evaluation"):
            score += 1
        ev = r.get("evidence") or {}
        if ev.get("state") in ("reproducible", "verified"):
            score += 2
        candidates.append((score, r))
    candidates.sort(key=lambda x: x[0], reverse=True)
    evidence_matches = [r for _, r in candidates if r.get("name") == m.get("name")]
    primary = evidence.get("evidence", {})
    agentic = evidence.get("agentic", {})
    outcome = agentic.get("outcome", {})
    measured = primary.get("evidence_type") in ("measured", "verified")
    evidence_model = (evidence.get("model") or {}).get("name")
    evidence_runtime = (agentic.get("runtime") or {}).get("name")
    runtime_benchmark = evidence.get("runtime_benchmark") or {}
    benchmark_measured = runtime_benchmark.get("status") == "measured"
    runtime = evidence_runtime if measured and evidence_runtime else (
        "llama.cpp" if fmt == "gguf" else None
    )
    evidence_matches_model = (
        measured and evidence_model and evidence_model == m.get("name")
    )
    evidence_runtime_match = bool(
        evidence_matches_model and evidence_runtime and evidence_runtime == runtime
    )
    decision = "candidate" if fits is not False else "reject_memory"
    if task_name == "vision" and "vision" not in capabilities:
        decision = "insufficient_task_capability"
    if evidence_matches_model and outcome.get("status") == "success":
        decision = "evidence_supported" if decision == "candidate" else decision
    elif evidence_matches_model and outcome.get("status") in ("failed", "error"):
        decision = "evidence_failed"
    reason = "Heurística histórica basada en memoria, formato, tarea y evidencia."
    return {
        "router_version": "0.5",
        "decision_type": "heuristic_with_primary_evidence",
        "decision": decision,
        "task": {"name": task_name, "capabilities": sorted(capabilities)},
        "hardware": {
            "ram_gb": ram,
            "gpu": h.get("gpu"),
            "vram_gb": h.get("vram_gb"),
            "os": h.get("os"),
        },
        "model": {
            "name": m.get("name"),
            "format": m.get("format"),
            "size_bytes": size,
            "sha256": m.get("sha256"),
        },
        "atlas": {
            "records_available": len(records),
            "matching_records": len(evidence_matches),
        },
        "runtime": runtime,
        "primary_evidence": {
            "present": bool(primary),
            "type": primary.get("evidence_type"),
            "model_match": bool(evidence_matches_model),
            "runtime_match": evidence_runtime_match,
            "runtime_benchmark_measured": benchmark_measured,
        },
        "memory_check": {
            "safety_factor": SAFETY_FACTOR,
            "estimated_required_ram_gb": round(required, 2)
            if required is not None else None,
            "fits_heuristically": fits,
        },
        "reason": reason,
    }


def main():
    p = argparse.ArgumentParser(description="Historical LEONES router")
    p.add_argument("--hardware", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--task")
    p.add_argument("--atlas")
    p.add_argument("--evidence")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    try:
        result = route(
            load_json(a.hardware), load_json(a.model),
            load_json(a.task) if a.task else {},
            load_json(a.atlas) if a.atlas else {},
            load_json(a.evidence) if a.evidence else {},
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: no se pudieron leer las entradas JSON: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if a.json else result["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
