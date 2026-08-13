#!/usr/bin/env python3
"""Report the sources scheduled for daily prospection.

This is the orchestration boundary: individual source adapters can be added
without changing the Atlas ingest contract. It intentionally does not mark
sources as successfully crawled unless an adapter records evidence.
"""
import argparse,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--registry',default='scripts/prospection/sources_registry.json');a=ap.parse_args()
 data=json.loads(Path(a.registry).read_text(encoding='utf-8'))
 for s in data.get('sources',[]):
  print(json.dumps({'source_id':s['id'],'name':s['name'],'url':s['url'],'kind':s['kind'],'scheduled':True,'status':'adapter-required'},ensure_ascii=False))
if __name__=='__main__':main()
