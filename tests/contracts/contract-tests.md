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

## Reglas de integración

1. Los schemas son la primera barrera.
2. Los tests de transición son la segunda.
3. Las pruebas de integración verifican que ningún adaptador pueda saltarse el flujo canónico.
4. Un fallo de contrato bloquea promoción.
5. Los tests deben ejecutarse en CI antes de cualquier writer canónico.

## Invariantes

```text
PROMOTED → Quality Gate PASS
PROMOTED → OSI PASS o NOT_REQUIRED
RECOMMENDATION → evidencia trazable
ROUTER → solo lectura del conocimiento canónico
ESTIMATED ≠ VERIFIED
MEASURED ≠ ESTIMATED
```

## Fixtures futuras

Los fixtures deberán incluir casos válidos, inválidos, fronterizos y contradictorios. Deben evitar datos reales o secretos.

## Criterio de aceptación

La implementación no se considera lista para producción hasta que todos los casos críticos pasen automáticamente en CI y exista al menos una prueba de integración por cada frontera:

```text
Evidence → Quality Gate
Quality Gate → Promotion
Promotion → Atlas
Atlas → Router
```
