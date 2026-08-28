# Estado de JALONES — LEONES

**Actualizado: 2026-08-27**

Este documento separa explícitamente los jalones cerrados de los que todavía requieren trabajo de ingeniería o ejecución física.

| JALÓN | Estado | Criterio de salida |
|---|---|---|
| JALÓN 1 — CI / #62 / puente | 🟢 CERRADO | Integración V1.1, autorización de runtime y puente benchmark/evidence demostrados por código, CI y documentación. |
| JALÓN 2 — runtime físico / evidencia | 🟢 CERRADO | Cinco ejecuciones físicas de `llama.cpp` conservadas con registros, logs, transcripciones, resumen y manifest SHA-256; bridge y tests específicos validados. |
| JALÓN 3 — contrato de medición real | 🟢 CERRADO — diseño | Contrato y protocolo común fijados; la validación empírica final queda reservada a la primera ejecución física bajo ese contrato. |
| JALÓN 4 — adapters / runtime selection V1.1 | 🟡 ABIERTO | Validación completa de adapters y selección declarativa según su alcance. |
| JALÓN 5 — segunda oleada | 🟡 ABIERTO | Contratos/adapters preparados y validación en los hosts donde cada runtime sea ejecutable. |

## Regla de cierre

Un jalón puede cerrarse cuando sus criterios de salida están demostrados por código, tests, documentación y/o evidencia apropiada. **La preparación no se presenta como ejecución física.**

En particular, JALÓN 2 queda cerrado por la evidencia física ya conservada; JALÓN 3 fija el contrato común para las mediciones posteriores.

```text
JALÓN 1  🟢
   ↓
CI / integración
   ↓
JALÓN 2  🟢
   ↓
runtime físico + evidencia íntegra
   ↓
JALÓN 3  🟢 diseño
   ↓
contrato de medición congelado
   ↓
próxima ejecución física bajo contrato
   ↓
JALÓN 4 / JALÓN 5
```

## Registro histórico

El cierre formal de JALÓN 2 está documentado en [`docs/completed/JALON-2.md`](completed/JALON-2.md) y anclado al commit `947f61e4a65e9a34151999c8f94fd606295009f5`.

La evidencia histórica no debe reescribirse retrospectivamente para acomodar cambios posteriores del contrato o del tooling.
