# NEPENTHES — importación Nsight/CUPTI en LEONES

## Alcance

`scripts/nepenthes_nsys_import.py` ofrece dos modos de ingestión:

- **Emparejado:** JSONL emitido por el sink NEPENTHES (`schema_version=1.0`) más SQLite exportado por Nsight Systems.
- **Nsight-only:** un SQLite de Nsight sin JSONL asociado, para preservar capturas históricas sin inventar un `run_id` ni eventos NEPENTHES.

El importador no requiere que Nsight esté instalado. Lee el SQLite fuente en modo solo lectura y escribe una base LEONES independiente.

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

## Importación histórica sin JSONL

Cuando solo se conserva el SQLite de Nsight (por ejemplo, la captura Qwen3.5-35B del 14-11-2026), se puede importar de forma independiente:

```bash
python3 scripts/nepenthes_nsys_import.py \\
  --nsys-only /ruta/captura/qwen35-correlated-20261114.sqlite \\
  --output /ruta/salida/qwen35-nsys-only.sqlite
```

El modo crea tablas separadas `nepenthes_nsys_imports` y `nepenthes_nsys_activities`, sin insertar filas en `nepenthes_imports` ni `nepenthes_events`. El resumen declara `mode=nsys_only`, `run_id=null` y `jsonl=null`. Conserva SHA-256, ruta de origen, payload JSON por fila, recuentos por tabla y estado de cobertura. La captura fuente nunca se modifica y la base de salida no puede sobrescribirla.

La migración `003_nepenthes_nsys_only.sql` crea el esquema aislado. El importador aplica las migraciones 002 y 003 al crear su base de salida.

## Modelo de almacenamiento

La migración `db/migrations/002_nepenthes_observability.sql` crea:

- `nepenthes_imports`: run ID, hashes SHA-256, recuentos, distribución por categorías y política de correlación.
- `nepenthes_events`: eventos JSONL tipados, campos de consulta e `raw_json` íntegro.
- `nsys_activities`: kernel, memcpy, memset, CUDA runtime y CUDA driver para importaciones emparejadas.
- `nepenthes_nsys_imports` y `nepenthes_nsys_activities` (migración 003): ingestión standalone con procedencia separada y sin requisito de JSONL/run ID.

Los nombres de kernel se resuelven mediante `StringIds` cuando esa tabla está disponible. Las filas fuente se conservan en JSON para permitir adaptar el normalizador a nuevas versiones de Nsight sin perder datos.

## Reglas de correlación y evidencia

- `request_id` NEPENTHES **no** es `correlationId` CUPTI.
- `monotonic_ns` NEPENTHES y `start`/`end` Nsight permanecen en dominios de reloj separados.
- No se crea un join request-kernel ni se atribuye una transferencia a prefetch por proximidad temporal.
- `correlation_id` se conserva para relacionar actividades Nsight con APIs CUDA dentro del propio conjunto Nsight; el importador no inventa relaciones entre JSONL y Nsight.
- Los hashes identifican los archivos exactos importados. Los registros no promueven por sí mismos evidencia a `VERIFIED`.

El importador falla ante JSONL malformado, campos requeridos ausentes, IDs duplicados, múltiples `run_id` en un mismo archivo o ausencia de tablas de actividad CUDA reconocidas. El resumen final informa las tablas encontradas y el recuento por tipo.

## Cobertura conocida y extensiones

El normalizador admite `KERNEL`, `CONCURRENT_KERNEL`, `MEMCPY`, `MEMCPY2`, `MEMSET`, `RUNTIME`, `DRIVER`, `GRAPH_TRACE`, `SYNCHRONIZATION`, `CUDA_EVENT` y `OVERHEAD`. Las tablas CUPTI adicionales se cuentan y aparecen en el informe como no soportadas; el estado de cobertura será `partial` si existen filas en tablas no mapeadas. Las filas de las tablas admitidas se conservan íntegramente en `raw_json`.

La validación incluye fixtures SQLite sintéticos. La inspección real del SQLite Qwen3.5-35B del MSI ha confirmado 8.982 kernels, 44.488 memcpy, 9 memset, 84.116 runtime, 5.207 graph trace, 7.864 synchronization, 262 CUDA events y 111 overhead. Esos recuentos son inspección de esquema/filas, no una importación ejecutada. La ingestión Nsight-only de esa captura real sigue pendiente.
