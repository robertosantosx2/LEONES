# Registro homogéneo del conocimiento LEONES

Este registro es el índice semántico del bloque `docs/sources/`. Su función es impedir que una ficha mezcle **fuente**, **evidencia**, **estimación** y **medición LEONES**.

## Semántica común

| Campo | Significado |
|---|---|
| Fuente | origen externo y procedencia del conocimiento |
| Evidencia | claim respaldado por fuente primaria/externa o verificación documental |
| Estimación | predicción, recomendación o cálculo externo todavía no medido por LEONES |
| Medición LEONES | resultado obtenido por ejecución reproducible del pipeline LEONES |
| Estado | posición actual del objeto dentro de LEONES |
| Próximo gate | paso necesario para aumentar su nivel de confianza/integración |

## Inventario actual

| Ficha | Capa principal | Papel en LEONES | Fuente | Evidencia | Estimación | Medición LEONES | Estado principal |
|---|---|---|---|---|---|---|---|
| [FREETOKEN.md](FREETOKEN.md) | selección/runtime | candidato MoE edge | primaria | documental + código + resultados publicados | separada | pendiente | `runtime-candidate` |
| [FREETOKEN-EL-OTRO-FREETOKEN.md](FREETOKEN-EL-OTRO-FREETOKEN.md) | runtime/serving | runtime MoE edge-native | primaria | documental + código + claims | sí | pendiente | `runtime-candidate` |
| [ODYSSEUS.md](ODYSSEUS.md) | workspace/harness | workloads agentivos | primaria | documental + verificación | Cookbook externo | pendiente | `workspace-reference` |
| [LLMFIT.md](LLMFIT.md) | preselector | reducción de candidatos por hardware | primaria | código/docs + bench externo | **central** | pendiente | `preselector` |
| [LLMFIT-REAL-HARDWARE-2026-08-20.md](LLMFIT-REAL-HARDWARE-2026-08-20.md) | verificación | calibración futura de estimaciones | observación real | verificación | sí | aún no benchmark | `verification-leones` |
| [AIRLLM.md](AIRLLM.md) | runtime/inferencia | candidato memory-constrained | primaria | documental + código | separada | pendiente | `runtime-candidate` |
| [ODS.md](ODS.md) | despliegue | appliance/stack local | primaria | código/docs/installer | sí | pendiente | `research-candidate` |
| [MAGNITUDE.md](MAGNITUDE.md) | agente/runtime | perfilado + harness agentivo | primaria | código/docs | sí | pendiente | `research-candidate` |
| [LOCAL-RUNTIMES-2026.md](LOCAL-RUNTIMES-2026.md) | radar/runtime | mapa de runtimes | primaria por entrada | consolidada | posible | por runtime | `source-inspiration` |
| [LOCAL-INFERENCE-2026.md](LOCAL-INFERENCE-2026.md) | radar | prospección | descubrimiento | derivada | separada | pendiente | `source-inspiration` |
| [LOCAL-INFERENCE-2026-CANDIDATES.md](LOCAL-INFERENCE-2026-CANDIDATES.md) | candidatos | promoción documental | derivada | quality gate | no equivale a medición | pendiente | `research-candidate` |
| [LOCAL-INFERENCE-2026-VERIFICATION.md](LOCAL-INFERENCE-2026-VERIFICATION.md) | verificación | identidad/estado/licencia | primaria | foco principal | separada | pendiente | `verified-primary` |
| [ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md](ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md) | benchmark/metodología | diseño agentivo | metodológica | externa | no es estimador | pendiente | `research-candidate` |
| [BUDDY_HARNESS.md](BUDDY_HARNESS.md) | harness | workload agentivo | primaria | documental + código | hipótesis | pendiente | `harness-reference` |
| [MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md](MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md) | ecosistema | descubrimiento/contexto | publicación | claims | conceptual | no aplica | `source-inspiration` |
| [LLMS-DE-CERO-A-HEROE-2026.md](LLMS-DE-CERO-A-HEROE-2026.md) | fundamentos | marco técnico | fuente compilada | documental | conceptual | no aplica | `source-inspiration` |
| [KNOWLEDGE-FICHA-CONTRACT.md](KNOWLEDGE-FICHA-CONTRACT.md) | contrato | norma editorial | LEONES | contrato | n/a | n/a | `verified-primary` |
| [KNOWLEDGE-REGISTRY.md](KNOWLEDGE-REGISTRY.md) | registro | índice semántico | LEONES | registro | n/a | n/a | `verified-primary` |
| [KNOWLEDGE-FOUR-LAYER-AUDIT.md](KNOWLEDGE-FOUR-LAYER-AUDIT.md) | auditoría | control de separación | LEONES | auditoría | n/a | n/a | `verified-primary` |
| [KNOWLEDGE-FOUR-LAYER-CARDS.md](KNOWLEDGE-FOUR-LAYER-CARDS.md) | normalización | lectura homogénea de fichas | derivada LEONES | síntesis | separada | n/a | `verified-primary` |

## Regla de lectura

### Fuente

La ficha explica qué existe y enlaza el artefacto original. No implica adopción.

### Evidencia

La ficha identifica qué afirmaciones están respaldadas y bajo qué condiciones. Una evidencia externa sigue siendo externa.

### Estimación

La ficha conserva la predicción de la herramienta y sus supuestos. LLMFit, ODS, Magnitude u otra herramienta pueden aportar señales de este tipo.

### Medición LEONES

Solo se rellena con resultados obtenidos por el ejecutor/benchmark de LEONES y vinculados a evidencia reproducible.

## Regla de promoción

```text
source-inspiration
        ↓
research-candidate
        ↓
verified-primary
        ↓
selector/runtime/workspace/harness candidate
        ↓
runtime-selection.v1
        ↓
executor
        ↓
grader
        ↓
benchmark LEONES
        ↓
measured
```

La promoción no es automática. Un resultado `measured` es una observación reproducible, no una recomendación universal.

## Regla para la web

La web consume `web/data/knowledge.json` y presenta **exactamente cuatro capas**, sin fusionarlas:

1. **Fuente / Descubrimiento** — procedencia.
2. **Evidencia** — respaldo verificable.
3. **Estimación** — predicción/recomendación externa.
4. **Medición LEONES** — resultado producido por el pipeline propio.

La tarjeta web no debe inventar una quinta categoría ni convertir `estado`, `clasificación` o `próximo gate` en una de las cuatro capas. Esos metadatos pueden servir para navegar, pero no deben contaminar el contenido semántico de las cuatro capas.
