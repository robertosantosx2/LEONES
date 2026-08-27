# JALÓN 2 — Evidencia física de runtime

**Estado: CERRADO**  
**Commit de cierre:** `947f61e4a65e9a34151999c8f94fd606295009f5`  
**Rama de cierre:** `jalon2-evidence-bridge`

## Objeto

JALÓN 2 convierte la primera ejecución física de `llama.cpp` en evidencia versionada, reproducible y auditable dentro de LEONES.

## Criterio de salida

El jalón queda cerrado porque el repositorio contiene:

- cinco ejecuciones físicas independientes de `llama.cpp`;
- `runtime-execution.json` por ejecución;
- `runtime-benchmark-evidence.json` por ejecución;
- `execution.log` y `terminal.transcript` por ejecución;
- un `jalon2-summary.json` consolidado;
- un `jalon2-integrity-manifest.json` con SHA-256 y tamaño de los artefactos;
- el bridge de extracción/normalización de evidencia física;
- el esquema `runtime-execution.v1`;
- tests específicos del bridge y del runtime execution contract;
- validación del conjunto específico de JALÓN 2: **9 tests pasados**.

## Identidad del runtime observado

Las ejecuciones conservan la identidad exacta del binario físico de `llama.cpp`, incluyendo versión/build/commit y SHA-256 del ejecutable. La evidencia mantiene además la identidad del modelo, cuantización, argumentos efectivos y datos de hardware disponibles en la ejecución.

## Integridad

La evidencia se publica bajo:

`artifacts/runtime-executions/jalon2-repeat/`

Manifest de integridad:

`artifacts/runtime-executions/jalon2-repeat/jalon2-integrity-manifest.json`

SHA-256 del manifest al cierre:

`e89651b58e1ba01f7f3647aa937ab77e352ae6e7e92d325bcdc538111773c6cc`

## Reproducibilidad

Las cinco ejecuciones se conservan como unidades independientes identificadas por `execution_id`. No se sustituye la evidencia física por una estimación ni por datos de proveedor: el registro conserva la salida de ejecución y la evidencia normalizada derivada de ella.

## Frontera con JALÓN 3

JALÓN 2 **no congela el protocolo general de medición**. Su función es cerrar el puente entre ejecución física y evidencia.

JALÓN 3 toma esta evidencia como antecedente y fija el contrato común de medición (`runtime-benchmark-evidence.v1.1`) para que las futuras ejecuciones sean comparables y reproducibles.

```text
JALÓN 2
runtime físico → extracción → normalización → evidencia íntegra
                                      ↓
                                  JALÓN 3
                         contrato de medición común
```

## Regla de preservación

Una vez cerrado, el conjunto de evidencia de JALÓN 2 se considera histórico. Las mejoras posteriores del contrato, documentación o tooling no deben reescribir retrospectivamente la evidencia física de este cierre.
