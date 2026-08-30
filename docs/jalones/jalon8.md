# JALÓN 8 — Trazabilidad E2E del ciclo de evidencia

**Estado:** 🟠 CONTRATO FIJADO — EJECUCIÓN PENDIENTE
**Base:** `rc1-minimal-script-cleanup`

## Propósito

JALÓN 8 fija un único sobre de trazabilidad para conectar los contratos ya construidos sin crear otro selector, benchmark, scoring engine ni almacén de verdad.

`hardware → selection → runtime → execution → measurement → evidence → decision → validation → promotion → publication → recommendation`

El contrato describe el ciclo; no ejecuta modelos ni fabrica resultados.

## Autoridad

Cada etapa conserva su propio artefacto y procedencia mediante `ref`. La traza sólo enlaza referencias existentes. Una etapa `complete` exige referencia.

Los estados de traza son:

- `planned`: preparación sin afirmar medición.
- `measured`: ejecución, medición y evidencia local ya completadas.
- `published`: además de lo anterior, validación, promoción y publicación completadas.

## Componentes canónicos

- `schemas/leones-e2e-trace.v1.json`
- `scripts/validate_e2e_trace.py`
- `tests/test_validate_e2e_trace.py`
- `scripts/run_jalon8_audit.sh`

## Reglas

1. El sobre no duplica la lógica de selección ni de benchmark.
2. El orden de las etapas es contractual.
3. Las etapas completadas deben apuntar a una referencia identificable.
4. `measured` requiere `execution`, `measurement` y `evidence`.
5. `published` requiere además `validation`, `promotion` y `publication`.
6. La recomendación sigue dependiendo de los gates y de la evidencia que corresponda.
7. La traza no convierte estimaciones externas en mediciones.

## Criterio de cierre declarativo

El runner debe comprobar contrato, validación e invariantes. La traza de una ejecución física completa se generará cuando exista una nueva operación E2E que deba conservarse; no se inventa para cerrar el jalón.

**Frase de recuperación:**

> JALÓN 8 = un único hilo de trazabilidad desde hardware hasta recomendación, reutilizando todos los contratos anteriores.
