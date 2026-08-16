# H06 — Validación

## Objetivo

Demostrar que la frontera feed → Atlas es repetible, conservadora y compatible con el schema canónico.

## Checks

| Check | Qué demuestra |
|---|---|
| Promotion contract tests | Que identidad, unknown y evidencia se comportan como se espera. |
| Identity audit | Que los candidatos de duplicación/colisión quedan visibles. |
| Quality audit | Que las incidencias de datos se registran sin alterar silenciosamente el dato. |
| Verified-only promotion | Que los registros no verificados no entran en `catalog.json`. |
| JSON Schema validation | Que cada registro canónico cumple `atlas/schema.json`. |
| H06 audit report | Que quedan cuantificados feed, identidades, flags y registros canónicos. |

## Evidencia generada

- `data/prospection/atlas_identity_audit.csv`
- `data/prospection/atlas_quality_flags.csv`
- `data/prospection/atlas_promotion_report.json`
- `data/prospection/h06_audit_report.json`
- `atlas/catalog.json`

## Regla de interpretación

Un workflow verde demuestra que el proceso es válido. No demuestra que todos los modelos estén verificados, que todos tengan benchmarks físicos ni que todas las recomendaciones sean óptimas.

Si el feed tiene cero registros verificables, el resultado correcto es un catálogo canónico vacío y un workflow verde.

## Aceptación

H06 queda lista para aceptación cuando el workflow `H06 Atlas knowledge gate` haya ejecutado correctamente todos los checks y los outputs publicados correspondan a esa ejecución.
