#!/usr/bin/env python3
"""🦁 LEONES · Task Intelligence v0.2.

Normaliza una necesidad humana en requisitos explícitos para el Router.
No elige modelos y no inventa benchmarks.
"""
from __future__ import annotations
import argparse, json, re

TASKS = {
    "chat": {"capabilities": ["conversation", "reasoning"], "quality": "general"},
    "coding": {"capabilities": ["code_generation", "code_reasoning", "tool_use"], "quality": "coding"},
    "rag": {"capabilities": ["long_context", "retrieval", "grounded_answer"], "quality": "knowledge"},
    "vision": {"capabilities": ["vision", "multimodal"], "quality": "multimodal"},
    "agent": {"capabilities": ["tool_use", "planning", "structured_output"], "quality": "agentic"},
}

def infer(text: str, kind: str | None):
    raw = (kind or "").strip().lower()
    t = text.lower()
    if raw in TASKS: return raw
    if any(x in t for x in ("código", "codigo", "programar", "python", "javascript", "web", "programación")): return "coding"
    if any(x in t for x in ("imagen", "foto", "visual", "multimodal")): return "vision"
    if any(x in t for x in ("rag", "documentos", "documentos", "buscar en", "base de conocimiento")): return "rag"
    if any(x in t for x in ("agente", "agent", "herramientas", "automatizar una tarea")): return "agent"
    return "chat"

def extract_constraints(text: str):
    t = text.lower()
    latency = None
    m = re.search(r"(?:menos de|<|máximo|max)\s*(\d+(?:[.,]\d+)?)\s*(?:s|seg|segundos)", t)
    if m: latency = float(m.group(1).replace(',', '.'))
    memory = None
    m = re.search(r"(?:menos de|<|máximo|max)\s*(\d+(?:[.,]\d+)?)\s*(?:gb|gib)\s*(?:de\s*)?(?:ram|memoria)?", t)
    if m: memory = float(m.group(1).replace(',', '.'))
    gpu = None
    if any(x in t for x in ("sin gpu", "cpu-only", "solo cpu", "sin gráfica")): gpu = False
    elif any(x in t for x in ("con gpu", "nvidia", "cuda", "gráfica")): gpu = True
    return {
        "local_only": True,
        "max_latency_seconds": latency,
        "max_memory_gb": memory,
        "requires_gpu": gpu,
        "privacy": "local_by_default",
    }

def normalize(text: str, kind: str | None = None):
    key = infer(text, kind)
    profile = TASKS[key]
    return {
        "task_intelligence_version": "0.2",
        "task": key,
        "request": text,
        "capabilities": profile["capabilities"],
        "quality_target": profile["quality"],
        "constraints": extract_constraints(text),
        "decision_status": "normalized",
        "next_step": "router",
    }

def main():
    p = argparse.ArgumentParser(description="LEONES Task Intelligence v0.2")
    p.add_argument("request", help="Necesidad o tarea del usuario")
    p.add_argument("--kind", choices=sorted(TASKS))
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    result = normalize(a.request, a.kind)
    if a.json: print(json.dumps(result, indent=2, ensure_ascii=False)); return
    print("🦁 LEONES · Task Intelligence v0.2")
    print(f"Tarea: {result['task']}")
    print(f"Capacidades: {', '.join(result['capabilities'])}")
    print(f"Restricciones: {json.dumps(result['constraints'], ensure_ascii=False)}")
    print("Siguiente paso: router")

if __name__ == "__main__": main()
