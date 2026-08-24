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
| [FREETOKEN.md](FREETOKEN.md) | selección/runtime | candidato para exploración de selección/runtime | primaria | documental + código | pendiente de separar por claim | pendiente | `research-candidate` |
| [FREETOKEN-EL-OTRO-FREETOKEN.md](FREETOKEN-EL-OTRO-FREETOKEN.md) | workspace/servicio | referencia independiente que debe evaluarse junto a Odysseus sin fusionar capas | primaria | documental + código | según claims de la ficha | pendiente | `research-candidate` |
| [LLMFIT.md](LLMFIT.md) | preselector | reducir espacio de candidatos según hardware | primaria | documental + código | **sí, función central** | pendiente/casos existentes separados | `preselector` |
| [LLMFIT-REAL-HARDWARE-2026-08-20.md](LLMFIT-REAL-HARDWARE-2026-08-20.md) | evidencia técnica | contrastar claims de LLMFit con hardware real | primaria + observación | verificación documental | sí, como referencia | solo si existe ejecución LEONES registrada | `verification-leones` |
| [AIRLLM.md](AIRLLM.md) | runtime/inferencia | candidato memory-constrained | primaria | documental + código | claims de memoria/rendimiento separados | pendiente de benchmark canónico | `runtime-candidate` |
| [ODS.md](ODS.md) | despliegue | instalación/detección/selección de stack local | primaria | documental + código | sí | pendiente | `research-candidate` |
| [MAGNITUDE.md](MAGNITUDE.md) | agente/runtime | perfilado, recomendación y ejecución agentiva local | primaria | documental + código | sí | pendiente | `research-candidate` |
| [LOCAL-RUNTIMES-2026.md](LOCAL-RUNTIMES-2026.md) | radar/runtime | mapa de runtimes locales | primaria + secundaria según entrada | consolidada por proyecto | puede contener estimaciones externas | pendiente por runtime | `source-inspiration` |
| [LOCAL-INFERENCE-2026.md](LOCAL-INFERENCE-2026.md) | radar | prospección de infraestructura de inferencia | fuente de descubrimiento | verificación en derivados | claims externos separados | pendiente | `source-inspiration` |
| [LOCAL-INFERENCE-2026-CANDIDATES.md](LOCAL-INFERENCE-2026-CANDIDATES.md) | candidatos | promoción de candidatos tras prospección | derivada | estado de verificación por candidato | no equivale a medición | pendiente | `research-candidate` |
| [LOCAL-INFERENCE-2026-VERIFICATION.md](LOCAL-INFERENCE-2026-VERIFICATION.md) | verificación | comprobación uno a uno de candidatos | primaria/externa según candidato | **sí, foco principal** | separada | pendiente salvo benchmark LEONES explícito | `verified-primary` |
| [ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md](ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md) | benchmark/metodología | fuente para evaluación de agentes/modelos | primaria + externa | resultados publicados | no confundir con score LEONES | pendiente de reproducción | `research-candidate` |
| [BUDDY_HARNESS.md](BUDDY_HARNESS.md) | harness | referencia para ejecución/evaluación | primaria | documental + código | según claims | pendiente | `harness-reference` |
| [MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md](MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md) | radar/metodología | fuente de descubrimiento y contexto del ecosistema | primaria/edición publicada | claims de la fuente | no convertir rankings/estimaciones en medición | pendiente | `source-inspiration` |
| [KNOWLEDGE-FICHA-CONTRACT.md](KNOWLEDGE-FICHA-CONTRACT.md) | contrato | norma editorial y de trazabilidad | LEONES | contrato | n/a | n/a | `verified-primary` |

> Si aparece una ficha adicional en `docs/sources/`, debe incorporarse a este registro antes de considerarla parte del conocimiento consolidado.

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

La web debe presentar las fichas como **conocimiento navegable**, no como un listado plano. La tarjeta y la página ampliada deben conservar las mismas cuatro etiquetas semánticas:

- **Fuente**
- **Evidencia**
- **Estimación**
- **Medición LEONES**

Cuando una de las cuatro no exista, se debe decir explícitamente `no disponible` o `pendiente`, nunca rellenarla por inferencia.
