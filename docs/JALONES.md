# Estado de JALONES — LEONES

**Actualizado: 2026-08-27**

Este documento separa explícitamente lo que ya está cerrado de lo que todavía requiere ejecución física.

| JALÓN | Estado | Criterio de salida |
|---|---|---|
| JALÓN 1 — CI / #62 / puente | 🟢 CERRADO | Integración V1.1, autorización de runtime y puente benchmark/evidence documentados e integrados en `main`. |
| JALÓN 2 — runtime físico | 🟡 ABIERTO | Ejecutar en Debian, medir, validar y conservar evidencia real. |
| JALÓN 3 — medición real | 🟢 CERRADO — diseño | Contrato y protocolo de medición fijados antes de la ejecución física. |
| JALÓN 4 — adapters / runtime selection V1.1 | 🟡 ABIERTO | Validación completa de los adapters y selección declarativa según su alcance. |
| JALÓN 5 — segunda oleada | 🟡 ABIERTO | Contratos/adapters preparados y validación en los hosts donde cada runtime sea ejecutable. |

## Regla de cierre

Un jalón puede cerrarse cuando sus criterios de salida están demostrados por código, tests, documentación y/o evidencia apropiada. **La preparación no se presenta como ejecución física.**

En particular:

```text
JALÓN 1  🟢
   ↓
CI / integración
   ↓
JALÓN 3  🟢
   ↓
protocolo congelado
   ↓
JALÓN 2  🟡
   ↓
Debian
   ↓
ejecutar → medir → validar → conservar evidencia
```

## Siguiente cierre

El siguiente cierre importante será **JALÓN 2**, una vez realizada en Debian la ejecución física y conservada la evidencia correspondiente. No se adelantará ese cierre por tener el runtime preparado.
