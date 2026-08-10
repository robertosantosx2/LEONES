#!/usr/bin/env python3
"""Generate a privacy-conscious metaLOAS report and optionally publish it."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, os, platform, re, subprocess, time
from pathlib import Path

REPO="robertosantosx2/LOAS"; REMOTE_DIR="results/metaLOAS"
def run(cmd,timeout=8):
    try:
        p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=timeout); return p.stdout.strip()
    except Exception:return ""
def first(s):return s.splitlines()[0].strip() if s else ""
def mem_gb():
    try:return f"{os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')/1024**3:.1f} GB"
    except Exception:return "No disponible"
def cpu_model():
    p=Path('/proc/cpuinfo')
    if p.exists():
        for l in p.read_text(errors='ignore').splitlines():
            if l.lower().startswith('model name'):return l.split(':',1)[1].strip()
    return platform.processor() or 'No disponible'
def os_info():
    d={};p=Path('/etc/os-release')
    if p.exists():
        for l in p.read_text(errors='ignore').splitlines():
            if '=' in l:k,v=l.split('=',1);d[k]=v.strip().strip('"')
    return d.get('PRETTY_NAME',platform.system()),d.get('VERSION_ID','')
def gpu_info():
    out=[];n=run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'])
    for l in n.splitlines():out.append('NVIDIA: '+l.strip())
    for l in run(['lspci']).splitlines():
        if re.search(r'VGA compatible controller|3D controller|Display controller',l,re.I):out.append(re.sub(r'^[0-9a-f:. -]+(?:VGA compatible controller|3D controller|Display controller):\s*','',l,flags=re.I).strip())
    return list(dict.fromkeys(out)) or ['No GPU detectada / no disponible']
def git_rev(path):
    v=run(['git','-C',path,'rev-parse','HEAD']) if Path(path).exists() else '';return v[:12] if v else 'No disponible'
def sha256(path):
    if not path or not Path(path).is_file():return 'No indicado'
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()
def profile(r):return 'H0' if r.startswith('8.') else 'H1' if r.startswith('16.') else 'H2' if r.startswith('32.') else 'H3' if r.startswith('64.') else 'pendiente'
def extract_bench(text):
    patterns=[r'([0-9]+(?:\.[0-9]+)?)\s*tok/s',r'([0-9]+(?:\.[0-9]+)?)\s*tokens?/sec']
    for p in patterns:
        m=re.search(p,text,re.I)
        if m:return m.group(1)
    return ''
def main():
    ap=argparse.ArgumentParser(description='Genera un informe metaLOAS y opcionalmente lo publica en GitHub')
    ap.add_argument('--output',default='');ap.add_argument('--llama-cpp',default='llama.cpp');ap.add_argument('--buddy',default='buddy');ap.add_argument('--model',default='')
    ap.add_argument('--bench-output',default='',help='salida guardada de llama-bench/benchmark para extraer tok/s')
    ap.add_argument('--lotb-results',default='',help='Markdown/JSON de LOTB para incorporar resultados')
    ap.add_argument('--publish',action='store_true');ap.add_argument('--repo',default=REPO);args=ap.parse_args()
    os_name,os_version=os_info();now=dt.datetime.now(dt.timezone.utc);ram=mem_gb();pr=profile(ram);stamp=now.strftime('%Y%m%d-%H%M%S');filename=f'{stamp}-{pr}.md';rel=f'{REMOTE_DIR}/{filename}';output=Path(args.output or rel)
    bench=Path(args.bench_output).read_text(errors='ignore') if args.bench_output and Path(args.bench_output).is_file() else ''
    lotb=Path(args.lotb_results).read_text(errors='ignore') if args.lotb_results and Path(args.lotb_results).is_file() else ''
    tok=extract_bench(bench);lotb_lines=[]
    for i in range(1,6):
        m=re.search(rf'B0{i}[^\n]*?[:=-]\s*([^\n]+)',lotb,re.I);lotb_lines.append(f'- B0{i}: {m.group(1).strip() if m else "pendiente"}')
    result='pendiente'
    if lotb:
        result='PASS' if all('pass' in x.lower() for x in lotb_lines) else 'PARCIAL/REVISAR'
    lines=['# metaLOAS — Informe automático','', '> Generado automáticamente. Revisar antes de publicar. No incluye deliberadamente datos personales.','',f'- Fecha de captura: {now:%Y-%m-%d %H:%M UTC}',f'- Perfil LOAS: {pr}',f'- Sistema: {os_name} {os_version}',f'- Kernel: {platform.release()}',f'- Arquitectura: {platform.machine()}',f'- CPU: {cpu_model()}',f'- RAM: {ram}',f'- GPU: {"; ".join(gpu_info())}','', '## Software','',f'- Python: {platform.python_version()}',f'- Git: {first(run(["git","--version"])) or "No disponible"}',f'- llama.cpp commit: `{git_rev(args.llama_cpp)}`',f'- llama-server presente: {"sí" if Path(args.llama_cpp,"build/bin/llama-server").is_file() else "no"}',f'- llama-bench presente: {"sí" if Path(args.llama_cpp,"build/bin/llama-bench").is_file() else "no"}',f'- Buddy commit: `{git_rev(args.buddy)}`','', '## Modelo','',f'- Fichero/modelo: `{Path(args.model).name if args.model else "No indicado"}`',f'- SHA-256: `{sha256(args.model)}`','- Cuantización: completar si no está indicada en el nombre del modelo','', '## Rendimiento','',f'- Inferencia: {tok+" tok/s" if tok else "no indicado"}','- Latencia: no indicada','- Tiempo por tarea: no indicado','', '## LOTB','']+lotb_lines+[f'- Resultado agentivo: {result}','', '## Revisión humana','', '- Verificar que no aparecen datos personales o identificadores del equipo.','- Verificar modelo y SHA-256.','- Verificar commits exactos.','- Verificar las métricas de rendimiento y LOTB.','- Observaciones: ']
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(f'Informe creado: {output}')
    if args.publish:
        if not run(['gh','auth','status'],10):print('GitHub CLI no está autenticado. Ejecuta: gh auth login');return 2
        content=base64.b64encode(output.read_bytes()).decode();res=run(['gh','api',f'repos/{args.repo}/contents/{rel}','--method','PUT','-f',f'message=metaLOAS: add {filename}','-f',f'content={content}'],30)
        if res:print(f'Publicado en https://github.com/{args.repo}/blob/main/{rel}')
        else:print('No se pudo publicar en GitHub.');return 1
    return 0
if __name__=='__main__':raise SystemExit(main())