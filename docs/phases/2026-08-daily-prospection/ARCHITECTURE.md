# Arquitectura — Prospección diaria

## Flujo operativo

```text
GitHub / Hugging Face / fuentes especializadas
                    ↓
             adaptadores/fuentes
                    ↓
              descubrimiento
                    ↓
             normalización
                    ↓
          clasificación de licencia
                    ↓
             enriquecimiento
                    ↓
              revisión/evidencia
                    ↓
             Atlas / artefactos
                    ↓
                 web
```

## Separación de responsabilidades

| Capa | Función |
|---|---|
| `scripts/prospection/adapters/` | acceso a fuentes y forjas |
| `classifier.py` | clasificación de candidatos |
| `enrich_sources.py` / `enrich_github.py` | enriquecimiento |
| `merge_discoveries.py` | consolidación |
| `daily_report.py` | informe diario |
| `run_daily_prospection.py` | orquestación |
| `.github/workflows/daily-prospection.yml` | ejecución automática |
| `web/data/prospeccion.json` | salida consumida por la web |

## Estados conceptuales

```text
candidate
   ↓
OSI-approved
   ↓
external-unvalidated
   ↓
review
   ↓
evidence
   ↓
Atlas
```

Un candidato puede detenerse en cualquier punto. El sistema no debe interpretar la mera existencia de una fila como validación.

## Principio de robustez

La prospección debe tolerar el fallo de una fuente sin convertir el fallo de un adaptador en la pérdida del resto del ciclo. Las fuentes y adaptadores se mantienen desacoplados para permitir sustitución y ampliación.
