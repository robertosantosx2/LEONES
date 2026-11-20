# NEPENTHES — estado software P0 del importer Nsight

**Fecha:** 2026-11-20  
**Alcance:** implementación en main y regresiones software; no incluye validación física MSI.

## Aceptado en main (software/CI)

### Decodificación dinámica de enums Nsight
- Tablas de origen: `ENUM_CUDA_MEMCPY_OPER` y `ENUM_CUDA_MEM_KIND`.
- Columnas consultables: `copy_kind_value/name`, `src_kind_value/name`, `dst_kind_value/name`, `enum_decode_status`.
- Los valores desconocidos y sentinelas unsigned se conservan en `raw_json`; no se inventan etiquetas.
- Implementación: `scripts/nepenthes_nsys_import.py` (`load_enum_tables`, `decode_activity_enums`, `ensure_enum_schema`).

### Correlación NVTX explícita
- Lectura de `NVTX_EVENTS` y extracción de tokens request/batch.
- Calibración host↔Nsight con incertidumbre basada en brackets.
- Atribución `windowed` solo cuando una única ventana explícita contiene la actividad.
- Ventanas solapadas rechazadas; batch many-to-many; sin inferencia por proximidad temporal.
- Scoping por proceso/hilo, incluida la recuperación de identidad de proceso desde `globalTid` cuando falta `globalPid`.

### Regresiones
En `tests/test_nepenthes_nsys_import.py`:
- Mapping HTOD/DTOH y PAGEABLE/PINNED/DEVICE.
- Preservación de sentinelas `-1`/UINT64_MAX y valores desconocidos.
- Rechazo de reimportación sin sobrescritura.
- Calibración paired NVTX.
- Rechazo de ventanas solapadas.
- Batch many-to-many y rechazo de cruce de hilos.
- Idempotencia de migración de esquema.

## Ramas históricas obsoletas
- `feat/nepenthes-nsys-enum-decode-20261119`
- `feat/nepenthes-nsys-nvtx-correlation-20261119`

La implementación de `main` contiene la línea integrada más completa. No utilizar estas ramas como fuente de estado ni fusionarlas para recuperar el código.

## Pendiente físico — no bloquea P0 software
- Validación adicional contra la versión exacta de Nsight SQLite instalada en MSI.
- C07 batch de Tandem.cpp.
- C08 AIPerf-first: al menos tres pares baseline/instrumented y gate de overhead.
- Correlación end-to-end física de LEONES issue #212.

## Autoridad
El documento maestro [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md) es la única autoridad de prioridades, estado global y aceptación. Este documento es un anexo técnico.
