# LEONES — Contract tests v1

## Objetivo

Comprobar automáticamente que las fronteras canónicas no se rompen al implementar los componentes.

## Matriz mínima

| Contrato | Caso | Resultado esperado |
|---|---|---|
| Atlas/Evidence | entidad sin `entity_id` | FAIL |
| Atlas/Evidence | evidencia sin `evidence_id` | FAIL |
| Atlas/Evidence | `verification_state=ESTIMATED` | PASS schema, nunca equivalente a VERIFIED |
| Atlas/Evidence | estado desconocido | FAIL |
| Quality/Promotion | `PROMOTED` + `quality_gate=FAIL` | FAIL |
| Quality/Promotion | `PROMOTED` + OSI `BLOCKED` | FAIL |
| Quality/Promotion | `PROMOTED` + OSI `PASS` + gate `PASS` | PASS |
| Quality/Promotion | check `FAIL` | no promoción |
| Router | `osi_mode=OPEN_ALL` | PASS |
| Router | `osi_mode=FORCE_COPYLEFT_CHECK` | PASS |
| Router | OSI arbitrario creado por usuario | FAIL |
| Router | recomendación sin `evidence_refs` | FAIL |
| Router | `ATLAS_WRITE` | FAIL por diseño |
| Router | Router no muta la recomendación de entrada | PASS |
| Selector → runtime-selection.v1 | candidato FreeToken con evidencia MoE/agentic y hardware medido | PASS, plan de benchmark |
| Selector → runtime-selection.v1 | candidato FreeToken sin evidencia MoE | FAIL, runtime bloqueado |
| Runtime evidence → Atlas | `measured` con execution_id y provenance | actualiza feedback |
| Runtime evidence → Atlas | `reported` | no sustituye medición |
| Runtime evidence → Atlas | `verified` sin verificador independiente | FAIL |
| Atlas → Router | recomendación con `evidence_refs` | PASS, read-only |
| Atlas → Router | recomendación sin trazabilidad | FAIL |
| Atlas → Router | intento de escritura | FAIL |

## Reglas de integración

1. Los schemas son la primera barrera.
2. Los tests de transición son la segunda.
3. Las pruebas de integración verifican que ningún adaptador pueda saltarse el flujo canónico.
4. Un fallo de contrato bloquea promoción.
5. Los tests deben ejecutarse en CI antes de cualquier writer canónico.
6. La regresión selector → `runtime-selection.v1` debe ejecutarse sin runtimes instalados ni hardware real; solo valida el contrato y sus gates deterministas.
7. El Router es estrictamente de lectura: consume conocimiento y evidencia, pero nunca escribe sobre el Atlas canónico.
8. Toda recomendación que llegue al Router debe mantener referencias de evidencia trazables.

## Invariantes

```text
PROMOTED → Quality Gate PASS
PROMOTED → OSI PASS o NOT_REQUIRED
RECOMMENDATION → evidencia trazable
ROUTER → solo lectura del conocimiento canónico
ROUTER → no ATLAS_WRITE
ESTIMATED ≠ VERIFIED
MEASURED ≠ ESTIMATED
SELECTOR → runtime-selection.v1 sin pérdida de evidencia runtime-específica
FreeToken → MoE + agentic + señales de hardware medidas
MEASURED → puede alimentar comparación futura
REPORTED → no sustituye MEASURED
```

## Criterio de aceptación

La implementación no se considera lista para producción hasta que todos los casos críticos pasen automáticamente en CI y exista al menos una prueba de integración por cada frontera:

```text
Evidence → Quality Gate
Quality Gate → Promotion
Promotion → Atlas
Atlas → Router
Selector → runtime-selection.v1
Runtime benchmark → Evidence
Evidence → Atlas feedback
```
