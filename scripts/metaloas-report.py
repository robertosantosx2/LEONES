#!/usr/bin/env python3
"""Generate a privacy-conscious metaLOAS report and optionally publish it."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, os, platform, re, subprocess
from pathlib import Path

REPO = "robertosantosx2/LOAS"
REMOTE_DIR = "results/metaLOAS"

def run(cmd, timeout=8):
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout)
        return p.stdout.strip()
    except Exception: return ""

def first_line(s): return s.splitlines()[0].strip() if s else ""
def mem_gb():
    try: return f"{os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / 1024**3:.1f} GB"
    except Exception: return "No disponible"
def cpu_model():
    p=Path('/proc/cpuinfo')
    if p.exists():
        for line in p.read_text(errors='ignore').splitlines():
            if line.lower().startswith('model name'): return line.split(':',1)[1].strip()
    return platform.processor() or 'No disponible'
def os_info():
    data={}; p=Path('/etc/os-release')
    if p.exists():
        for line in p.read_text(errors='ignore').splitlines():
            if '=' in line:
                k,v=line.split('=',1); data[k]=v.strip().strip('"')
    return data.get('PRETTY_NAME', platform.system()), data.get('VERSION_ID','')
def gpu_info():
    out=[]
    n=run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'])
    for line in n.splitlines(): out.append('NVIDIA: '+line.strip())
    for line in run(['lspci']).splitlines():
        if re.search(r'VGA compatible controller|3D controller|Display controller',line,re.I):
            out.append(re.sub(r'^[0-9a-f:. -]+(?:VGA compatible controller|3D controller|Display controller):\s*','',line,flags=re.I).strip())
    return list(dict.fromkeys(out)) or ['No GPU detectada / no disponible']
def git_rev(path):
    if not Path(path).exists(): return 'No disponible'
    v=run(['git','-C',path,'rev-parse','HEAD']); return v[:12] if v else 'No disponible'
def sha256(path):
    if not path or not Path(path).is_file(): return 'No indicado'
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Genera un informe metaLOAS y opcionalmente lo publica en GitHub')
    ap.add_argument('--output', default='')
    ap.add_argument('--llama-cpp', default='llama.cpp'); ap.add_argument('--buddy', default='buddy'); ap.add_argument('--model', default='')
    ap.add_argument('--publish', action='store_true', help='publica en GitHub usando gh ya autenticado')
    ap.add_argument('--repo', default=REPO); args=ap.parse_args()
    os_name,os_version=os_info(); now=dt.datetime.now(dt.timezone.utc); stamp=now.strftime('%Y%m%d-%H%M%S')
    ram=mem_gb(); profile='H0' if ram.startswith('8.') else 'H1' if ram.startswith('16.') else 'H2' if ram.startswith('32.') else 'H3' if ram.startswith('64.') else 'pendiente'
    filename=f'{stamp}-{profile}.md'; rel=f'{REMOTE_DIR}/{filename}'; output=Path(args.output or rel)
    lines=['# metaLOAS — Informe automático','', '> Generado automáticamente. Revisar antes de publicar. No incluye deliberadamente datos personales.','',
      f'- Fecha de captura: {now.strftime("%Y-%m-%d %H:%M UTC")}',f'- Perfil LOAS: {profile}',f'- Sistema: {os_name} {os_version}'.strip(),f'- Kernel: {platform.release()}',f'- Arquitectura: {platform.machine()}',f'- CPU: {cpu_model()}',f'- RAM: {ram}',f'- GPU: {"; ".join(gpu_info())}','',
      '## Software','',f'- Python: {platform.python_version()}',f'- Git: {first_line(run(["git","--version"])) or "No disponible"}',f'- llama.cpp commit: `{git_rev(args.llama_cpp)}`',f'- llama-server presente: {"sí" if Path(args.llama_cpp,"build/bin/llama-server").is_file() else "no"}',f'- llama-bench presente: {"sí" if Path(args.llama_cpp,"build/bin/llama-bench").is_file() else "no"}',f'- Buddy commit: `{git_rev(args.buddy)}`','',
      '## Modelo','',f'- Fichero/modelo: `{Path(args.model).name if args.model else "No indicado"}`',f'- SHA-256: `{sha256(args.model)}`','- Cuantización: completar si no está indicada en el nombre del modelo','',
      '## LOTB','', '- B01: pendiente','- B02: pendiente','- B03: pendiente','- B04: pendiente','- B05: pendiente','- Resultado agentivo: pendiente','',
      '## Revisión humana','', '- Verificar que no aparecen datos personales o identificadores del equipo.','- Verificar modelo y SHA-256.','- Verificar commits exactos.','- Observaciones: ']
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(f'Informe creado: {output}')
    if args.publish:
        if not run(['gh','auth','status'],timeout=10):
            print('GitHub CLI no está autenticado. Ejecuta: gh auth login'); return 2
        content=base64.b64encode(output.read_bytes()).decode()
        result=run(['gh','api',f'repos/{args.repo}/contents/{rel}','--method','PUT','-f',f'message=metaLOAS: add {filename}','-f',f'content={content}'],timeout=30)
        if result: print(f'Publicado en https://github.com/{args.repo}/blob/main/{rel}')
        else: print('No se pudo publicar en GitHub.'); return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
