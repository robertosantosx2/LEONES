# JALÓN 6 — CIERRE

## Estado

**CERRADO — integración mínima verificable de ODS y Magnitude.**

JALÓN 6 integra ODS y Magnitude con LEONES mediante adaptadores mínimos,
contratos comunes y el puente canónico `runtime-benchmark.v1`.

## Alcance cerrado

- Contrato común de `preflight`, `health`, `evidence` y `benchmark`.
- Adaptador ODS.
- Adaptador Magnitude.
- Evidencia `REPORTED` con referencia fijada.
- Puente de benchmark hacia `runtime-benchmark.v1`.
- Prohibición de convertir estimaciones en mediciones.
- Tests unitarios independientes del software externo.
- No ejecución ni instalación implícita de ODS/Magnitude.
- Plan de E2E físico separado de CI.

## Regla de autoridad

ODS y Magnitude pueden aportar:

- despliegue;
- configuración;
- perfilado;
- estado;
- recomendaciones;
- evidencia reportada.

LEONES conserva la autoridad sobre:

- decisión;
- procedencia;
- normalización;
- benchmark independiente;
- clasificación;
- recomendación final.

Una estimación o recomendación externa nunca se promociona automáticamente a
`MEASURED`.

## Evidencia de validación

La integración mínima queda respaldada por:

- `tests/test_external_stack_contract.py`
- `tests/test_ods_magnitude_adapters.py`
- `tests/test_ods_magnitude_evidence.py`
- `tests/test_ods_magnitude_benchmark_bridge.py`
- `tests/test_runtime_measurement.py`
- `tests/test_runtime_benchmark_evidence.py`
- tests activos de promoción, publicación, registro y validación.

Última validación:

**28 passed**

Además:

- `git diff --check`: limpio.
- Árbol de trabajo: limpio.
- Implementación fijada en Git.

## Límite del cierre

Este jalón **no certifica rendimiento físico de ODS ni Magnitude**.

La ejecución física E2E queda fuera de CI y sólo podrá producir evidencia
`MEASURED` mediante un host, runtime, modelo, workload y protocolo de medición
reales y reproducibles.

La ausencia de ese host no constituye un hueco del contrato.

## Siguiente jalón

El siguiente trabajo debe consumir esta integración, no duplicarla.

Debe partir del flujo:

`selección → preflight → ejecución → medición → evidencia → clasificación → recomendación`

y conservar `runtime-benchmark.v1` como frontera canónica de medición.
