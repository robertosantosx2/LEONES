#!/usr/bin/env python3
"""🦁 LEONES · Task Intelligence v0.1.

Normaliza una necesidad humana en requisitos que el Router pueda usar.
No elige modelos por sí mismo y no inventa benchmarks.
"""
from __future__ import annotations
import argparse, json

TASKS = {
    "chat": {"capabilities": ["conversation", "reasoning"], "quality": "general"},
    "coding": {"capabilities": ["code_generation", "code_reasoning", "tool_use"], "quality": "coding"},
    "rag": {"capabilities": ["long_context", "retrieval", "grounded_answer"], "quality": "knowledge"},
    "vision": {"capabilities": ["vision", "multimodal"], "quality": "multimodal"},
    "agent": {"capabilities": ["tool_use", "planning", "structured_output"], "quality": "agentic"},
}

def normalize(text: str, kind: str | None = None):
    raw = (kind or text or "chat").strip().lower()
    key = raw if raw in TASKS else "chat"
    profile = TASKS[key]
    return {
        "task_intelligence_version": "0.1",
        "task": key,
        "request": text,
        "capabilities": profile["capabilities"],
        "quality_target": profile["quality"],
        "constraints": {
            "local_only": True,
            "max_latency_seconds": None,
            "max_memory_gb": None,
            "requires_gpu": None,
            "privacy": "local_by_default",
        },
        "decision_status": "normalized",
        "next_step": "router",
    }

def main():
    p = argparse.ArgumentParser(description="LEONES Task Intelligence v0.1")
    p.add_argument("request", help="Necesidad o tarea del usuario")
    p.add_argument("--kind", choices=sorted(TASKS))
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    result = normalize(a.request, a.kind)
    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("🦁 LEONES · Task Intelligence v0.1")
        print(f"Tarea: {result['task']}")
        print(f"Capacidades: {', '.join(result['capabilities'])}")
        print("Siguiente paso: router")

if __name__ == "__main__":
    main()
