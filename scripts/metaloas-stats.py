#!/usr/bin/env python3
"""Aggregate metaLOAS reports into statistics, charts and recommendation signals."""
from __future__ import annotations
import argparse,re
from collections import Counter,defaultdict
from pathlib import Path
try: import matplotlib.pyplot as plt
except ImportError: raise SystemExit('Falta matplotlib. Instala con: python3 -m pip install matplotlib')

def rx(name): return re.compile(rf'^- {name}:\s*(.+)$',re.M)
RAM=rx('RAM');CPU=rx('CPU');OS=rx('Sistema');GPU=rx('GPU');PROFILE=rx('Perfil LOAS');TOK=rx('Inferencia');LAT=rx('Latencia');TASK=rx('Tiempo por tarea');RESULT=rx('Resultado agentivo');B=re.compile(r'^- B0([1-5]):\s*(.+)$',re.M)
def val(r,t):
 m=r.search(t);return m.group(1).strip() if m else 'No indicado'
def num(s):
 m=re.search(r'([0-9]+(?:[.,][0-9]+)?)',s.replace(',','.'));return float(m.group(1)) if m else None
def parse(p):
 t=p.read_text(encoding='utf-8',errors='ignore');return {'file':p.name,'ram':val(RAM,t),'cpu':val(CPU,t),'os':val(OS,t),'gpu':val(GPU,t),'profile':val(PROFILE,t),'tok':num(val(TOK,t)),'lat':num(val(LAT,t)),'task':num(val(TASK,t)),'result':val(RESULT,t),'b':dict(B.findall(t))}
def bar(c,title,path,xlabel=''):
 if not c:return
 l,v=zip(*c.most_common());fig,ax=plt.subplots(figsize=(10,5));ax.bar(l,v);ax.set_title(title);ax.set_ylabel('Informes');ax.set_xlabel(xlabel);ax.tick_params(axis='x',rotation=35);fig.tight_layout();fig.savefig(path,dpi=150);plt.close(fig)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',default='results/metaLOAS');ap.add_argument('--output',default='results/metaLOAS/stats');a=ap.parse_args();root=Path(a.input);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 rs=[parse(p) for p in sorted(root.glob('*.md')) if p.name.lower()!='readme.md' and not p.is_relative_to(out)]
 if not rs:raise SystemExit(f'No hay informes Markdown en {root}')
 profiles=Counter(r['profile'] for r in rs);oses=Counter(r['os'] for r in rs);rams=Counter(r['ram'] for r in rs);cpus=Counter(r['cpu'] for r in rs)
 bar(profiles,'metaLOAS — perfiles',out/'profiles.png','Perfil');bar(oses,'metaLOAS — sistemas operativos',out/'os.png','Sistema');bar(rams,'metaLOAS — RAM',out/'ram.png','RAM');bar(cpus,'metaLOAS — CPU',out/'cpu.png','CPU')
 valid=[r for r in rs if r['tok'] is not None];
 if valid:
  fig,ax=plt.subplots(figsize=(10,5));ax.scatter([r['profile'] for r in valid],[r['tok'] for r in valid]);ax.axhline(10,linestyle='--');ax.set_title('metaLOAS — rendimiento de inferencia');ax.set_ylabel('tok/s');ax.set_xlabel('Perfil');fig.tight_layout();fig.savefig(out/'tokens-per-second.png',dpi=150);plt.close(fig)
 bs={f'B0{i}':Counter(r['b'].get(str(i),'Pendiente') for r in rs) for i in range(1,6)};passes={k:sum(v for s,v in c.items() if s.lower().startswith(('pass','ok','éxito','exito'))) for k,c in bs.items()}
 fig,ax=plt.subplots(figsize=(9,5));ax.bar(list(passes),list(passes.values()));ax.set_title('metaLOAS — PASS por LOTB');ax.set_ylabel('Informes PASS');fig.tight_layout();fig.savefig(out/'lotb-pass.png',dpi=150);plt.close(fig)
 md=['# Estadísticas metaLOAS','',f'Informes analizados: **{len(rs)}**','', '## Rendimiento','',f'- Informes con tok/s: **{len(valid)}**',f'- Media tok/s: **{sum(r["tok"] for r in valid)/len(valid):.2f}**' if valid else '- Media tok/s: no disponible',f'- >=10 tok/s: **{sum(r["tok"]>=10 for r in valid)}**' if valid else '- >=10 tok/s: no disponible',f'- >=100 tok/s: **{sum(r["tok"]>=100 for r in valid)}**' if valid else '- >=100 tok/s: no disponible','', '## Distribución','']
 for title,c in [('Perfiles',profiles),('RAM',rams),('Sistemas operativos',oses)]:md += [f'### {title}','']+[f'- {k}: {v}' for k,v in c.most_common()]+['']
 md += ['## LOTB — PASS','']+[f'- {k}: {v}' for k,v in passes.items()]+['','## Señales para recomendaciones','']
 for prof,grp in __import__('itertools').groupby(sorted(rs,key=lambda x:x['profile']),lambda x:x['profile']):
  g=list(grp);v=[x['tok'] for x in g if x['tok'] is not None]
  if v:md.append(f'- **{prof}**: media {sum(v)/len(v):.2f} tok/s; {sum(x>=10 for x in v)}/{len(v)} supera el mínimo de 10 tok/s.')
 md += ['','## Gráficas','', '- `profiles.png`','- `os.png`','- `ram.png`','- `cpu.png`','- `tokens-per-second.png`','- `lotb-pass.png`']
 (out/'README.md').write_text('\n'.join(md)+'\n',encoding='utf-8');print(f'Analizados: {len(rs)}; estadísticas: {out}/README.md')
if __name__=='__main__':main()
