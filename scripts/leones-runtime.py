#!/usr/bin/env python3
"""LEONES runtime check: discover a local HTTP inference endpoint.

ANTES
-----
Pregunta: «¿Tengo ya un servicio local al que LEONES pueda enviar una petición?»
Este programa NO instala software, descarga modelos, inicia servicios ni publica datos.

DURANTE
-------
Comprueba únicamente los endpoints que indiques. No envía prompts a internet.

DESPUÉS
-------
Devuelve JSON con los endpoints alcanzables y una recomendación. Un endpoint
alcanzable no demuestra que un modelo funcione bien: para eso existe infer.

Ejemplo:
    python3 scripts/leones-runtime.py --url http://127.0.0.1:8080
"""
from __future__ import annotations
import argparse, json, time, urllib.error, urllib.request

def check(url: str, timeout: float) -> dict:
    started=time.perf_counter()
    try:
        req=urllib.request.Request(url, headers={"Accept":"application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"url":url,"reachable":True,"http_status":r.status,"elapsed_seconds":round(time.perf_counter()-started,3)}
    except Exception as exc:
        return {"url":url,"reachable":False,"error":str(exc),"elapsed_seconds":round(time.perf_counter()-started,3)}

def main()->int:
    p=argparse.ArgumentParser(description="Comprueba un runtime local; no instala ni ejecuta modelos.")
    p.add_argument("--url",action="append",help="URL a comprobar; puede repetirse")
    p.add_argument("--timeout",type=float,default=5)
    p.add_argument("--explain",action="store_true",help="Explica el propósito antes del resultado")
    a=p.parse_args(); urls=a.url or ["http://127.0.0.1:8080/v1/models","http://127.0.0.1:11434/api/tags"]
    if a.explain: print("🦁 LEONES · Comprobación de runtime\nNo instalamos nada ni enviamos prompts. Solo comprobamos si un endpoint local responde.\n")
    results=[check(u,a.timeout) for u in urls]
    reachable=[r for r in results if r["reachable"]]
    out={"tool":"leones-runtime","tool_version":"1.0","status":"ok","endpoints":results,"next_step":"infer" if reachable else "runtime setup"}
    print(json.dumps(out,indent=2,ensure_ascii=False)); return 0 if reachable else 2
if __name__=="__main__": raise SystemExit(main())
