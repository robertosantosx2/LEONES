#!/usr/bin/env python3
"""Classify discovery candidates without changing their provenance.

This is intentionally heuristic and transparent. It adds categories and reasons;
it does not publish to Atlas and does not infer license approval.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from pathlib import Path

RULES={
 'models':[r'\b(llm|language model|foundation model|vlm|vision-language|embedding|reranker|text-generation|code-generation|multimodal model)\b',r'\b(model|weights|checkpoint|inference model)\b'],
 'runtimes':[r'\b(inference runtime|model serving|serving|inference server|quantization|llama\.cpp|vllm|transformers|runtime|router)\b'],
 'agents':[r'\b(agent framework|ai agent|autonomous agent|multi-agent|tool calling|agentic|agent)\b'],
 'skills':[r'\b(mcp server|mcp|skill|plugin|tool|agent tool|workflow)\b'],
 'harnesses':[r'\b(evaluation harness|benchmark harness|agent harness|evaluation|benchmark|testing|test harness)\b'],
 'hardware':[r'\b(ai accelerator|cpu inference|gpu inference|npu|accelerator|edge ai|hardware|tpu)\b'],
}

def text(row):
    return ' '.join(str(row.get(k,'')) for k in ('name','description','query')).lower()

def classify(row):
    t=text(row); hits={}
    for category,patterns in RULES.items():
        matched=[p for p in patterns if re.search(p,t,re.I)]
        if matched:hits[category]=matched
    cats=list(hits)
    if not cats:
        cats=['unclassified']
        confidence='low'
    else:
        confidence='high' if len(cats)==1 and len(hits[cats[0]])>=2 else 'medium'
    row['categories']=cats
    row['category_confidence']=confidence
    row['classification_reason']='keyword evidence from name/description/discovery query'
    row['classification_evidence']=hits
    row['publication_status']='review'
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',default='data/prospection/live_discoveries.ndjson');p.add_argument('--output',default='data/prospection/classified_discoveries.ndjson');a=p.parse_args()
    src=Path(a.input);dst=Path(a.output);dst.parent.mkdir(parents=True,exist_ok=True)
    counts=Counter();total=0
    with src.open(encoding='utf-8') as f,dst.open('w',encoding='utf-8') as out:
        for line in f:
            if not line.strip():continue
            row=classify(json.loads(line));out.write(json.dumps(row,ensure_ascii=False)+'\n');total+=1
            for c in row['categories']:counts[c]+=1
    print(json.dumps({'total':total,'categories':dict(counts),'output':str(dst)},ensure_ascii=False))
if __name__=='__main__':main()
