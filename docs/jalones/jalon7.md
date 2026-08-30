# JALÓN 7 — Resultados de tareas y frontera de clasificación

**Estado:** 🟢 CERRADO — PUENTE MÍNIMO A RECOMENDACIÓN EXISTENTE
**Base canónica:** `main`

## 1. Propósito

JALÓN 7 convierte una ejecución ya medida y validada en un resultado de tarea auditable, sin crear otro benchmark, otro selector ni otra fuente de verdad.

```text
runtime-benchmark.v1
        ↓
   task-result.v1
        ↓
 agregación determinista
        ↓
 task summary provenance
        ↓
clasificación / recomendación existente
```

La finalidad no es medir tokens/segundo de nuevo. La finalidad es representar qué tarea se completó, falló, quedó inválida o no fue evaluada, conservando la procedencia de la ejecución y de la evidencia.

## 2. Componentes canónicos

- `scripts/task_result.py`
- `scripts/jalon9_recommend.py`
- `schemas/task-result.v1.json`
- `schemas/leones-recommendation.v1.json`
- `tests/contracts/test_jalon7_task_result.py`
- `tests/test_jalon9_recommendation.py`
- proyección desde `runtime-benchmark.v1`
- agregación determinista `task-set-summary.v1`

La implementación valida identidad de tarea, ejecución, modelo y runtime; los cuatro estados; medición; procedencia; evidencia para tareas completadas; y `completion_score` sólo cuando existe y está acotado a `[0,1]`.

## 3. Regla de procedencia

Un `task-result.v1` es una **proyección** de una evidencia de runtime existente. No puede fabricar identidad de ejecución ni convertir una estimación en medición.

Para una tarea `completed`, debe existir `benchmark_evidence_id`. Las tareas `not_evaluated` no se promocionan a evidencia de benchmark. La agregación conserva los cuatro estados y sólo considera `completed` y `failed` como tareas evaluadas.

## 4. Puente mínimo a recomendación

La recomendación canónica puede recibir `task_summary_ref`, una referencia al `task-set-summary.v1` ya agregado.

El puente:

1. valida la estructura mínima del resumen;
2. conserva su referencia de procedencia;
3. no modifica `status`;
4. no modifica `next_action`;
5. no crea puntuación ni ranking;
6. no convierte `completion_rate` en autoridad de selección.

Por tanto, el resumen de tareas es **contexto auditable para la recomendación**, no un selector paralelo.

## 5. Prohibiciones

- no se añade otro selector;
- no se añade otro benchmark de rendimiento;
- no se calcula un `ranking_score` paralelo;
- no se mezcla `estimated_tps` con `measured_tps`;
- no se convierte automáticamente una tasa de finalización en una nueva autoridad de selección.

La recomendación continúa siendo responsabilidad del contrato canónico de LEONES; JALÓN 7 aporta evidencia y contexto de ejecución de tareas para esa decisión.

## 6. Criterio de cierre

JALÓN 7 queda cerrado cuando:

1. `task-result.v1` es validable;
2. existe proyección desde `runtime-benchmark.v1`;
3. la agregación es determinista;
4. los cuatro estados de tarea se conservan explícitamente;
5. la trazabilidad `A01 → task result → evidencia` es comprobable;
6. las tareas no evaluadas quedan fuera de `benchmark_evidence_ids`;
7. `task-set-summary.v1` puede entrar en la recomendación existente como referencia auditable sin cambiar su semántica.

## 7. Frase de recuperación

> **JALÓN 7 = ejecución medida → resultado de tarea → agregación determinista → contexto auditable → clasificación/recomendación existente.**
