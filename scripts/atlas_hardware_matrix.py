#!/usr/bin/env python3
"""Generate the Atlas CPU/RAM/NVIDIA-GPU recommendation matrix.

GPU VRAM is treated separately from system RAM. Context is a model capability,
not a requirement that grows automatically with host RAM. For each hardware
profile the recommendation uses the model-supported context, capped by the
profile target.
"""
from __future__ import annotations
import csv, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GPU_FILE=ROOT/'data/hardware/nvidia_ai_gpus.csv'
OUT=ROOT/'data/prospection/atlas_hardware_matrix.csv'
RECOMMENDER=ROOT/'scripts/atlas_recommend_from_feed.py'
FEED=ROOT/'data/prospection/atlas_feed.csv'
CPUS=[('intel-i3','Intel Core i3'),('intel-i5','Intel Core i5'),('intel-i7','Intel Core i7'),('intel-i9','Intel Core i9'),('amd-ryzen3','AMD Ryzen 3'),('amd-ryzen5','AMD Ryzen 5'),('amd-ryzen7','AMD Ryzen 7'),('amd-ryzen9','AMD Ryzen 9')]
RAMS=[2,4,8,16,32,64,128]
FIELDS=['cpu_family','cpu_name','ram_gb','gpu_id','gpu_name','vram_gb','workload','rank','model_id','model_name','variant','quantization','runtime','estimated_memory_gb','context_tokens','context_target_tokens','tokens_per_second','quality_score','jgb_level','jgb_confidence','fit_score','confidence','reason']

def diagnose(rows, hardware, ram, vram, context):
    limit=ram+vram
    counts={k:0 for k in ('not_profile','memory','context','runtime','quantization_or_weights','hardware','workload','fits')}
    t23=0
    for r in rows:
        if (r.get('technical_profile_level') or '') not in ('T2','T3'):
            counts['not_profile']+=1; continue
        t23+=1
        if r.get('workload') and r['workload']!='chat': counts['workload']+=1; continue
        rh=(r.get('hardware_id') or '').strip().lower(); req=hardware.lower()
        if rh and rh not in req and rh != req: counts['hardware']+=1; continue
        try: mem=float(r.get('estimated_memory_gb') or r.get('weight_memory_gb') or '')
        except ValueError: mem=None
        try: ctx=float(r.get('context_tokens') or '')
        except ValueError: ctx=None
        if mem is None or mem>limit: counts['memory']+=1; continue
        if ctx is None: counts['context']+=1; continue
        if not (r.get('runtime') or '').strip(): counts['runtime']+=1; continue
        if not ((r.get('quantization') or '').strip() or (r.get('weight_memory_gb') or '').strip()): counts['quantization_or_weights']+=1; continue
        counts['fits']+=1
    print(f'Diagnostic {hardware}: T2/T3={t23}; exclusions=' + ', '.join(f'{k}={v}' for k,v in counts.items() if v))
    return counts

def run():
    gpus=list(csv.DictReader(GPU_FILE.open(encoding='utf-8')))
    rows=[]
    with FEED.open(encoding='utf-8-sig',newline='') as f:
        feed_rows=list(csv.DictReader(f))
    with tempfile.TemporaryDirectory() as td:
      for cpu,cpu_name in CPUS:
       for ram in RAMS:
        target_context=2048 if ram<=4 else 4096 if ram<=16 else 8192 if ram<=64 else 16384
        targets=[('', 'Sin GPU', 0)] + [(g['gpu_id'],g['model'],float(g['vram_gb'])) for g in gpus]
        for gid,gname,vram in targets:
         hardware=f'cpu-{cpu}-{ram}gb' + (f'-{gid}' if gid else '')
         out=Path(td)/'r.csv'
         cmd=['python3',str(RECOMMENDER),'--workload','chat','--hardware',hardware,'--ram',str(ram),'--vram',str(vram),'--context','1','--out',str(out)]
         subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
         if not out.exists(): continue
         for r in csv.DictReader(out.open(encoding='utf-8')):
          try: supported=float(r.get('context_tokens') or '')
          except (TypeError,ValueError): supported=None
          recommended=min(supported,target_context) if supported is not None else ''
          r['context_target_tokens']=recommended
          rows.append({'cpu_family':cpu,'cpu_name':cpu_name,'ram_gb':ram,'gpu_id':gid or 'cpu-only','gpu_name':gname,'vram_gb':int(vram),'workload':'chat',**{k:r.get(k,'') for k in FIELDS if k not in {'cpu_family','cpu_name','ram_gb','gpu_id','gpu_name','vram_gb','workload'}}})
    with OUT.open('w',encoding='utf-8',newline='') as f:
      w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f'Matrix: {len(rows)} recommendation rows -> {OUT}')
    if not rows:
        diagnose(feed_rows,'cpu-intel-i5-128gb',128,0,16384)
        if gpus:
            gid=gpus[0]['gpu_id']; v=float(gpus[0]['vram_gb'])
            diagnose(feed_rows,f'cpu-intel-i5-128gb-{gid}',128,v,16384)
        raise SystemExit('ERROR: la matriz hardware no puede publicarse vacía')

if __name__=='__main__': run()
