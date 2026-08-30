# JALÓN 11 — Operación E2E canónica V1

**Estado:** 🟠 CONTRATO FIJADO — EJECUCIÓN REAL PENDIENTE
**Base:** `rc1-minimal-script-cleanup`

## Propósito

JALÓN 11 convierte los contratos cerrados en una única ruta operativa de extremo a extremo. No crea otro selector, benchmark, scoring ni sistema de evidencia.

La ruta canónica es:

`selection → runtime → execution → measurement → evidence → decision → recommendation → publication → output → trace`

Cada etapa conserva la identidad de la etapa anterior y referencia su evidencia o decisión. El orquestador sólo encadena contratos existentes.

## Qué significa «operativo»

Una operación E2E es válida cuando puede demostrar, con referencias explícitas, qué selección entró, qué runtime fue autorizado, qué ejecución ocurrió, qué medición produjo evidencia, qué decisión consumió esa evidencia y qué recomendación terminó siendo publicada y presentada.

La prueba declarativa de este jalón puede ejecutarse sin hardware. La ejecución física seguirá siendo una evidencia independiente y sólo se afirma cuando el runtime haya corrido realmente.

## Contrato `leones-e2e-operation.v1`

El artefacto debe contener:

- `schema`;
- `operation_id`;
- `selection_ref`;
- `runtime_ref`;
- `execution_ref`;
- `measurement_ref`;
- `evidence_refs`;
- `decision_ref`;
- `recommendation_ref`;
- `publication_ref`;
- `output_ref`;
- `trace_ref`;
- `status`.

`status` sólo puede ser `planned`, `executed`, `measured`, `recommended` o `published`.

## Reglas de integridad

1. Todas las referencias son identificadores, no resultados recalculados.
2. El orquestador no decide qué modelo o runtime recomendar.
3. El orquestador no mide rendimiento.
4. El orquestador no genera evidencia física.
5. `evidence_refs` debe proceder de la frontera de evidencia existente.
6. `decision_ref` debe proceder del contrato de decisión ODS/Magnitude → LEONES.
7. `recommendation_ref` debe proceder de la recomendación canónica.
8. `output_ref` debe proceder de la salida fiel de JALÓN 10.
9. Una operación declarativa no puede etiquetarse como ejecución física real.
10. No se permiten campos paralelos de scoring, ranking o estimación de TPS.
11. Una etapa ausente debe dejar la operación en un estado anterior, nunca inventar su resultado.

## Frontera física

JALÓN 11 no obliga a repetir todavía el benchmark de JALÓN 2. Cuando se ejecute una operación física, deberá reutilizar la evidencia `runtime-benchmark-evidence.v1.1` existente y sus referencias, no crear otro formato de medición.

## Criterio de cierre declarativo

Schema, orquestador, tests y audit runner deben demostrar que existe una sola cadena E2E y que todas sus etapas reutilizan los contratos anteriores.

El cierre operativo real requerirá posteriormente una ejecución física conservada como evidencia.

**Frase de recuperación:**

> JALÓN 11 = recorrer todos los contratos existentes en una sola operación E2E, sin crear una segunda arquitectura.
