# Estado de JALONES — LEONES

**Actualizado: 2026-08-29**

Este documento es el índice operativo de los jalones. Distingue contratos fijados, cierres demostrados y trabajo que todavía requiere integración o ejecución física.

| JALÓN | Estado | Criterio de salida |
|---|---|---|
| JALÓN 1 — CI / #62 / puente | 🟢 CERRADO | Integración y puente benchmark/evidence demostrados. |
| JALÓN 2 — runtime físico | 🟢 CERRADO | Ejecución física reproducible, medición y evidencia real conservadas y validadas. |
| JALÓN 3 — medición real | 🟢 CERRADO — diseño | Contrato y protocolo de medición fijados antes de la ejecución física. |
| JALÓN 4 — adapters / runtime selection V1.1 | 🟢 CERRADO — contrato | Taxonomía y gate declarativo fijados; la ejecución física sigue siendo independiente. |
| JALÓN 5 — segunda oleada | 🟢 CERRADO — integración | Contratos y adapters integrados sin convertir preparación en medición física. |
| JALÓN 6 — ODS / Magnitude | 🟢 CERRADO | Integración mínima, evidencia reportada y puente a `runtime-benchmark.v1` fijados. |
| JALÓN 7 — task results | 🟡 BASE FIJADA | Contrato, implementación mínima, trazabilidad A01 y agregación determinista fijados; queda conectar el resumen con la clasificación/recomendación existente. |

## Regla de cierre

Un jalón se cierra sólo cuando sus criterios de salida están demostrados por código, tests, documentación y/o evidencia apropiada. **La preparación no se presenta como ejecución física.**

En particular, `REPORTED`, estimaciones y perfiles externos no se promocionan automáticamente a `MEASURED`.

## Cadena canónica actual

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

Cada capa conserva su autoridad. ODS/Magnitude aportan perfilado, configuración y evidencia reportada; LEONES mantiene la decisión, clasificación y recomendación final.

## JALÓN 7 — frontera actual

J7 ya tiene una base contractual fijada en `rc1-minimal-script-cleanup`:

- `task-result.v1` validable;
- proyección desde `runtime-benchmark.v1`;
- agregación determinista;
- separación explícita entre `completed`, `failed`, `invalid` y `not_evaluated`;
- trazabilidad A01 → task result → evidencia;
- exclusión de tareas no evaluadas de `benchmark_evidence_ids`.

El siguiente trabajo no debe crear otro benchmark ni otro selector. Debe **consumir el resumen J7 desde la clasificación/recomendación ya existente**.

## Ejecución física

Cuando una etapa requiera host real, el procedimiento será `ejecutar → medir → validar → conservar evidencia`. CI prueba contratos y fixtures; no sustituye la validación física.
