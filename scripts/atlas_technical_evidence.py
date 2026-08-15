#!/usr/bin/env python3
"""Conservatively enrich Atlas with structured technical evidence."""
from __future__ import annotations
import csv, json, re, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/'data/prospection/atlas_feed.csv'
EVIDENCE=ROOT/'data/prospection/atlas_technical_evidence.csv'
TIMEOUT=15
UA='LEONES-Atlas/1.0 (+https://github.com/robertosantosx2/LEONES)'
EXTRA=['parameters_total_b','parameters_active_b','architecture','context_tokens','runtime','runtime_version','backend','quantization','weight_memory_gb','estimated_memory_gb','hidden_size','num_hidden_layers','num_attention_heads','num_key_value_heads','torch_dtype','technical_evidence_url','technical_evidence_state','technical_profile_level','technical_evidence_checked_at']

def get_json(url):
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urlopen(req,timeout=TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))

def hf_model_id(row):
    url=(row.get('repository_url') or row.get('source_url') or '').strip()
    m=re.match(r'https?://huggingface\.co/([^/?#]+/[^/?#]+)',url)
    return m.group(1) if m else ''

def number(value):
    if isinstance(value,(int,float)): return float(value)
    if isinstance(value,str):
        m=re.search(r'(\d+(?:\.\d+)?)',value)
        return float(m.group(1)) if m else None
    return None

def infer_quant(config,model_id):
    text=' '.join(str(config.get(k,'')) for k in ('quantization_config','quantization','torch_dtype') if config.get(k) is not None).lower()+' '+model_id.lower()
    for q in ('gptq','awq','gguf','int4','4bit','int8','8bit','fp8','bf16','bfloat16','fp16','float16'):
        if q in text:
            return {'4bit':'int4','8bit':'int8','bfloat16':'bf16','float16':'fp16'}.get(q,q)
    return ''

def enrich(row):
    out=dict(row); model_id=hf_model_id(row)
    if not model_id:
        out['technical_profile_level']=out.get('technical_profile_level') or 'T0'
        return out
    base=f'https://huggingface.co/{model_id}'
    try:
        info=get_json(f'https://huggingface.co/api/models/{model_id}')
        config=info.get('config') or {}
        safe=info.get('safetensors') or {}
        archs=config.get('architectures') or []
        if archs: out['architecture']=str(archs[0])
        for key in ('max_position_embeddings','max_sequence_length','model_max_length'):
            value=number(config.get(key))
            if value and value < 10_000_000:
                out['context_tokens']=str(int(value)); break
        quant=infer_quant(config,model_id)
        if quant: out['quantization']=quant
        dtype=str(config.get('torch_dtype') or '').lower()
        if dtype: out['torch_dtype']=dtype
        if config:
            out['runtime']=out.get('runtime') or 'transformers'
            out['backend']=out.get('backend') or 'pytorch'
        card=info.get('cardData') or {}
        for key in ('parameters','parameter_count','num_parameters'):
            p=number(card.get(key))
            if p:
                out['parameters_total_b']=str(p/1e9 if p>1e6 else p); break
        total=safe.get('total')
        if isinstance(total,(int,float)) and total>0:
            out['weight_memory_gb']=str(round(total/1e9,2))
            if not out.get('estimated_memory_gb'):
                out['estimated_memory_gb']=str(round(total/1e9,2))
        for key in ('hidden_size','n_embd','d_model'):
            value=number(config.get(key))
            if value: out['hidden_size']=str(int(value)); break
        for key in ('num_hidden_layers','n_layer','num_layers'):
            value=number(config.get(key))
            if value: out['num_hidden_layers']=str(int(value)); break
        for key in ('num_attention_heads','n_head'):
            value=number(config.get(key))
            if value: out['num_attention_heads']=str(int(value)); break
        for key in ('num_key_value_heads','num_kv_heads'):
            value=number(config.get(key))
            if value: out['num_key_value_heads']=str(int(value)); break
        out['technical_evidence_url']=base
        out['technical_evidence_state']='reported'
        # T1: technical identity and execution context.
        t1=bool(out.get('runtime') and out.get('context_tokens') and (out.get('architecture') or out.get('parameters_total_b')))
        # T2: viability can be evaluated from observed weight size + context + runtime.
        # Quantization is not mandatory when actual weight-file size is observed.
        t2=bool(t1 and out.get('weight_memory_gb'))
        # T3 requires an actual performance observation; this extractor does not manufacture it.
        t3=bool(out.get('tokens_per_second') and out.get('hardware_id') and out.get('runtime'))
        out['technical_profile_level']='T3' if t3 else 'T2' if t2 else 'T1' if t1 else 'T0'
        out['technical_evidence_checked_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    except (HTTPError,URLError,TimeoutError,ValueError,json.JSONDecodeError) as exc:
        out['technical_evidence_state']='unavailable'
        out['technical_profile_level']='T0'
        out['notes']=(out.get('notes','')+f'; technical evidence unavailable: {type(exc).__name__}').strip('; ')
    return out

def main():
    if not FEED.exists(): raise SystemExit(f'Missing {FEED}')
    with FEED.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    fields=list(rows[0].keys()) if rows else []
    for field in EXTRA:
        if field not in fields: fields.append(field)
    enriched=[enrich(row) for row in rows]
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
    with EVIDENCE.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(enriched)
    for i,row in enumerate(enriched):
        for field in EXTRA:
            if row.get(field) and not rows[i].get(field): rows[i][field]=row[field]
    with FEED.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    counts={k:sum(r.get('technical_profile_level')==k for r in enriched) for k in ('T0','T1','T2','T3')}
    reported=sum(r.get('technical_evidence_state')=='reported' for r in enriched)
    print(f"Technical evidence: reported={reported}/{len(enriched)}; T0={counts['T0']} T1={counts['T1']} T2={counts['T2']} T3={counts['T3']}; output={EVIDENCE}")

if __name__=='__main__': main()
