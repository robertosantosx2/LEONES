# JALÓN 7 — Resultados de tareas y frontera de clasificación

**Estado:** 🟡 BASE CONTRACTUAL FIJADA — CONEXIÓN A CLASIFICACIÓN/RECOMENDACIÓN PENDIENTE
**Base canónica:** `main` (`31b6879`)

## 1. Propósito

JALÓN 7 convierte una ejecución ya medida y validada en un resultado de tarea auditable, sin crear otro benchmark, otro selector ni otra fuente de verdad.

```text
runtime-benchmark.v1
        ↓
   task-result.v1
        ↓
 agregación determinista
        ↓
clasificación / recomendación existente
```

La finalidad no es medir tokens/segundo de nuevo. La finalidad es representar **qué tarea se completó, falló, quedó inválida o no fue evaluada**, conservando la procedencia de la ejecución y de la evidencia.

## 2. Componentes canónicos

- `scripts/task_result.py`
- `schemas/task-result.v1.json` cuando corresponda al contrato publicado
- `tests/contracts/test_jalon7_task_result.py`
- proyección desde `runtime-benchmark.v1`
- agregación determinista `task-set-summary.v1`

La implementación existente valida como mínimo:

- identidad de tarea, ejecución, modelo y runtime;
- `completion_status` en `completed`, `failed`, `invalid` o `not_evaluated`;
- estado de medición;
- procedencia obligatoria;
- evidencia para tareas completadas;
- `completion_score` sólo cuando exista y esté acotado a `[0,1]`.

## 3. Regla de procedencia

Un `task-result.v1` es una **proyección** de una evidencia de runtime existente. No puede fabricar identidad de ejecución ni convertir una estimación en medición.

Para una tarea `completed`, debe existir `benchmark_evidence_id`. Las tareas `not_evaluated` no se promocionan a evidencia de benchmark.

La agregación conserva los cuatro estados y sólo considera `completed` y `failed` como tareas evaluadas.

## 4. Frontera con clasificación y recomendación

JALÓN 7 no debe crear un nuevo sistema de clasificación ni un nuevo ranking de modelos.

La siguiente pieza debe consumir `task-set-summary.v1` desde la clasificación/recomendación ya existente y utilizar sus estados y evidencia como entrada auditable.

En particular:

- no se añade otro selector;
- no se añade otro benchmark de rendimiento;
- no se calcula un `ranking_score` paralelo;
- no se mezcla `estimated_tps` con `measured_tps`;
- no se convierte automáticamente una tasa de finalización en una nueva autoridad de selección.

La recomendación continúa siendo responsabilidad del contrato canónico de LEONES; JALÓN 7 aporta evidencia de ejecución de tareas para esa decisión.

## 5. Criterio de cierre

El contrato base de JALÓN 7 está fijado cuando:

1. `task-result.v1` es validable;
2. existe proyección desde `runtime-benchmark.v1`;
3. la agregación es determinista;
4. los cuatro estados de tarea se conservan explícitamente;
5. la trazabilidad `A01 → task result → evidencia` es comprobable;
6. las tareas no evaluadas quedan fuera de `benchmark_evidence_ids`.

Queda como siguiente trabajo conectar el resumen J7 con la clasificación/recomendación existente, **sin crear una arquitectura paralela**.

## 6. Frase de recuperación

> **JALÓN 7 = ejecución medida → resultado de tarea → agregación determinista → clasificación/recomendación existente.**
