# LEONES Agentic Benchmark V1

## Objetivo

Batería reproducible para medir **tareas agentivas reales**, no únicamente respuestas de un modelo.

La unidad evaluada es:

```text
modelo + runtime + scaffold + herramientas + entorno + tarea
```

El resultado separa `outcome`, `trajectory`, eficiencia, seguridad y artefactos.

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

## Runner

El runner V1 debe ejecutar una tarea en un entorno controlado y producir un resultado compatible con `schemas/result.schema.json`.

Contrato conceptual:

```text
prepare → execute → capture trace → grade → measure → emit result
```

No se aceptan puntuaciones inventadas ni métricas estimadas como si fueran medidas.

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

## Smoke inicial

Antes de ampliar la batería, se deben instrumentar B01–B05 existentes y transformar especialmente B02/B04 en pruebas con herramientas reales donde el entorno lo permita.

## Estado

🟡 **DISEÑO V1 ACEPTADO — RUNNER PENDIENTE DE EJECUCIÓN REAL.**

No se publica un score global hasta tener ejecuciones reproducibles, graders versionados y evidencia primaria.

## Referencias

- `docs/EVALUACION_AGENTIC_TESTS.md`
- `docs/RESULT_SCHEMA.md`
- `docs/sources/ARTIFICIAL_ANALYSIS_OPTIMA_AGENTIC_BENCHMARKS.md`
- `schemas/result.schema.json`
