#!/usr/bin/env python3
"""Aggregate public metaLEONES Markdown reports into simple statistics."""
from pathlib import Path
from collections import Counter
import argparse, re

def value(text,key):
 m=re.search(rf'^- {re.escape(key)}:\s*(.+)$',text,re.M); return m.group(1).strip() if m else 'unknown'

def tok(text):
 m=re.search(r'([0-9]+(?:\.[0-9]+)?)\s*tok/s',text,re.I); return float(m.group(1)) if m else None

def main():
 p=argparse.ArgumentParser(description='Aggregate public metaLEONES reports.')
 p.add_argument('--input',default='results/metaLEONES');p.add_argument('--output',default='results/metaLEONES/stats.md');a=p.parse_args()
 root=Path(a.input); reports=[x for x in root.glob('*.md') if x.name.lower()!='readme.md']
 if not reports: raise SystemExit(f'No reports in {root}')
 data=[r.read_text(encoding='utf-8',errors='ignore') for r in reports]
 values=[tok(x) for x in data]; values=[x for x in values if x is not None]
 lines=['# metaLEONES statistics','',f'Reports analysed: **{len(data)}**','', '## Performance','',f'Reports with tok/s: **{len(values)}**']
 if values: lines += [f'Mean: **{sum(values)/len(values):.2f} tok/s**',f'≥ 10 tok/s: **{sum(x>=10 for x in values)}**',f'≥ 100 tok/s: **{sum(x>=100 for x in values)}**']
 else: lines += ['Mean: not available']
 for title,key in [('RAM','RAM'),('CPU','CPU'),('OS','Sistema'),('GPU','GPU')]:
  c=Counter(value(t,key) for t in data); lines += ['',f'## {title}','']+[f'- {k}: {v}' for k,v in c.most_common()]
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(out)

if __name__=='__main__': main()
