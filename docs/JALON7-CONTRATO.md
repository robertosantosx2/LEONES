# JALÓN 7 — CONTRATO OPERATIVO DE TAREAS

## Estado

**BASE FIJADA — implementación mínima validada; cierre funcional pendiente.**

JALÓN 7 convierte la medición de ejecución en un resultado de trabajo verificable: qué tarea se ejecutó, sobre qué modelo/runtime/hardware, con qué evidencia y si la tarea se completó según un criterio explícito.

## Frontera

J7 consume, no reemplaza, las capas cerradas en J1–J6. La frontera canónica sigue siendo `runtime-benchmark.v1` para la medición de ejecución.

```text
selección
  → preflight
  → ejecución
  → medición
  → runtime-benchmark.v1
  → task-result.v1
  → agregación
  → clasificación
  → recomendación
```

## Principio fundamental

`tok/s`, latencia, memoria u otras métricas de ejecución son **medidas instrumentales**. No equivalen por sí mismas a utilidad.

La utilidad de J7 se expresa mediante tareas completadas bajo un protocolo reproducible.

## Contrato mínimo `task-result.v1`

Cada resultado de tarea conserva, como mínimo:

- `schema_version`: `task-result.v1`.
- `task_id`: identificador estable de la tarea.
- `task_suite`: conjunto/version de tareas.
- `task_revision`: revisión del criterio o definición de la tarea.
- `execution_id`: vínculo con la ejecución física o reproducible.
- `benchmark_evidence_id`: vínculo con `runtime-benchmark.v1` cuando exista.
- `model_id` y revisión del modelo.
- `runtime` y versión.
- `hardware` identificado de forma suficiente para reproducibilidad.
- `workload` y configuración relevante.
- `completion_status`: `completed`, `failed`, `invalid` o `not_evaluated`.
- `completion_score`: valor normalizado de cumplimiento cuando la tarea lo permita.
- `measurement_status`: estado de la evidencia que sustenta el resultado.
- `provenance`: origen y referencias de los datos utilizados.

## Reglas de validez

1. Una tarea sólo puede marcarse `completed` si su criterio de éxito está definido y satisfecho.
2. Una estimación externa no puede producir por sí sola `completion_status=completed` medido.
3. Un resultado de tarea debe poder rastrearse hasta su ejecución y, cuando proceda, hasta `runtime-benchmark.v1`.
4. Un resultado sin evidencia suficiente debe quedar explícitamente `invalid` o `not_evaluated`, nunca rellenarse por inferencia.
5. La agregación de tareas es determinista y conserva los resultados individuales.
6. ODS/Magnitude pueden aportar configuración, perfilado o evidencia reportada, pero no adquieren autoridad para declarar la recomendación final de LEONES.

## Agregación

J7 calcula, sobre un conjunto definido:

`completed_tasks / evaluated_tasks`

La agregación no sustituye las métricas instrumentales; las complementa. Una recomendación debe poder explicar tanto **qué tareas se completaron** como **con qué comportamiento de ejecución**.

Los identificadores de `runtime-benchmark.v1` se conservan sólo para resultados válidos y evaluados (`completed` o `failed`). Una tarea `not_evaluated` no contamina la lista de evidencia de benchmark.

## No alcance

- No crear un benchmark de hardware paralelo.
- No duplicar `runtime-selection.v1`.
- No duplicar `runtime-benchmark.v1`.
- No convertir `REPORTED` en `MEASURED`.
- No declarar rendimiento físico sin ejecución física.
- No diseñar todavía tiers de hardware independientes de la evidencia.

## Cierre de J7

La base contractual y su implementación mínima están fijadas y cubiertas por tests. Para cerrar J7 falta únicamente demostrar el consumo del resumen `task-result.v1` por la **clasificación/recomendación existente**, sin introducir un clasificador ni un recomendador paralelo.

La validación física de suites que necesiten hardware real queda fuera de CI y se ejecutará sólo cuando el host sea imprescindible.
