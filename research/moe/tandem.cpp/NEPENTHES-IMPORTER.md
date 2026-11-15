# NEPENTHES — importación Nsight/CUPTI en LEONES

## Alcance

`scripts/nepenthes_nsys_import.py` ingiere dos artefactos de una misma ejecución:

- JSONL emitido por el sink NEPENTHES (`schema_version=1.0`).
- SQLite exportado por Nsight Systems (`.sqlite`).

El importador no requiere que Nsight esté instalado. Lee el SQLite exportado en modo solo lectura y escribe una base LEONES independiente o una base de evidencias existente.

## Inspección de un export Nsight existente

Antes de importar una captura emparejada, se puede inspeccionar el esquema real del SQLite sin necesitar JSONL y sin copiar filas fuente:

```bash
python3 scripts/nepenthes_nsys_import.py \\
  --inspect-nsys /ruta/captura/qwen35-moe-cuda-no-osrt-20261114.sqlite
```

El informe enumera tablas CUPTI reconocidas y no reconocidas, columnas y recuentos, además de las tablas de strings. No exporta valores de filas ni crea una base de importación. Sirve para comprobar compatibilidad de esquema, no para declarar que el SQLite pertenece a un run NEPENTHES.

## Uso

```bash
python3 scripts/nepenthes_nsys_import.py \
  --jsonl /ruta/captura/nepenthes.jsonl \
  --nsys-sqlite /ruta/captura/nsys.sqlite \
  --output /ruta/captura/nepenthes-import.sqlite
```

El `import_id` se deriva por defecto del SHA-256 del JSONL. Puede fijarse con `--import-id` para una importación controlada. Los artefactos fuente no se modifican.

## Modelo de almacenamiento

La migración `db/migrations/002_nepenthes_observability.sql` crea:

- `nepenthes_imports`: run ID, hashes SHA-256, recuentos, distribución por categorías y política de correlación.
- `nepenthes_events`: eventos JSONL tipados, campos de consulta e `raw_json` íntegro.
- `nsys_activities`: kernel, memcpy, memset, CUDA runtime y CUDA driver; incluye tiempos originales, stream/context/device, correlation ID y `raw_json`.

Los nombres de kernel se resuelven mediante `StringIds` cuando esa tabla está disponible. Las filas fuente se conservan en JSON para permitir adaptar el normalizador a nuevas versiones de Nsight sin perder datos.

## Reglas de correlación y evidencia

- `request_id` NEPENTHES **no** es `correlationId` CUPTI.
- `monotonic_ns` NEPENTHES y `start`/`end` Nsight permanecen en dominios de reloj separados.
- No se crea un join request-kernel ni se atribuye una transferencia a prefetch por proximidad temporal.
- `correlation_id` se conserva para relacionar actividades Nsight con APIs CUDA dentro del propio conjunto Nsight; el importador no inventa relaciones entre JSONL y Nsight.
- Los hashes identifican los archivos exactos importados. Los registros no promueven por sí mismos evidencia a `VERIFIED`.

El importador falla ante JSONL malformado, campos requeridos ausentes, IDs duplicados, múltiples `run_id` en un mismo archivo o ausencia de tablas de actividad CUDA reconocidas. El resumen final informa las tablas encontradas y el recuento por tipo.

## Cobertura conocida y extensiones

La primera versión normaliza `CUPTI_ACTIVITY_KIND_KERNEL`, `CONCURRENT_KERNEL`, `MEMCPY`, `MEMCPY2`, `MEMSET`, `RUNTIME` y `DRIVER`. Las tablas adicionales del export Nsight no se descartan de la fuente: permanecen en el SQLite original y pueden incorporarse mediante adaptadores explícitos.

La validación de esta versión usa fixtures SQLite sintéticos. No sustituye la importación de la captura Qwen3.5-35B real del MSI ni acredita todavía cobertura completa de esa captura.
