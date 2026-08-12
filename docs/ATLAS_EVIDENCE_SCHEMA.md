# Leones Atlas: evidence schema

La evidencia deja de ser solo una política documental y pasa a formar parte del SQLite de Atlas.

## Tabla `model_evidence`

| Campo | Significado |
|---|---|
| `evidence_id` | identificador interno |
| `model_id` | modelo al que se refiere |
| `source` | procedencia original |
| `evidence_type` | `measured`, `reported`, `estimated`, `calculated`, `anecdotal` |
| `source_type` | tipo de fuente |
| `status` | estado de revisión |
| `reviewer` | persona que revisó, cuando existe |
| `reviewed_at` | fecha de revisión |
| `notes` | contexto y observaciones |

## Regla

Una estimación externa puede almacenarse en Atlas sin convertirse por ello en un hecho validado. Su `status` conserva explícitamente `external-unvalidated` hasta que exista una revisión.

La tabla mantiene la procedencia y el tipo de evidencia incluso después de una promoción a `atlas-evidence`.

## Relación

```text
model_catalog
     │
     └──── model_evidence
             ├── source
             ├── evidence_type
             ├── source_type
             ├── status
             ├── reviewer
             └── reviewed_at
```

Esto permite que Router y las herramientas de análisis consulten no solo un valor, sino también **de dónde procede y qué grado de evidencia representa**.
