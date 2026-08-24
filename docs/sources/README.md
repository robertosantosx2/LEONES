# Fuentes de conocimiento — LEONES

Este directorio contiene fuentes externas y conocimiento derivado convertido en documentación trazable para LEONES. No es un directorio de enlaces: cada ficha debe explicar **qué es**, **qué demuestra**, **qué estima** y **qué ha medido LEONES**.

## Contrato editorial

La norma única del bloque es [`KNOWLEDGE-FICHA-CONTRACT.md`](KNOWLEDGE-FICHA-CONTRACT.md).

El inventario semántico y el estado de homogeneización están en [`KNOWLEDGE-REGISTRY.md`](KNOWLEDGE-REGISTRY.md).

### Las cuatro capas nunca se mezclan

| Capa | Pregunta | Puede alimentar directamente una medición LEONES? |
|---|---|---|
| **Fuente / descubrimiento** | ¿De dónde procede? | No |
| **Evidencia** | ¿Qué está respaldado? | Solo como contexto/hipótesis hasta pasar los gates |
| **Estimación** | ¿Qué predice o recomienda una herramienta externa? | No; requiere validación |
| **Medición LEONES** | ¿Qué ha ejecutado y observado LEONES? | Sí, como evidencia propia reproducible |

Regla permanente:

> **Descubrir no es verificar. Verificar no es estimar. Estimar no es medir. Medir no es aprobar.**

## Pipeline canónico

```text
FUENTE / DESCUBRIMIENTO
      ↓
ANÁLISIS LEONES
      ├──────────────→ EVIDENCIA
      └──────────────→ ESTIMACIÓN / HIPÓTESIS
                              ↓
                     CANDIDATO EJECUTABLE
                              ↓
                    runtime-selection.v1
                              ↓
                         EXECUTOR
                              ↓
                          GRADER
                              ↓
                    BENCHMARK LEONES
                              ↓
                    MEDICIÓN LEONES
                              ↓
                         EVIDENCE
                              ↓
                       ROUTER / ATLAS
```

## Fuentes activas y fichas estratégicas

| Fuente | Documento | Función LEONES | Estado |
|---|---|---|---|
| FreeToken | [`FREETOKEN.md`](FREETOKEN.md) | exploración de selección/runtime | 🟡 `research-candidate` |
| «El otro FreeToken» / Odysseus | [`FREETOKEN-EL-OTRO-FREETOKEN.md`](FREETOKEN-EL-OTRO-FREETOKEN.md) | referencia independiente de workspace/servicio | 🟡 `research-candidate` |
| LLMFit | [`LLMFIT.md`](LLMFIT.md) | preselector hardware-aware | 🟢 `preselector` |
| LLMFit + hardware real | [`LLMFIT-REAL-HARDWARE-2026-08-20.md`](LLMFIT-REAL-HARDWARE-2026-08-20.md) | verificación técnica | 🟢 `verification-leones` |
| AirLLM | [`AIRLLM.md`](AIRLLM.md) | runtime candidato memory-constrained | 🟡 `runtime-candidate` |
| ODS | [`ODS.md`](ODS.md) | despliegue/instalación local | 🟡 `research-candidate` |
| Magnitude | [`MAGNITUDE.md`](MAGNITUDE.md) | agente + inference engine local | 🟡 `research-candidate` |
| Runtimes locales | [`LOCAL-RUNTIMES-2026.md`](LOCAL-RUNTIMES-2026.md) | radar de runtimes | 🟡 `source-inspiration` |
| Infraestructura de inferencia | [`LOCAL-INFERENCE-2026.md`](LOCAL-INFERENCE-2026.md) | prospección | 🟡 `source-inspiration` |
| Candidatos de infraestructura | [`LOCAL-INFERENCE-2026-CANDIDATES.md`](LOCAL-INFERENCE-2026-CANDIDATES.md) | promoción documental | 🟡 `research-candidate` |
| Verificación de infraestructura | [`LOCAL-INFERENCE-2026-VERIFICATION.md`](LOCAL-INFERENCE-2026-VERIFICATION.md) | evidencia primaria por candidato | 🟢 `verified-primary` |
| Artificial Analysis / Optima / benchmarks agentivos | [`ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`](ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md) | metodología y fuentes de evaluación | 🟡 `research-candidate` |
| Buddy Harness | [`BUDDY_HARNESS.md`](BUDDY_HARNESS.md) | referencia de harness/evaluación | 🟡 `harness-reference` |
| Mozilla / ecosistema Open Source AI | [`MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md`](MOZILLA_OPEN_SOURCE_AI_ECOSYSTEM.md) | radar y contexto de descubrimiento | 🟡 `source-inspiration` |

El detalle completo está en `KNOWLEDGE-REGISTRY.md`.

## Qué significa cada estado

- `source-inspiration`: fuente útil para descubrir o contextualizar.
- `research-candidate`: merece estudio/integración, pero no está validado como componente ejecutable.
- `preselector`: herramienta que puede reducir el espacio de candidatos; sus predicciones siguen siendo estimaciones.
- `runtime-candidate`: runtime candidato pendiente de benchmark LEONES.
- `workspace-reference`: referencia de workspace/servicio.
- `harness-reference`: referencia de harness/evaluación.
- `verified-primary`: claims contrastados con fuentes primarias; no equivale a `measured`.
- `measured`: existe medición reproducible LEONES.
- `rejected`: evaluado y descartado para el uso considerado.
- `unresolved`: no existe evidencia suficiente para promocionarlo.

## Independencia de las fuentes

Una fuente puede aportar taxonomías, entidades, proyectos, hipótesis, mecanismos y señales de mercado. No puede alterar por sí sola las clasificaciones congeladas de LEONES ni convertir una estimación externa en medición propia.

### LLMFit

LLMFit actúa como **preselector hardware-aware**. Puede reducir el espacio de modelos candidatos según el hardware disponible. Sus predicciones se almacenan como estimaciones hasta que LEONES las contraste mediante ejecución y benchmark.

### AirLLM

AirLLM actúa como **runtime candidato para escenarios memory-constrained**. Sus claims de memoria y rendimiento se conservan con sus condiciones originales y no pasan a `measured` sin ejecución LEONES.

### ODS

ODS actúa como **capa de despliegue e instalación**. Puede detectar hardware, facilitar la puesta en marcha y seleccionar componentes. LEONES conserva la decisión canónica y la medición.

### Magnitude

Magnitude actúa como **agente + inference engine local**, con perfilado y recomendaciones propias. Es una fuente de hipótesis e integración, no una sustitución del benchmark LEONES.

### FreeToken y «El otro FreeToken» / Odysseus

Se mantienen como fichas independientes. La eventual integración entre ambos es una hipótesis que debe recorrer el pipeline ejecutable y producir evidencia propia.

## Mantenimiento

Ante una nueva fuente o edición:

1. registrar procedencia y versión;
2. ampliar la ficha siguiendo el contrato;
3. clasificar cada claim como fuente, evidencia o estimación;
4. conservar las condiciones experimentales;
5. registrar por separado cualquier medición LEONES;
6. actualizar `KNOWLEDGE-REGISTRY.md`;
7. actualizar la vista web sin alterar la semántica;
8. ejecutar contract-tests/regresiones si afecta al selector, runtime o benchmark.

Una referencia histórica no se elimina por quedar obsoleta: se conserva con estado explícito. Una referencia no resoluble no se promociona por inferencia.
