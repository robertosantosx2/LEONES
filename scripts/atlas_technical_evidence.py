#!/usr/bin/env python3
"""Enrich Atlas model records with conservative technical evidence.

The script only writes values backed by an external technical source. It is
intentionally conservative: missing evidence remains missing. Hugging Face
model metadata/config are currently supported because they provide a stable,
structured source for architecture, parameter-count and context evidence.
"""
from __future__ import annotations
import csv, json, re, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'data/prospection/atlas_feed.csv'
EVIDENCE = ROOT / 'data/prospection/atlas_technical_evidence.csv'

TIMEOUT = 15
UA = 'LEONES-Atlas/1.0 (+https://github.com/robertosantosx2/LEONES)'

EXTRA_FIELDS = [
    'parameters_total_b', 'parameters_active_b', 'architecture',
    'context_tokens', 'runtime', 'runtime_version', 'backend',
    'quantization', 'estimated_memory_gb', 'technical_evidence_url',
    'technical_evidence_state', 'technical_evidence_checked_at'
]


def get_json(url: str):
    req = Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def hf_model_id(row: dict) -> str:
    url = (row.get('repository_url') or row.get('source_url') or '').strip()
    m = re.match(r'https?://huggingface\.co/([^/?#]+/[^/?#]+)', url)
    return m.group(1) if m else ''


def first_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r'(\d+(?:\.\d+)?)', value)
        return float(m.group(1)) if m else None
    return None


def infer_quantization(config: dict, model_id: str) -> str:
    text = ' '.join(str(config.get(k, '')) for k in ('quantization_config', 'quantization', 'torch_dtype')).lower()
    text += ' ' + model_id.lower()
    for q in ('gptq', 'awq', 'gguf', 'int4', '4bit', 'int8', '8bit', 'fp8', 'bf16', 'bfloat16', 'fp16', 'float16'):
        if q in text:
            return {'4bit': 'int4', '8bit': 'int8', 'bfloat16': 'bf16', 'float16': 'fp16'}.get(q, q)
    return ''


def estimate_memory(params_b: float | None, quant: str) -> float | None:
    if params_b is None or not quant:
        return None
    bits = {'int4': 4, '4bit': 4, 'gptq': 4, 'awq': 4, 'int8': 8, '8bit': 8, 'fp8': 8, 'bf16': 16, 'fp16': 16, 'float16': 16}.get(quant.lower())
    if bits is None:
        return None
    # Weights only. Runtime/KV overhead is deliberately not included here.
    return round(params_b * (bits / 8.0) * 1.10, 2)


def enrich(row: dict) -> dict:
    out = dict(row)
    model_id = hf_model_id(row)
    if not model_id:
        return out
    base = f'https://huggingface.co/{model_id}'
    try:
        info = get_json(f'https://huggingface.co/api/models/{model_id}')
        config = info.get('config') or {}
        safetensors = info.get('safetensors') or {}
        params = None
        total = safetensors.get('total')
        if isinstance(total, (int, float)):
            params = float(total) / 1e9
            # total is bytes, not parameter count; only use it as a fallback for
            # memory if it is explicitly a weight-size measurement.
        architecture = ''
        archs = config.get('architectures') or []
        if archs:
            architecture = str(archs[0])
        if architecture:
            out['architecture'] = architecture
        context = None
        for key in ('max_position_embeddings', 'max_sequence_length', 'model_max_length'):
            context = first_number(config.get(key))
            if context:
                break
        if context:
            out['context_tokens'] = str(int(context))
        quant = infer_quantization(config, model_id)
        if quant:
            out['quantization'] = quant
        # HF Transformers is an evidence-backed execution route for model
        # repositories exposing a standard Transformers config.
        if config:
            out['runtime'] = out.get('runtime') or 'transformers'
            out['backend'] = out.get('backend') or 'pytorch'
        # Parameter count is taken only from explicit API metadata when present.
        card_data = info.get('cardData') or {}
        for key in ('parameters', 'parameter_count', 'num_parameters'):
            p = first_number(card_data.get(key))
            if p:
                out['parameters_total_b'] = str(p / 1e9 if p > 1e6 else p)
                break
        if not out.get('parameters_total_b') and isinstance(info.get('pipeline_tag'), str):
            # Do not infer parameter count from pipeline metadata.
            pass
        mem = estimate_memory(first_number(out.get('parameters_total_b')), out.get('quantization', ''))
        if mem is not None:
            out['estimated_memory_gb'] = str(mem)
        out['technical_evidence_url'] = base
        out['technical_evidence_state'] = 'reported'
        out['technical_evidence_checked_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        return out
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        out['technical_evidence_state'] = 'unavailable'
        out['notes'] = (out.get('notes', '') + f'; technical evidence unavailable: {type(exc).__name__}').strip('; ')
        return out


def main():
    if not FEED.exists():
        raise SystemExit(f'Missing {FEED}')
    with FEED.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys()) if rows else []
    for field in EXTRA_FIELDS:
        if field not in fields:
            fields.append(field)
    enriched = [enrich(row) for row in rows]
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(enriched)
    # Feed is deliberately updated only with evidence values; empty values do
    # not overwrite previously known values.
    for row in enriched:
        for field in EXTRA_FIELDS:
            if row.get(field) and not rows[enriched.index(row)].get(field):
                rows[enriched.index(row)][field] = row[field]
    with FEED.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    usable = sum(1 for r in enriched if r.get('technical_evidence_state') == 'reported')
    print(f'Technical evidence: {usable}/{len(enriched)} records enriched; output={EVIDENCE}')

if __name__ == '__main__':
    main()
