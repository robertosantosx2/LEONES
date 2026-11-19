# Informe de captura histórica — Qwen3.5-35B / Nsight Systems

**Language / Idioma:** [English version](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115-EN.md) · [Versión en español](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md)


**Fecha del informe:** 2026-11-15  
**Tipo:** análisis retrospectivo de una captura Nsight existente; importación standalone NEPENTHES.  
**Estado:** importación validada estructuralmente. No es una nueva ejecución de `nepenthes run` ni una captura emparejada JSONL+Nsight.

## 1. Resumen ejecutivo

Se importó en el MSI el SQLite histórico de Nsight Systems:

- Origen: `~/NEPENTHES_QWEN35_CORRELATED_20261114/qwen35-correlated-20261114.sqlite`
- Destino: `qwen35-nepenthes-nsys-only-20261115.sqlite`
- Modo: `nsys_only`
- Import ID: `nsys-30df43c0a1b2`
- SHA-256 origen: `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`
- Filas importadas: **151.039**
- Tamaño destino observado: aproximadamente **82 MiB** (85.020.672 bytes).

La importación conserva procedencia separada: `run_id=null`, `jsonl=null`; no se afirma que el archivo tenga un JSONL NEPENTHES asociado.

## 2. Distribución de actividades

| Familia normalizada | Tabla CUPTI | Filas |
|---|---|---:|
| CUDA kernel | `CUPTI_ACTIVITY_KIND_KERNEL` | 8.982 |
| CUDA memcpy | `CUPTI_ACTIVITY_KIND_MEMCPY` | 44.488 |
| CUDA memset | `CUPTI_ACTIVITY_KIND_MEMSET` | 9 |
| CUDA runtime | `CUPTI_ACTIVITY_KIND_RUNTIME` | 84.116 |
| CUDA graph trace | `CUPTI_ACTIVITY_KIND_GRAPH_TRACE` | 5.207 |
| CUDA synchronization | `CUPTI_ACTIVITY_KIND_SYNCHRONIZATION` | 7.864 |
| CUDA event | `CUPTI_ACTIVITY_KIND_CUDA_EVENT` | 262 |
| CUDA overhead | `CUPTI_ACTIVITY_KIND_OVERHEAD` | 111 |
| **Total** | **8 tablas detectadas** | **151.039** |

Cobertura declarada: `complete_for_detected_cupti_tables`. No hubo filas no soportadas en las tablas CUPTI detectadas. Esta etiqueta no significa que Nsight haya capturado todas las categorías de actividad posibles; describe únicamente las tablas detectadas en este archivo.

### Visualización de volumen por familia

![Recuento de actividades CUPTI por familia](figures/nepenthes-qwen35-activity-counts-20261115.svg)

La gráfica compara recuentos de filas, no duración ni porcentaje de tiempo de GPU. La escala es lineal y la actividad runtime domina el volumen de registros.

## 3. Auditoría de integridad

| Prueba | Resultado |
|---|---|
| SQLite `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | Sin filas |
| Actividades | 151.039 |
| IDs únicos | 151.039 |
| Pares tabla/ID únicos | 151.039 |
| `start_ns` nulo | 0 |
| `end_ns < start_ns` | 0 |
| Duración negativa | 0 |
| Migraciones | 002 y 003 aplicadas |
| Importaciones standalone | 1 |
| Importaciones JSONL emparejadas | 0 |
| Eventos JSONL | 0 |

El hash SHA-256 almacenado en el registro de procedencia coincide con el hash de origen comunicado por el importador. El fichero de origen no se modificó.

## 4. Particularidad de CUDA_EVENT

La tabla original `CUPTI_ACTIVITY_KIND_CUDA_EVENT` contiene 262 filas. La consulta directa sobre el origen devolvió:

- total: 262
- `timestamp = 0`: 262
- `timestamp IS NULL`: 0
- mínimo y máximo: 0

En la base importada, las 262 filas tienen `start_ns=0`, `end_ns=null` y `duration_ns=null`. El valor coincide con la fuente. No es una pérdida del importador. Estos registros no deben usarse para ordenar eventos por tiempo ni para calcular duración.

## 5. Dominio temporal observado

En las actividades que sí tienen marcas temporales, los rangos globales observados en la auditoría fueron aproximadamente:

- Inicio mínimo: 1.453.681.912 ns (runtime).
- Final máximo: 85.612.540.605 ns (runtime).

Las marcas pertenecen al dominio temporal exportado por Nsight. No deben compararse directamente con `monotonic_ns` de NEPENTHES sin calibración. Los CUDA_EVENT con timestamp cero se excluyen de cualquier reconstrucción temporal.

## 6. Contexto de la ejecución histórica

Los metadatos de benchmark conservados para esta ejecución Qwen3.5-35B-A3B indican 39 tokens evaluados, 128 tokens generados, aproximadamente 14,96 tokens/s de prompt y 32,07 tokens/s de generación. El registro Nsight tuvo una duración aproximada de 217,805 s.

Estos valores describen el benchmark histórico asociado a la captura, no una medición nueva realizada por el importador. El número de actividades CUPTI tampoco equivale al número de tokens ni permite por sí solo asignar un kernel a un token o request.

## 7. Qué permite concluir

1. El SQLite histórico contiene una cantidad sustancial de actividad CUDA y se pudo importar sin exigir un JSONL inexistente.
2. Las ocho familias CUPTI detectadas fueron importadas íntegramente según el adaptador actual.
3. La base destino es estructuralmente íntegra, sin duplicados detectados y con procedencia explícita.
4. Los identificadores `correlationId` se preservan en el dominio Nsight; pueden ayudar a relacionar actividades CUDA internas, pero no crean una relación con `request_id` NEPENTHES.
5. El archivo histórico sirve como dataset retrospectivo para análisis de kernels, transferencias, runtime, sincronización y graph trace.

## 8. Qué no permite concluir

- No permite atribuir cada kernel a una petición NEPENTHES: no hay JSONL emparejado ni identificador compartido demostrado.
- No permite mezclar timestamps Nsight y monotónicos de NEPENTHES.
- No demuestra que lookahead/prefetch estuviera activo ni que una transferencia concreta le perteneciera.
- No demuestra ausencia general de OOM ni reconstruye por sí solo el ciclo de vida completo de KV cache.
- No es una validación de la captura integrada del wrapper CLI.
- No mide el overhead de NEPENTHES, porque esta captura precede a la prueba de extremo a extremo del wrapper.

## 9. Próxima prueba necesaria

Ejecutar una inferencia nueva con el motor Tandem.cpp instrumentado bajo `nepenthes run --profile full`, conservando en el mismo paquete:

1. manifest y configuración exacta;
2. host-events y engine-events JSONL;
3. SQLite y reporte nativo Nsight;
4. respuesta, logs, exit code y checksums;
5. importación emparejada en LEONES;
6. auditoría de cobertura, pérdidas, integridad y overhead.

Solo esa prueba permitirá cerrar la aceptación end-to-end. Ver el roadmap: [NEPENTHES-ROADMAP.md](NEPENTHES-ROADMAP.md).
