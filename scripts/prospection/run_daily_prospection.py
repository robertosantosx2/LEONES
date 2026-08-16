#!/usr/bin/env python3
"""Prepara el plan diario de prospección de LEONES.

IMPORTANTE: este script NO es el buscador completo. Su trabajo es construir
un plan reproducible de fuentes y consultas que después utilizarán los
adaptadores de prospección.

Separar planificación de descubrimiento evita confundir:
    fuente registrada → consulta planificada → hallazgo → evidencia → Atlas

La documentación humana está en docs/completed/H04-DAILY-PROSPECTION.md.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# Localizamos la raíz del repositorio desde scripts/prospection/.
ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'scripts/prospection/sources_registry.json'
PLAN = ROOT / 'scripts/prospection/adapters/source_query_plan.json'
OUT = ROOT / 'data/prospection'

# Consultas genéricas por categoría. El plan específico de cada familia se
# combina con estas consultas para aumentar cobertura sin duplicar código.
CATEGORY_QUERIES = {
    'models': [
        'LLM', 'language model', 'vision language model',
        'embedding model', 'reranker', 'multimodal model',
    ],
    'runtimes': [
        'LLM inference', 'inference runtime', 'model serving',
        'local inference', 'quantization',
    ],
    'agents': [
        'AI agent', 'agent framework', 'tool calling',
        'MCP agent', 'autonomous agent',
    ],
    'skills': [
        'AI skill', 'MCP server', 'AI tool', 'agent tool', 'plugin',
    ],
    'harnesses': [
        'evaluation harness', 'benchmark harness', 'agent harness',
        'LLM evaluation', 'agent testing',
    ],
    'hardware': [
        'AI accelerator', 'CPU inference', 'GPU inference',
        'NPU inference', 'AI hardware', 'edge AI',
    ],
}


def load_json(path: Path):
    """Lee un JSON UTF-8 y lo convierte a objetos Python."""
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    """Construye el NDJSON de consultas y el informe de planificación."""
    parser = argparse.ArgumentParser(
        description='Genera el plan diario de consultas de prospección LEONES.'
    )
    parser.add_argument('--registry', default=str(REGISTRY), help='Registro de fuentes.')
    parser.add_argument('--plan', default=str(PLAN), help='Plan de familias y adaptadores.')
    parser.add_argument(
        '--output',
        default=str(OUT / 'source_discovery_plan.ndjson'),
        help='Archivo NDJSON que recibirá las consultas planificadas.',
    )
    args = parser.parse_args()

    # El registro dice qué fuentes conocemos. El plan dice cómo queremos
    # consultarlas. Mantener ambos separados permite auditar la cobertura.
    registry = load_json(Path(args.registry))
    plan = load_json(Path(args.plan))

    sources = {
        item['id']: item
        for item in registry.get('sources', [])
    }
    now = datetime.now(timezone.utc).isoformat()

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    # Recorremos cada familia del plan y cada fuente que la familia declara.
    # Si una fuente no está registrada, la ignoramos: nunca debemos fabricar
    # metadatos de una fuente que el inventario no conoce.
    for family in plan.get('families', []):
        for source_id in family.get('sources', []):
            source = sources.get(source_id)
            if not source:
                continue

            for category, queries in CATEGORY_QUERIES.items():
                # dict.fromkeys conserva el orden y elimina duplicados.
                family_queries = list(dict.fromkeys(
                    family.get('queries', []) + queries
                ))

                for query in family_queries:
                    rows.append({
                        'observed_at': now,
                        'source': source_id,
                        'source_url': source.get('url', ''),
                        'source_kind': source.get('kind', ''),
                        'priority': source.get('priority', 'medium'),
                        'family': family.get('id', ''),
                        'category': category,
                        'adapter': family.get('adapter', ''),
                        'query': query,

                        # Todavía no hemos ejecutado la consulta. Por eso
                        # «planned» es correcto y «discovered» sería falso.
                        'status': 'planned',
                        'license_status': 'unvalidated',
                        'publication_status': 'discovered',

                        # La procedencia permite saber de qué registro salió
                        # cada consulta cuando el archivo se audita más tarde.
                        'provenance': {
                            'registry_id': source_id,
                            'registry_url': source.get('url', ''),
                            'query_plan': family.get('id', ''),
                        },
                    })

    # NDJSON: un objeto JSON por línea. Es cómodo para pipelines porque una
    # línea puede procesarse sin cargar el archivo completo en memoria.
    with destination.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')

    # El informe es deliberadamente pequeño: sirve para saber qué plan se
    # generó sin tener que abrir todo el NDJSON.
    report = OUT / 'daily_source_report.json'
    report.write_text(
        json.dumps(
            {
                'generated_at': now,
                'status': 'planned',
                'sources_in_registry': len(sources),
                'discovery_queries': len(rows),
                'categories': list(CATEGORY_QUERIES),
                'license_policy': 'license_gate_before_publication',
                'note': 'Query planning is separate from live discovery and Atlas publication.',
            },
            ensure_ascii=False,
            indent=2,
        ) + '\n',
        encoding='utf-8',
    )

    print(json.dumps({
        'sources': len(sources),
        'queries': len(rows),
        'output': str(destination),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
