#!/usr/bin/env python3
"""🦁 LEONES LOTB — mínima batería funcional de tareas agentivas.

ANTES
-----
Este script responde una pregunta concreta: «¿el agente local puede completar
cinco tareas reproducibles, no solo generar texto?». Necesita un endpoint local
compatible con la API de chat. NO descubre hardware, NO mide tok/s y NO publica.

DURANTE
-------
Cada tarea se envía por separado y se registra tiempo, respuesta y estado. Las
pruebas son deliberadamente pequeñas para que el usuario pueda repetirlas.

DESPUÉS
-------
El JSON permite continuar con `leones-report.py`. Un `completed` significa que
el endpoint respondió; no significa que la tarea haya sido validada por una
persona ni que el agente sea seguro o generalmente capaz.

Los cinco casos son mínimos: memoria/contexto, archivos, secuencia multietapa,
recuperación ante error y coding local. Las tareas que requieren herramientas
reales deben ejecutarse contra un agente que tenga esas herramientas habilitadas.
"""
from __future__ import annotations
import argparse, json, time, urllib.error, urllib.request

TASKS = {
    "B01": "Recuerda exactamente este código: LEONES-B01-7429. Responde solo con ese código.",
    "B02": "Si tienes una herramienta de archivos, crea un archivo temporal llamado leones_lotb_b02.txt con el texto LEONES-B02 y léelo de nuevo. Si no tienes herramienta de archivos, indica claramente tool_unavailable.",
    "B03": "Realiza estos pasos en orden: 1) escribe A; 2) transforma A en B; 3) transforma B en C. Devuelve únicamente A->B->C.",
    "B04": "Resuelve esta operación deliberadamente fallida: intenta dividir 10 entre 0, reconoce el error y después responde 10/2=5. Devuelve ambas partes.",
    "B05": "Escribe una función Python llamada add(a,b) que devuelva a+b y añade un ejemplo add(2,3)=5. No ejecutes código si no tienes herramienta de ejecución.",
}

def call_agent(url: str, prompt: str, timeout: float) -> dict:
    payload={"messages":[{"role":"user","content":prompt}],"stream":False}
    request=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(request,timeout=timeout) as response:
            raw=response.read().decode("utf-8",errors="replace")
        elapsed=round(time.perf_counter()-started,3)
        try: body=json.loads(raw)
        except json.JSONDecodeError: body={"raw_response":raw}
        content=body.get("choices",[{}])[0].get("message",{}).get("content") if isinstance(body,dict) else None
        return {"status":"completed","elapsed_seconds":elapsed,"response":content if content is not None else body}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status":"error","elapsed_seconds":round(time.perf_counter()-started,3),"error":str(exc)}

def main()->int:
    p=argparse.ArgumentParser(description="Ejecuta la batería mínima LOTB de LEONES")
    p.add_argument("--endpoint",required=True,help="URL local del endpoint de chat")
    p.add_argument("--task",choices=[*TASKS,"all"],default="all")
    p.add_argument("--timeout",type=float,default=120.0)
    p.add_argument("--explain",action="store_true",help="Explica el propósito antes de ejecutar")
    a=p.parse_args()
    if a.explain or True:
        print("🦁 LEONES · LOTB\nPregunta: ¿puede el agente completar tareas pequeñas y reproducibles?\nNo es un benchmark de inteligencia general. No publica nada.\n")
    selected=TASKS if a.task=="all" else {a.task:TASKS[a.task]}
    results={}
    for code,prompt in selected.items():
        print(f"[{code}] ejecutando…",flush=True)
        results[code]=call_agent(a.endpoint,prompt,a.timeout)
        print(f"[{code}] {results[code]['status']} · {results[code]['elapsed_seconds']} s",flush=True)
    completed=sum(v.get("status")=="completed" for v in results.values())
    output={"schema_version":"1.0","tool":"leones-lotb","tool_version":"1.1","status":"completed","tasks":results,"summary":{"completed":completed,"total":len(results)}}
    print(json.dumps(output,indent=2,ensure_ascii=False))
    return 0 if completed else 2
if __name__=="__main__": raise SystemExit(main())
