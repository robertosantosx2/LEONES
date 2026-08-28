# JALÓN 7 — DISEÑO MÍNIMO DE IMPLEMENTACIÓN

J7 no introduce un nuevo motor de benchmark. Añade una capa fina de interpretación de resultados de tarea sobre la evidencia de ejecución ya existente.

## Estado

**BASE FIJADA.** La implementación mínima está validada; queda únicamente el seam de consumo por la clasificación/recomendación existente.

## Flujo

`runtime-benchmark.v1 → task-result.v1 → task-set summary → clasificación → recomendación`

## Separación de responsabilidades

| Capa | Autoridad |
|---|---|
| Selección | LEONES |
| Perfilado externo | ODS / Magnitude |
| Preflight / runtime | LEONES + adapters |
| Medición | runtime / harness |
| Evidencia de ejecución | `runtime-benchmark.v1` |
| Resultado de tarea | `task-result.v1` |
| Agregación | LEONES |
| Clasificación | LEONES |
| Recomendación | LEONES |

## Implementación mínima fijada

La implementación proporciona las operaciones necesarias para:

1. **validar** un `task-result.v1` sin inventar campos ni resultados;
2. **agregar** resultados de una suite de tareas de forma determinista;
3. **proyectar** un `runtime-benchmark.v1` válido a `task-result.v1` conservando procedencia.

No ejecuta runtimes ni descarga modelos.

El siguiente paso es un adaptador de consumo hacia la clasificación/recomendación ya existente. No se crea un cuarto sistema de decisión.

## Semántica de estados

- `completed`: criterio de éxito satisfecho y evidencia válida.
- `failed`: la tarea fue evaluada pero no satisfizo el criterio.
- `invalid`: existe un problema de protocolo/evidencia que impide interpretar el resultado.
- `not_evaluated`: no se ejecutó o no existe evidencia suficiente para evaluarla.

Sólo `completed` cuenta como tarea completada. `failed`, `invalid` y `not_evaluated` no se convierten en éxito por inferencia.

## Métricas

El resumen conserva al menos:

- tareas evaluadas;
- tareas completadas;
- tareas fallidas;
- tareas inválidas;
- tareas no evaluadas;
- tasa de completitud sobre tareas evaluadas;
- identificadores de los resultados fuente;
- identificadores de evidencia sólo para resultados válidos y evaluados.

Las métricas de runtime (`tok/s`, latencia, memoria, etc.) permanecen como evidencia instrumental y no se mezclan con la tasa de tareas completadas.

## Regla de recomendación

Una recomendación basada en tareas debe poder responder simultáneamente:

1. qué tareas se evaluaron;
2. cuáles se completaron;
3. qué evidencia de ejecución las sustenta;
4. qué runtime/modelo/hardware se utilizó;
5. qué parte procede de evidencia `MEASURED` y cuál de `REPORTED` o estimaciones.

## Criterio de no-regresión

J7 no puede modificar la semántica de `runtime-selection.v1`, `runtime-benchmark.v1` ni la promoción de evidencia existente. Los tests previos deben seguir pasando íntegramente.

## Fase física

La suite real no se ejecutará durante el desarrollo contractual si requiere hardware externo. Primero se implementa y prueba el contrato con fixtures sintéticos explícitos. La ejecución física posterior sólo genera resultados válidos cuando se respeten el protocolo y la procedencia definidos.
