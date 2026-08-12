#!/usr/bin/env python3
"""🦁 LEONES LOTB — batería mínima y reproducible de tareas agentivas.

OBJETIVO
========
LOTB responde una pregunta muy concreta: «¿esta pila local puede completar
pequeñas tareas reproducibles que se parecen a las que tendrá que resolver un
agente?». No pretende medir inteligencia general, seguridad, autonomía general
ni sustituir benchmarks especializados.

ANTES
=====
Necesitas un endpoint local compatible con la API de chat. El script NO instala
runtimes, NO descarga modelos, NO descubre hardware, NO mide tok/s y NO publica.
Si una prueba necesita una herramienta real, el agente debe disponer de ella.

DURANTE
=======
Cada tarea se ejecuta por separado. Se conserva la respuesta, el tiempo y una
evaluación automática cuando es posible. El estado `completed` solo significa
que hubo respuesta HTTP válida; el campo `evaluation` indica si la respuesta
superó el criterio mínimo de esa tarea.

DESPUÉS
=======
El resultado se puede guardar con `--output result.json` y pasar a
`leones-report.py`. Una tarea `pass` no demuestra capacidad general: demuestra
únicamente que el caso reproducible concreto superó su criterio.

FILOSOFÍA
=========
Es mejor declarar `tool_unavailable` o `manual_review` que convertir una
respuesta ambigua en un aprobado. LOTB debe producir evidencia conservadora.
"""
from __future__ import annotations
import argparse, json, re, time, urllib.error, urllib.request

TASKS = {
    "B01": {
        "name": "memoria/contexto",
        "prompt": "Recuerda exactamente este código: LEONES-B01-7429. Responde solo con ese código.",
        "kind": "exact",
        "expected": "LEONES-B01-7429",
    },
    "B02": {
        "name": "archivo",
        "prompt": "Si tienes una herramienta de archivos, crea un archivo temporal llamado leones_lotb_b02.txt con el texto LEONES-B02 y léelo de nuevo. Si no tienes herramienta de archivos, responde exactamente tool_unavailable.",
        "kind": "tool",
        "expected": "LEONES-B02",
    },
    "B03": {
        "name": "secuencia multietapa",
        "prompt": "Realiza estos pasos en orden: 1) escribe A; 2) transforma A en B; 3) transforma B en C. Devuelve únicamente A->B->C.",
        "kind": "exact",
        "expected": "A->B->C",
    },
    "B04": {
        "name": "recuperación ante error",
        "prompt": "Resuelve esta operación deliberadamente fallida: intenta dividir 10 entre 0, reconoce el error y después responde 10/2=5. Incluye el reconocimiento del error y el resultado final.",
        "kind": "contains",
        "expected": ["10/2", "5"],
    },
    "B05": {
        "name": "coding local",
        "prompt": "Escribe una función Python llamada add(a,b) que devuelva a+b y añade un ejemplo add(2,3)=5. No ejecutes código si no tienes herramienta de ejecución.",
        "kind": "contains",
        "expected": ["def add", "a+b", "5"],
    },
}

def call_agent(url: str, prompt: str, timeout: float) -> dict:
    payload = {"messages": [{"role": "user", "content": prompt}], "stream": False}
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            http_status = response.status
        elapsed = round(time.perf_counter() - started, 3)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw_response": raw}
        content = body.get("choices", [{}])[0].get("message", {}).get("content") if isinstance(body, dict) else None
        return {"status": "completed", "http_status": http_status, "elapsed_seconds": elapsed, "response": content if content is not None else body}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": "error", "elapsed_seconds": round(time.perf_counter() - started, 3), "error": str(exc)}

def evaluate(task: dict, result: dict) -> dict:
    if result.get("status") != "completed":
        return {"status": "not_evaluable", "reason": "no hubo respuesta válida del endpoint"}
    text = str(result.get("response", ""))
    if task["kind"] == "tool":
        if "tool_unavailable" in text.lower():
            return {"status": "tool_unavailable", "reason": "el agente declara no disponer de herramienta de archivos"}
        if task["expected"].lower() in text.lower() and "leones_lotb_b02.txt" in text:
            return {"status": "pass", "reason": "la respuesta contiene el artefacto y el contenido esperado; revisión manual recomendada"}
        return {"status": "manual_review", "reason": "la herramienta no puede verificarse solo desde el texto devuelto"}
    if task["kind"] == "exact":
        normalized = re.sub(r"\s+", "", text)
        expected = re.sub(r"\s+", "", task["expected"])
        return {"status": "pass" if expected in normalized else "fail", "expected": task["expected"]}
    missing = [x for x in task["expected"] if x.lower() not in text.lower()]
    return {"status": "pass" if not missing else "fail", "missing": missing}

def main() -> int:
    p = argparse.ArgumentParser(description="Ejecuta la batería mínima LOTB de LEONES")
    p.add_argument("--endpoint", required=True, help="URL local del endpoint de chat")
    p.add_argument("--task", choices=[*TASKS, "all"], default="all")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--output", help="Guarda el resultado estructurado en JSON")
    p.add_argument("--explain", action="store_true", help="Explica el propósito antes de ejecutar")
    a = p.parse_args()

    print("🦁 LEONES · LOTB")
    print("Pregunta: ¿puede esta pila local completar tareas pequeñas y reproducibles?")
    print("No es un benchmark de inteligencia general. No instala, descarga ni publica nada.")
    print("Un PASS solo acredita el caso concreto; no certifica capacidad general.\n")

    selected = TASKS if a.task == "all" else {a.task: TASKS[a.task]}
    results = {}
    for code, task in selected.items():
        print(f"[{code}] {task['name']} · ejecutando…", flush=True)
        result = call_agent(a.endpoint, task["prompt"], a.timeout)
        result["evaluation"] = evaluate(task, result)
        results[code] = result
        print(f"[{code}] endpoint={result['status']} · evaluación={result['evaluation']['status']} · {result['elapsed_seconds']} s", flush=True)

    evaluations = [v["evaluation"]["status"] for v in results.values()]
    passed = evaluations.count("pass")
    manual = evaluations.count("manual_review")
    unavailable = evaluations.count("tool_unavailable")
    failed = evaluations.count("fail")
    output = {
        "schema_version": "1.1",
        "tool": "leones-lotb",
        "tool_version": "1.2",
        "status": "completed" if results else "empty",
        "tasks": results,
        "summary": {
            "pass": passed,
            "fail": failed,
            "manual_review": manual,
            "tool_unavailable": unavailable,
            "total": len(results),
        },
        "next_step": "report" if results else "runtime",
    }
    text = json.dumps(output, indent=2, ensure_ascii=False)
    print("\nRESULTADO LOTB")
    print(text)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\nResultado guardado en: {a.output}")
        print("Siguiente paso: python3 scripts/leones-report.py --input " + a.output)
    return 0 if passed > 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
