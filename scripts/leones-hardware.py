#!/usr/bin/env python3
"""🦁 LEONES · Hardware probe.

ANTES
-----
Pregunta: «¿Qué máquina tengo y qué límites físicos condicionan la IA local?»
Solo inspecciona información del sistema operativo. No descarga modelos,
no ejecuta inferencia, no modifica el sistema y no publica nada.

DURANTE
-------
Recoge CPU, arquitectura, RAM, GPU y sistema operativo. Las operaciones son
locales. Si una utilidad no está instalada, el campo queda sin detectar.

DESPUÉS
-------
El resultado es un punto de partida, no una recomendación definitiva. El
siguiente paso habitual es identificar un modelo y después medir inferencia.
Para compartirlo, revisa siempre privacidad antes de publicar.

Ejemplo:
    python3 scripts/leones-hardware.py --explain --json
"""
from __future__ import annotations
from pathlib import Path
import argparse, json, os, platform, re, subprocess

def command(*args):
    try:return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=5).strip()
    except Exception:return ""
def ram_gb():
    try:return round(os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')/1024**3,1)
    except Exception:return None
def cpu():
    p=Path('/proc/cpuinfo')
    if p.exists():
        for line in p.read_text(errors='ignore').splitlines():
            if line.lower().startswith('model name:'): return line.split(':',1)[1].strip()
    return platform.processor() or None
def gpu():
    found=[]; n=command('nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader')
    found += [f"NVIDIA: {x}" for x in n.splitlines() if x]
    for line in command('lspci').splitlines():
        if re.search(r'VGA compatible controller|3D controller|Display controller',line,re.I): found.append(line.split(': ',1)[-1].strip())
    return list(dict.fromkeys(found)) or []
def main():
    p=argparse.ArgumentParser(description='Perfil técnico local, sin benchmark ni publicación')
    p.add_argument('--json',action='store_true'); p.add_argument('--explain',action='store_true')
    a=p.parse_args()
    if a.explain and not a.json: print('🦁 LEONES · Diagnóstico de hardware\nVoy a identificar CPU, RAM, GPU, arquitectura y sistema operativo. No descargaré ni ejecutaré modelos.\n')
    data={'tool':'leones-hardware','tool_version':'1.1','status':'ok','hardware':{'cpu':cpu(),'architecture':platform.machine(),'ram_gb':ram_gb(),'gpu':gpu(),'os':f'{platform.system()} {platform.release()}'},'next_step':'model'}
    if a.json: print(json.dumps(data,indent=2,ensure_ascii=False)); return 0
    h=data['hardware']; print(f"CPU: {h['cpu'] or 'no detectada'}\nArquitectura: {h['architecture']}\nRAM: {h['ram_gb'] or 'no detectada'} GB\nGPU: {'; '.join(h['gpu']) if h['gpu'] else 'ninguna detectada'}\nOS: {h['os']}\n\nSiguiente paso recomendado: identificar un modelo y luego medirlo.")
if __name__=='__main__': main()
