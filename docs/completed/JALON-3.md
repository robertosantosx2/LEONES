# JALÓN 3 — Protocolo de medición real

**Estado: 🟢 CERRADO (diseño y contrato)**  
**Fecha de cierre: 2026-08-27**

## Objetivo

Fijar antes de la ejecución física el protocolo que convierte una ejecución de runtime en evidencia comparable, reproducible y conservable.

## Resultado

JALÓN 3 deja fijado el contrato operativo `runtime-benchmark-evidence.v1.1`: identidad del modelo y artefacto, protocolo de workload, warm-up, iteraciones, métricas, entorno, runtime, ejecución, stdout/stderr y hashes.

También queda fijada la separación entre estimación, dato reportado y medición física, así como la distinción metodológica entre medición local y benchmarks de API.

## Validación de implementación

El contrato cuenta con implementación, schema y pruebas automatizadas. La validación actual de:

- `tests/test_runtime_measurement.py`
- `tests/test_runtime_benchmark_evidence.py`

es **8/8 tests pasados**.

## Relación con la ejecución física

El cierre de este documento significa que **el diseño y el contrato están cerrados**. No significa que JALÓN 3 tenga ya una nueva medición física propia.

La primera ejecución física que materializa este contrato debe producir una evidencia real reproducible de runtime y conservarla según `runtime-benchmark-evidence.v1.1`.

## Criterio de continuación

No se rediseña el protocolo al llegar al equipo físico. Se ejecuta:

```text
selección → runtime gate → ejecución → medición → evidencia → validación → conservación
```

## Decisión

**JALÓN 3 queda cerrado en diseño, contrato y protocolo.** La ejecución física queda como siguiente etapa operativa, sin alterar retroactivamente el contrato.
