# LLMFit ↔ LEONES

**Perfil:** preselector hardware-aware de modelos.

LLMFit es una herramienta externa que analiza el hardware disponible y estima qué modelos pueden encajar, junto con señales como memoria, velocidad, contexto, cuantización, modo de ejecución y runtime. En LEONES ocupa una posición deliberadamente anterior al benchmark físico.

## Qué aporta LLMFit

- primera reducción del espacio de candidatos;
- estimación de encaje modelo ↔ hardware;
- estimaciones de memoria y velocidad;
- señales de contexto y modo de ejecución;
- indicación del runtime/configuración propuesta;
- ahorro de tiempo y almacenamiento antes de descargar modelos grandes.

## Qué NO aporta

LLMFit **no demuestra** que un modelo funcione en el hardware concreto. Tampoco sustituye Atlas, JGB, CABE/RULA, el benchmark LEONES ni el Router.

La regla es:

```text
LLMFit estima
     ↓
LEONES contrasta
     ↓
LEONES ejecuta
     ↓
LEONES mide
```

Por tanto:

```text
LLMFit claim/recommendation → reported / estimated
LEONES hardware observation → observed
LEONES benchmark            → measured
```

Nunca se promociona automáticamente una estimación de LLMFit a `measured` o `verified`.

## Flujo canónico

```text
HARDWARE + INTENCIÓN DEL USUARIO
             ↓
          LLMFit
             ↓
       TOP-N CANDIDATOS
             ↓
 Atlas + identidad + evidencia + JGB
             ↓
 cuantización + contexto + runtime
             ↓
        CABE / RULA
             ↓
   benchmark LEONES físico
             ↓
          measured
             ↓
     recomendador / Router
```

## Contrato del adaptador

Cuando LEONES consuma LLMFit, debe conservar los valores externos sin mezclarlos con las mediciones propias. Como mínimo, cuando estén disponibles:

- `llmfit_quality_estimate`;
- `llmfit_speed_estimate`;
- `llmfit_fit`;
- `llmfit_context_fit`;
- `llmfit_quantization`;
- `llmfit_run_mode`;
- `llmfit_memory_estimate`;
- `llmfit_runtime`;
- `llmfit_source_version`.

El adaptador debe registrar también la fuente, versión/revisión, fecha de observación y condiciones de hardware que originaron la estimación.

Los valores ausentes permanecen `unknown`/`null`; no se reconstruyen por inferencia.

## Relación con Atlas

Atlas conserva la identidad y la evidencia de los modelos. LLMFit solo aporta una señal de encaje inicial:

```text
LLMFit
  ↓
fit estimate
  ↓
Atlas identity/evidence
  ↓
requirements + runtime
  ↓
benchmark
  ↓
Atlas / Router
```

La recomendación final puede cambiar respecto a LLMFit cuando exista evidencia mejor, otra cuantización, otro runtime o una medición física.

## Relación con hardware y CABE/RULA

LLMFit ayuda a generar una hipótesis inicial de `CABE`, pero no sustituye el cálculo/validación de LEONES. `RULA` requiere además evidencia de utilidad bajo la carga de trabajo relevante.

Un candidato puede ser recomendado por LLMFit y posteriormente quedar descartado por memoria, contexto, runtime, estabilidad o rendimiento medido.

## Verificación física

La ficha de conocimiento [`../../sources/LLMFIT-REAL-HARDWARE-2026-08-20.md`](../../sources/LLMFIT-REAL-HARDWARE-2026-08-20.md) recoge la verificación técnica disponible y debe leerse junto con [`../../sources/LLMFIT.md`](../../sources/LLMFIT.md).

El benchmark físico se documenta en [`../..//completed/BENCHMARK-MEASURED-EVIDENCE.md`](../../completed/BENCHMARK-MEASURED-EVIDENCE.md) y el resultado canónico en [`../../RESULT_SCHEMA.md`](../../RESULT_SCHEMA.md).

## Documentación relacionada

- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) — posición de LLMFit en la arquitectura.
- [`../../phases/2026-08-atlas-recommendation-pipeline/`](../../phases/2026-08-atlas-recommendation-pipeline/) — integración con el recomendador.
- [`../../phases/2026-08-hardware-matrix/`](../../phases/2026-08-hardware-matrix/) — perfiles de hardware.
- [`../../completed/H08-HARDWARE-MATRIX.md`](../../completed/H08-HARDWARE-MATRIX.md) — guía de la matriz.
- [`../../completed/H09-CABE-RULA.md`](../../completed/H09-CABE-RULA.md) — contrato CABE/RULA.
- [`../../RESULT_SCHEMA.md`](../../RESULT_SCHEMA.md) — resultado canónico.
- [`../../integrations/DATA-CONTRACT.md`](../DATA-CONTRACT.md) — contrato de datos de integraciones.
- [`../../integrations/E2E.md`](../E2E.md) — validación E2E.

## Fuente primaria

- LLMFit: https://www.llmfit.org/
- Repositorio de referencia: https://github.com/AlexsJones/llmfit

La fuente externa sigue siendo fuente de conocimiento. Las mediciones de LEONES se conservan separadas.
