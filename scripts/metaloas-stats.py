#!/usr/bin/env python3
"""Aggregate metaLOAS Markdown reports into statistics and PNG charts."""
from __future__ import annotations
import argparse, re
from collections import Counter
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ImportError:
    raise SystemExit("Falta matplotlib. Instala con: python3 -m pip install matplotlib")

RAM_RE=re.compile(r'^- RAM:\s*(.+)$', re.M)
CPU_RE=re.compile(r'^- CPU:\s*(.+)$', re.M)
OS_RE=re.compile(r'^- Sistema:\s*(.+)$', re.M)
GPU_RE=re.compile(r'^- GPU:\s*(.+)$', re.M)
PROFILE_RE=re.compile(r'^- Perfil LOAS:\s*(.+)$', re.M)
RESULT_RE=re.compile(r'^- Resultado agentivo:\s*(.+)$', re.M)
B_RE=re.compile(r'^- B0([1-5]):\s*(.+)$', re.M)

def val(rx,text):
    m=rx.search(text); return m.group(1).strip() if m else 'No indicado'

def parse(path):
    t=path.read_text(encoding='utf-8',errors='ignore')
    bs=dict(B_RE.findall(t))
    return {'file':path.name,'ram':val(RAM_RE,t),'cpu':val(CPU_RE,t),'os':val(OS_RE,t),'gpu':val(GPU_RE,t),'profile':val(PROFILE_RE,t),'result':val(RESULT_RE,t),'b':bs}

def save_bar(counter,title,path,xlabel=''):
    if not counter: return
    labels,values=zip(*counter.most_common())
    fig,ax=plt.subplots(figsize=(10,5)); ax.bar(labels,values); ax.set_title(title); ax.set_ylabel('Informes'); ax.set_xlabel(xlabel); ax.tick_params(axis='x',rotation=35); fig.tight_layout(); fig.savefig(path,dpi=150); plt.close(fig)

def main():
    ap=argparse.ArgumentParser(description='Genera estadísticas y gráficas de resultados metaLOAS')
    ap.add_argument('--input',default='results/metaLOAS'); ap.add_argument('--output',default='results/metaLOAS/stats'); args=ap.parse_args()
    root=Path(args.input); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    reports=[parse(p) for p in sorted(root.glob('*.md')) if p.name.lower()!='readme.md']
    if not reports: raise SystemExit(f'No hay informes Markdown en {root}')
    profiles=Counter(r['profile'] for r in reports); oses=Counter(r['os'] for r in reports); cpus=Counter(r['cpu'] for r in reports); rams=Counter(r['ram'] for r in reports)
    bs={f'B0{i}':Counter((r['b'].get(str(i),'Pendiente') for r in reports)) for i in range(1,6)}
    save_bar(profiles,'metaLOAS — perfiles de hardware',out/'profiles.png','Perfil')
    save_bar(oses,'metaLOAS — sistemas operativos',out/'os.png','Sistema')
    save_bar(rams,'metaLOAS — memoria RAM',out/'ram.png','RAM')
    save_bar(cpus,'metaLOAS — CPU',out/'cpu.png','CPU')
    b_success=Counter()
    for k,c in bs.items():
        b_success[k]=sum(v for label,v in c.items() if label.lower().startswith(('pass','ok','éxito','exito')))
    fig,ax=plt.subplots(figsize=(9,5)); ax.bar(list(b_success),list(b_success.values())); ax.set_title('metaLOAS — PASS por prueba LOTB'); ax.set_ylabel('Informes PASS'); fig.tight_layout(); fig.savefig(out/'lotb-pass.png',dpi=150); plt.close(fig)
    md=['# Estadísticas metaLOAS','',f'Informes analizados: **{len(reports)}**','', '## Distribución', '']
    for title,c in [('Perfiles',profiles),('RAM',rams),('Sistemas operativos',oses)]:
        md += [f'### {title}','']+[f'- {k}: {v}' for k,v in c.most_common()]+['']
    md += ['## LOTB — PASS detectados','']+[f'- {k}: {v}' for k,v in b_success.items()]+['','## Gráficas','', '- `profiles.png`', '- `os.png`', '- `ram.png`', '- `cpu.png`', '- `lotb-pass.png`','']
    (out/'README.md').write_text('\n'.join(md),encoding='utf-8')
    print(f'Analizados: {len(reports)}'); print(f'Estadísticas: {out}/README.md')

if __name__=='__main__': main()
