# LEONES Agentic Benchmark V1

## Objetivo

Batería reproducible para medir **tareas agentivas reales**, no únicamente respuestas de un modelo.

La unidad evaluada es:

```text
modelo + runtime + scaffold + herramientas + entorno + tarea
```

El resultado separa `outcome`, `trajectory`, eficiencia, seguridad, artefactos y procedencia de la evidencia.

## Regla de evidencia

LEONES mantiene cuatro conceptos que no deben mezclarse:

| Tipo | Significado | Puede alimentar evidencia empírica |
|---|---|---|
| `estimated` | cálculo o predicción previa a la ejecución | No |
| `reported` | dato declarado por una fuente o ejecución aún no verificada como medición | No |
| `measured` | dato obtenido de una ejecución identificable y fechada | Sí |
| `verified` | medición que además ha pasado una verificación independiente explícita | Sí, como evidencia verificada |

La etiqueta no se cambia por conveniencia: `measured` exige `execution_id` y `measured_at`; `verified` exige además verificador, fecha y método.

## Familias V1

| ID | Familia | Qué comprueba |
|---|---|---|
| A01 | Tool Use | Selección y uso correcto de herramientas |
| A02 | Multi-step | Dependencias entre pasos |
| A03 | Files & Artifacts | Creación/modificación/verificación de artefactos |
| A04 | Recovery | Recuperación ante errores |
| A05 | Long Horizon | Coherencia en tareas largas |
| A06 | Research | Búsqueda, contraste y síntesis |
| A07 | Coding | Inspección, modificación y pruebas |
| A08 | Local Operations | Operaciones en entorno local controlado |
| A09 | Safety | Respeto de permisos y límites |
| A10 | Cost/Latency | Presupuesto de tiempo/coste |

## Tarea canónica

Cada tarea debe declarar al menos:

- `id` y versión;
- objetivo;
- estado inicial;
- herramientas;
- restricciones/permisos;
- criterio de éxito;
- artefactos esperados;
- presupuesto opcional;
- grader y versión;
- estado dorado cuando exista.

A01 ya tiene una tarea canónica en `benchmarks/agentic/tasks/A01_tool_use_v1.json` y un smoke harness determinista en `benchmarks/agentic/smoke_a01.py`.

## Runner

El runner V1 ejecuta únicamente herramientas registradas por un adaptador: nunca interpreta texto del modelo como código ejecutable.

Contrato:

```text
prepare → execute → capture trace → grade → measure → emit result
```

`schemas/result.schema.json` separa el `status` del resultado de la procedencia `evidence.evidence_type`.

## Trazas

Los eventos mínimos son:

- `model`
- `tool_call`
- `tool_result`
- `error`
- `recovery`
- `artifact`
- `grader`
- `other`

## Estado

🟠 **V1 EN IMPLEMENTACIÓN — runner instrumentado + A01 smoke preparado.**

El smoke es deliberadamente determinista: valida el arnés, no constituye un benchmark de un modelo. El siguiente salto es conectar un adaptador real de modelo/runtime y ejecutar A01 con evidencia primaria. No se publica un score global hasta disponer de ejecuciones reproducibles y graders versionados.

## Referencias

- `docs/EVALUACION_AGENTIC_TESTS.md`
- `docs/RESULT_SCHEMA.md`
- `schemas/result.schema.json`
- `schemas/evidence.schema.json`
- `scripts/validate_evidence.py`
