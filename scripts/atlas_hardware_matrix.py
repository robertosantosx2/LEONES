#!/usr/bin/env python3
"""Generate the Atlas CPU/RAM/NVIDIA-GPU recommendation matrix.

GPU VRAM is treated separately from system RAM. The matrix is deliberately
materialized as one CSV instead of thousands of small files.
"""
from __future__ import annotations
import csv, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GPU_FILE=ROOT/'data/hardware/nvidia_ai_gpus.csv'
OUT=ROOT/'data/prospection/atlas_hardware_matrix.csv'
RECOMMENDER=ROOT/'scripts/atlas_recommend_from_feed.py'
CPUS=[('intel-i3','Intel Core i3'),('intel-i5','Intel Core i5'),('intel-i7','Intel Core i7'),('intel-i9','Intel Core i9'),('amd-ryzen3','AMD Ryzen 3'),('amd-ryzen5','AMD Ryzen 5'),('amd-ryzen7','AMD Ryzen 7'),('amd-ryzen9','AMD Ryzen 9')]
RAMS=[2,4,8,16,32,64,128]
FIELDS=['cpu_family','cpu_name','ram_gb','gpu_id','gpu_name','vram_gb','workload','rank','model_id','model_name','variant','quantization','runtime','estimated_memory_gb','context_tokens','tokens_per_second','quality_score','jgb_level','jgb_confidence','fit_score','confidence','reason']

def run():
    gpus=list(csv.DictReader(GPU_FILE.open(encoding='utf-8')))
    rows=[]
    with tempfile.TemporaryDirectory() as td:
      for cpu,cpu_name in CPUS:
       for ram in RAMS:
        # CPU-only baseline
        targets=[('', 'Sin GPU', 0)] + [(g['gpu_id'],g['model'],float(g['vram_gb'])) for g in gpus]
        for gid,gname,vram in targets:
         out=Path(td)/'r.csv'
         cmd=['python3',str(RECOMMENDER),'--workload','chat','--hardware',f'{cpu}-{ram}gb'+(f'-{gid}' if gid else ''),'--ram',str(ram),'--vram',str(vram),'--context',str(2048 if ram<=4 else 4096 if ram<=16 else 8192 if ram<=64 else 16384),'--out',str(out)]
         subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
         if not out.exists(): continue
         for r in csv.DictReader(out.open(encoding='utf-8')):
          rows.append({'cpu_family':cpu,'cpu_name':cpu_name,'ram_gb':ram,'gpu_id':gid or 'cpu-only','gpu_name':gname,'vram_gb':int(vram),'workload':'chat',**{k:r.get(k,'') for k in FIELDS if k not in {'cpu_family','cpu_name','ram_gb','gpu_id','gpu_name','vram_gb','workload'}}})
    with OUT.open('w',encoding='utf-8',newline='') as f:
      w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f'Matrix: {len(rows)} recommendation rows -> {OUT}')

if __name__=='__main__': run()
