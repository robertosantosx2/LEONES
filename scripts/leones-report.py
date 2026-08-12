#!/usr/bin/env python3
"""🦁 LEONES report — presentation only.

ANTES: recibe un resultado JSON ya obtenido por otras herramientas.
DURANTE: valida que sea JSON y convierte los campos conocidos a Markdown.
DESPUÉS: deja un informe legible y señala explícitamente qué está medido,
qué no se ejecutó y qué significa el estado. No publica ni verifica.

Uso: python3 scripts/leones-report.py result.json --output result.md
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

def task_line(code:str,task:dict|None)->str:
    if not task:return f"| {code} | not_run | — |"
    return f"| {code} | {task.get('status','not_run')} | {task.get('elapsed_seconds','—')} |"

def render(data:dict)->str:
    hw=data.get('hardware',{}); model=data.get('model',{}); inf=data.get('inference',{}); lotb=data.get('lotb',{}); software=data.get('software',{})
    status=data.get('status','reported')
    lines=["# 🦁 LEONES · Informe de resultado","","> Este documento presenta mediciones obtenidas localmente. Generarlo no publica el resultado ni lo convierte automáticamente en evidencia verificada.","",f"**Schema:** `{data.get('schema_version','unknown')}`  ",f"**Estado declarado:** `{status}`","", "## ¿Qué se hizo?", "", "LEONES separa descubrimiento, medición, tareas agentivas, presentación y publicación. Los campos ausentes se muestran como no disponibles en lugar de inventarlos.","", "## Hardware", "",f"- Perfil: `{hw.get('profile','unknown')}`",f"- CPU: {hw.get('cpu','unknown')}",f"- Arquitectura: {hw.get('architecture','unknown')}",f"- Cores / threads: {hw.get('cores','—')} / {hw.get('threads','—')}",f"- RAM: {hw.get('ram_gb','—')} GB",f"- GPU: {hw.get('gpu','none reported')}",f"- VRAM: {hw.get('vram_gb','—')} GB",f"- OS: {hw.get('os','unknown')}","", "## Modelo", "",f"- Nombre: `{model.get('name','unknown')}`",f"- Formato: `{model.get('format','—')}`",f"- Quantisation: `{model.get('quantization','—')}`",f"- Tamaño: `{model.get('size_bytes','—')}` bytes",f"- SHA-256: `{model.get('sha256','—')}`","", "## Inferencia", "",f"- Tiempo: {inf.get('elapsed_seconds','—')} s",f"- Prompt tokens: {inf.get('prompt_tokens','—')}",f"- Completion tokens: {inf.get('completion_tokens','—')}",f"- Generación: {inf.get('generation_tokens_per_second','—')} tok/s","", "## LOTB", "", "| Tarea | Estado | Tiempo (s) |", "|---|---|---:|"]
    for code in ('B01','B02','B03','B04','B05'): lines.append(task_line(code,lotb.get(code)))
    lines += ["", "## Software", ""]
    for key,value in software.items(): lines.append(f"- {key}: `{value}`")
    lines += ["", "## Cómo interpretar este informe", "", "`reported` significa que existe un resultado presentado. `reproducible` y `verified` requieren procesos adicionales; `verified` no debe asignarse solo por generar este documento.","", "## Siguiente paso", "", "Si vas a compartirlo, ejecuta primero `leones-privacy.py` y revisa manualmente el contenido. Solo después considera `leones-publish.py`.","", "---", "Generado por `scripts/leones-report.py`.", ""]
    return '\n'.join(lines)

def main()->int:
    p=argparse.ArgumentParser(description='Genera un informe Markdown explicado a partir de un resultado LEONES')
    p.add_argument('result'); p.add_argument('--output',required=True); p.add_argument('--explain',action='store_true')
    a=p.parse_args()
    if a.explain: print('🦁 LEONES · Informe\nConvierte un JSON existente en un documento legible. No mide, no publica y no verifica.\n')
    try:data=json.loads(Path(a.result).read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as exc: print(f'No se pudo leer el resultado: {exc}'); return 2
    if not isinstance(data,dict): print('El resultado debe ser un objeto JSON.'); return 2
    Path(a.output).write_text(render(data),encoding='utf-8'); print(f'Informe creado: {a.output}\nSiguiente paso: revisar privacidad antes de compartir.'); return 0
if __name__=='__main__': raise SystemExit(main())
