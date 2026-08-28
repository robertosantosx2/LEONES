# JALÓN 10 — Contrato de salida y consumo V1

**Estado:** 🟠 CONTRATO FIJADO — EJECUCIÓN PENDIENTE
**Base:** `rc1-minimal-script-cleanup`

## Propósito

JALÓN 10 cierra la última frontera entre la recomendación canónica y su consumo por LEONES. Define una salida estable, verificable y trazable sin crear otro motor de decisión, benchmark o scoring.

Cadena canónica:

`selection → runtime → measurement → evidence → decision → recommendation → output → consumer`

La salida no decide de nuevo. Sólo transporta la recomendación ya validada y sus referencias.

## Contrato

El artefacto `leones-recommendation-output.v1` debe contener:

- `schema`;
- `output_id`;
- `recommendation_ref`;
- `entity`;
- `status`;
- `rationale`;
- `unknowns`;
- `next_action`;
- `decision_ref`;
- `evidence_refs`;
- `trace_ref` opcional;
- `generated_at`.

## Reglas de integridad

1. `recommendation_ref` debe identificar una recomendación existente.
2. `status`, `rationale`, `unknowns` y `next_action` deben conservarse sin reinterpretación.
3. `decision_ref` y `evidence_refs` se transportan, no se recalculan.
4. `trace_ref`, si existe, sólo aporta trazabilidad.
5. La salida no puede contener `score`, `ranking_score`, TPS estimado ni métricas derivadas nuevas.
6. El consumidor no puede convertir una salida `watch`, `reject` o `verify_first` en `recommend` sin una nueva decisión canónica.
7. La publicación de salida debe ser determinista para una misma recomendación.

## Criterio de cierre declarativo

Schema, productor/validador, tests y runner deben demostrar que la salida es un transporte fiel de la recomendación y que no existe una segunda capa de decisión.

La ejecución real de consumo se conservará como evidencia independiente cuando se realice.

**Frase de recuperación:**

> JALÓN 10 = transportar la recomendación canónica hasta el consumidor sin reinterpretar decisión, evidencia ni scoring.
