#!/usr/bin/env python3
"""Create a simple Markdown experiment report from supplied evidence.

No measurement is invented here. Missing values remain 'not provided'.
"""
from pathlib import Path
import argparse, datetime as dt

def read(path):
    return Path(path).read_text(encoding='utf-8',errors='ignore') if path else ''

def main():
    p=argparse.ArgumentParser(description='Create a LEONES Markdown experiment report.')
    p.add_argument('--hardware',help='Text/Markdown produced by leones-hardware.py')
    p.add_argument('--model',help='Text/Markdown produced by leones-model.py')
    p.add_argument('--inference',help='Inference measurements')
    p.add_argument('--lotb',help='LOTB results')
    p.add_argument('--output',default='result.md')
    a=p.parse_args()
    sections=[]
    for title,path in [('Hardware',a.hardware),('Model',a.model),('Inference',a.inference),('LOTB',a.lotb)]:
        sections += [f'## {title}','',read(path) if path else 'Not provided','']
    text='\n'.join(['# LEONES experiment report','',f'Captured: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M UTC}','', '> Generated from supplied measurements. Review privacy before publication.','']+sections)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(text,encoding='utf-8'); print(out)

if __name__ == '__main__': main()
