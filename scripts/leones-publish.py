#!/usr/bin/env python3
"""Validate a report for obvious private data before optional GitHub publication."""
from pathlib import Path
import argparse, re, subprocess

PATTERNS={
 'email':r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
 'token':r'(?i)\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]+',
 'home path':r'/(?:home|Users)/[^\s`]+',
}

def main():
 p=argparse.ArgumentParser(description='Check and optionally publish a LEONES report.')
 p.add_argument('report');p.add_argument('--publish',action='store_true');p.add_argument('--repo',default='robertosantosx2/LEONES');p.add_argument('--path',default='')
 a=p.parse_args(); path=Path(a.report); text=path.read_text(encoding='utf-8',errors='ignore'); issues=[]
 for name,pattern in PATTERNS.items():
  if re.search(pattern,text): issues.append(name)
 if issues:
  print('Privacy check FAILED: '+', '.join(issues)); return 2
 print('Privacy check: OK')
 if not a.publish: return 0
 target=a.path or f'results/metaLEONES/{path.name}'
 try:
  subprocess.run(['gh','auth','status'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
  subprocess.run(['gh','api',f'repos/{a.repo}/contents/{target}','--method','PUT','--field',f'message=metaLEONES: add {path.name}','--field',f'content={__import__("base64").b64encode(path.read_bytes()).decode()}'],check=True,timeout=30)
 except Exception:
  print('Publication failed. Authenticate with: gh auth login'); return 1
 print(f'Published: https://github.com/{a.repo}/blob/main/{target}'); return 0

if __name__=='__main__': raise SystemExit(main())
