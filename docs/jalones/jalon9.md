# JALÓN 9 — Contrato operativo de recomendación V1

**Estado:** 🟠 CONTRATO FIJADO — EJECUCIÓN PENDIENTE
**Base:** `rc1-minimal-script-cleanup`

## Propósito

JALÓN 9 convierte la cadena ya construida en una recomendación operativa reproducible. No crea un benchmark, un selector, un scoring engine ni una fuente de verdad paralela.

La recomendación se limita a sintetizar referencias canónicas ya validadas:

`decision → evidence/publication → recommendation`

Cuando exista traza E2E, la recomendación puede quedar enlazada a ella mediante `trace_ref`.

## Autoridad

- La **decisión** procede del contrato ODS/Magnitude ya fijado.
- La **evidencia medida** procede de `runtime-benchmark-evidence.v1.1` y de la cadena de validación/promoción/publicación.
- LLMFit y ODS/Magnitude siguen siendo señales externas con su naturaleza declarada; no se convierten en mediciones locales por aparecer en una recomendación.
- JALÓN 9 no recalcula rendimiento ni introduce una puntuación propia.

## Contrato

El artefacto `leones-recommendation.v1` debe identificar:

- `recommendation_id`;
- `entity`;
- `decision_ref`;
- `evidence_refs`;
- `status`;
- `rationale`;
- `unknowns`;
- `next_action`;
- `trace_ref` opcional.

Los estados son `recommend`, `watch`, `reject` y `verify_first`.

## Reglas de integridad

1. Una recomendación debe apuntar a una decisión existente.
2. Una recomendación no puede afirmar evidencia medida si no referencia evidencia.
3. `recommend` exige que el gate de evidencia mínimo esté satisfecho.
4. `verify_first` y `watch` deben conservar los desconocidos que justifican no recomendar.
5. `reject` no necesita evidencia medida, pero debe conservar una razón explícita.
6. La recomendación no contiene ni calcula `score`, `tokens_per_second` estimados ni otra métrica paralela.
7. `trace_ref`, si existe, sólo enlaza la trazabilidad E2E; no sustituye las referencias de decisión/evidencia.

## Criterio de cierre declarativo

JALÓN 9 queda cerrado declarativamente cuando el schema, validador, tests y runner demuestren estas invariantes. La ejecución real de una recomendación se conserva sólo cuando exista una operación real que la produzca.

**Frase de recuperación:**

> JALÓN 9 = recomendar sólo sintetizando decisión y evidencia canónicas, sin inventar otra capa de medición o scoring.
