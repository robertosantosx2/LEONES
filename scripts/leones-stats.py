#!/usr/bin/env python3
"""🦁 LEONES stats — agrega resultados; no los valida ni publica.

ANTES: recibe una carpeta de resultados JSON y explica qué va a contar.
DURANTE: ignora JSON inválido, resultados sin schema/status y, opcionalmente,
demos. Los valores ausentes no se inventan.
DESPUÉS: escribe estadísticas agregadas. No modifica resultados individuales,
no convierte `reported` en `verified` y no sustituye la revisión de Atlas.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
VALID_STATUSES={'reported','reproducible','verified','rejected'}
def load_results(root:Path,exclude_demo:bool)->list[dict]:
 results=[]
 if not root.exists():return results
 for path in root.rglob('*.json'):
  try:data=json.loads(path.read_text(encoding='utf-8'))
  except (OSError,json.JSONDecodeError):continue
  if not isinstance(data,dict) or 'schema_version' not in data or data.get('status') not in VALID_STATUSES:continue
  if exclude_demo and data.get('demo') is True:continue
  results.append(data)
 return results
def aggregate(results:list[dict])->dict:
 official=[r for r in results if r.get('status')!='rejected'];verified=[r for r in results if r.get('status')=='verified']
 statuses=Counter(r.get('status') for r in results);profiles=Counter();ram=Counter();speeds=[];lotb=defaultdict(Counter)
 for result in official:
  hw=result.get('hardware',{})
  if hw.get('profile'):profiles[str(hw['profile'])]+=1
  if hw.get('ram_gb') is not None:ram[str(hw['ram_gb'])]+=1
  speed=result.get('inference',{}).get('generation_tokens_per_second')
  if isinstance(speed,(int,float)):speeds.append(float(speed))
  for code,task in result.get('lotb',{}).items():
   if isinstance(task,dict):lotb[code][str(task.get('status','unknown'))]+=1
 return {'schema_version':'1.0','tool':'leones-stats','tool_version':'1.1','result_count':len(results),'official_count':len(official),'verified_count':len(verified),'status_counts':dict(statuses),'hardware_profiles':dict(profiles),'ram_gb':dict(ram),'generation_tokens_per_second':{'count':len(speeds),'min':min(speeds) if speeds else None,'max':max(speeds) if speeds else None,'average':round(sum(speeds)/len(speeds),3) if speeds else None,'at_least_10':sum(x>=10 for x in speeds),'at_least_100':sum(x>=100 for x in speeds)},'lotb':{code:dict(counts) for code,counts in sorted(lotb.items())}}
def main()->int:
 p=argparse.ArgumentParser(description='Agrega resultados LEONES sin convertirlos en verificaciones')
 p.add_argument('--root',default='results');p.add_argument('--output',default='web/data/stats.json');p.add_argument('--exclude-demo',action='store_true');p.add_argument('--explain',action='store_true')
 a=p.parse_args();print('🦁 LEONES · Estadísticas\nAntes: leeré resultados JSON existentes. No publicaré ni modificaré resultados individuales.\nDurante: aceptaré solo resultados con schema y estado reconocibles.\n')
 results=load_results(Path(a.root),a.exclude_demo);output=aggregate(results);destination=Path(a.output);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps(output,indent=2,ensure_ascii=False));print(f'\nDespués: estadísticas escritas en {destination}. Siguiente paso: interpretar estos agregados como evidencia colectiva, sin sustituir la revisión de Atlas.')
 return 0
if __name__=='__main__':raise SystemExit(main())
