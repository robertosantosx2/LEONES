# JALÓN 7 — Publicación controlada de evidencia medida

**Estado:** 🟠 CONTRATO FIJADO — EJECUCIÓN PENDIENTE
**Base:** `rc1-minimal-script-cleanup`

## 1. Propósito

JALÓN 7 cierra la frontera entre una medición real ya validada y su incorporación controlada al almacén empírico reutilizable de LEONES.

`JALÓN 3 → validate_measured_benchmark → promote_measured_benchmark → publish_measured_benchmark → Atlas`

No ejecuta modelos, no calcula benchmarks y no convierte estimaciones en mediciones.

## 2. Autoridad

La evidencia física validada conserva su procedencia. La publicación es un paso explícito y posterior a la validación.

- `measured` es la única clase publicable por este flujo.
- La identidad de modelo, hardware y runtime debe estar presente.
- `tokens_per_second` debe ser numérico y no negativo.
- La promoción puede enriquecer el registro, pero no debe cambiar su naturaleza.
- El publicador añade evidencia; no borra ni sustituye registros anteriores.

## 3. Componentes canónicos

- `scripts/validate_measured_benchmark.py`
- `scripts/promote_measured_benchmark.py`
- `scripts/publish_measured_benchmark.py`
- `scripts/runtime_feedback_atlas.py`
- tests existentes de validación, promoción y publicación.

No se crea un segundo almacén de verdad ni un segundo benchmark.

## 4. Contrato operativo mínimo

1. Recibir una medición producida por runtime real.
2. Validar identidad y `measurement_type=measured`.
3. Enriquecer sin fabricar rendimiento.
4. Publicar como registro JSONL independiente.
5. Conservar procedencia y marcas de evidencia cuando existan.
6. Permitir revisión posterior antes de cualquier incorporación adicional a Atlas.

## 5. Criterio de cierre

El cierre declarativo requiere que el runner compruebe el contrato y que las pruebas de validación/promoción/publicación pasen. La publicación de una medición física nueva en el entorno objetivo sigue siendo una operación explícita cuando corresponda.

**Frase de recuperación:**

> JALÓN 7 = medición validada → promoción explícita → publicación reproducible, sin fabricar evidencia.
