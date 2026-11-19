# NEPENTHES — importación Nsight/CUPTI en LEONES

**Language / Idioma:** [English version](NEPENTHES-IMPORTER-EN.md) · [Versión en español](NEPENTHES-IMPORTER.md)


## Alcance

`scripts/nepenthes_nsys_import.py` ofrece tres operaciones:
- **Inspección:** `--inspect-nsys SQLITE`, solo lectura, sin importar filas.
- **Emparejada:** JSONL NEPENTHES (`schema_version=1.0`) + SQLite Nsight Systems de la misma ejecución.
- **Nsight-only:** `--nsys-only SQLITE --output DB`, para capturas históricas sin JSONL asociado.

El SQLite fuente se abre en modo solo lectura. La base LEONES de salida es independiente y no debe sobrescribir la fuente.

## Importación standalone

```bash
python3 scripts/nepenthes_nsys_import.py \
  --nsys-only /ruta/qwen35-correlated-20261114.sqlite \
  --output /ruta/qwen35-nepenthes-nsys-only.sqlite
```

La migración `003_nepenthes_nsys_only.sql` crea `nepenthes_nsys_imports` y `nepenthes_nsys_activities`. No inserta filas en `nepenthes_imports` ni `nepenthes_events`; no inventa `run_id`. El resumen usa `mode=nsys_only`, `run_id=null`, `jsonl=null` y registra ruta, SHA-256, recuentos, cobertura y política de correlación.

## Importación emparejada

```bash
python3 scripts/nepenthes_nsys_import.py \
  --jsonl /ruta/nepenthes.jsonl \
  --nsys-sqlite /ruta/nsys.sqlite \
  --output /ruta/nepenthes-import.sqlite
```

La identidad del import se deriva del SHA-256 del JSONL salvo que se indique `--import-id`. Los relojes y correlaciones permanecen separados cuando no existe calibración o identificador compartido.

## Tablas y adaptadores

La migración 002 contiene `nepenthes_imports`, `nepenthes_events` y `nsys_activities` para el flujo emparejado. La migración 003 contiene las tablas independientes Nsight-only.

Se reconocen las actividades:
- `KERNEL`, `CONCURRENT_KERNEL`
- `MEMCPY`, `MEMCPY2`
- `MEMSET`
- `RUNTIME`, `DRIVER`
- `GRAPH_TRACE`
- `SYNCHRONIZATION`
- `CUDA_EVENT`
- `OVERHEAD`

Los nombres se resuelven mediante `StringIds` cuando está disponible. El payload original de cada actividad se conserva en `raw_json`. Las tablas CUPTI adicionales con filas no soportadas fuerzan cobertura `partial`; `complete_for_detected_cupti_tables` significa únicamente que se importaron todas las filas de las tablas CUPTI detectadas y soportadas en esa fuente.

## Evidencia de importación real en MSI — 2026-11-15

Fuente: `~/NEPENTHES_QWEN35_CORRELATED_20261114/qwen35-correlated-20261114.sqlite`.

Destino: `qwen35-nepenthes-nsys-only-20261115.sqlite`.

- SHA-256 fuente: `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`.
- Filas importadas: **151.039** en ocho familias.
- Distribución: kernel 8.982; memcpy 44.488; memset 9; runtime 84.116; graph trace 5.207; synchronization 7.864; CUDA event 262; overhead 111.
- Cobertura: `complete_for_detected_cupti_tables`; tablas no soportadas con filas: 0.
- SQLite destino: aproximadamente 82 MiB.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: vacío.
- IDs únicos: 151.039/151.039; pares source_table/activity_id únicos: 151.039/151.039.
- `start_ns` nulo: 0; end anterior a start: 0; duración negativa: 0.
- Migraciones aplicadas: `002_nepenthes_observability`, `003_nepenthes_nsys_only`.
- La procedencia queda aislada: un registro en `nepenthes_nsys_imports`; cero registros en `nepenthes_imports` y `nepenthes_events`.

### Reproducción de la validación standalone

Para repetir la importación sin tocar la captura fuente ni sobrescribir una base previa:

```bash
set -euo pipefail
SRC="$HOME/NEPENTHES_QWEN35_CORRELATED_20261114/qwen35-correlated-20261114.sqlite"
TMPDIR_RUN="$(mktemp -d /tmp/nepenthes-nsys-only.XXXXXX)"
OUT="$TMPDIR_RUN/import.sqlite"
python3 scripts/nepenthes_nsys_import.py --inspect-nsys "$SRC"
python3 scripts/nepenthes_nsys_import.py --nsys-only "$SRC" --output "$OUT"
sqlite3 "$OUT" <<'SQL'
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SELECT COUNT(*) FROM nepenthes_nsys_imports;
SELECT COUNT(*) FROM nepenthes_nsys_activities;
SELECT activity_kind, COUNT(*) FROM nepenthes_nsys_activities
GROUP BY activity_kind ORDER BY activity_kind;
SELECT COUNT(*) FROM nepenthes_imports;
SELECT COUNT(*) FROM nepenthes_events;
SQL
```

Criterios de aceptación para esta captura concreta: integridad `ok`; `foreign_key_check` vacío; un import standalone; 151.039 actividades; cero imports emparejados y cero eventos JSONL. Las ocho cantidades esperadas se detallan arriba. El directorio temporal se crea con permisos privados; conserva la base resultante para su inspección posterior.

### Particularidad CUDA_EVENT

La tabla fuente `CUPTI_ACTIVITY_KIND_CUDA_EVENT` contiene 262 filas y sus 262 valores `timestamp` son cero (mínimo y máximo 0). El importador conserva esos valores como `start_ns=0`, `end_ns=null`, `duration_ns=null`. Esto coincide con el origen y no es una pérdida introducida por la normalización. No se deben usar esos registros para inferir duración o cronología.

## Correlación y límites

- `request_id` NEPENTHES no es `correlationId` CUPTI.
- Los relojes monotónicos de NEPENTHES y los timestamps Nsight permanecen en dominios separados.
- `correlation_id` puede relacionar actividades con APIs CUDA dentro del conjunto Nsight; no prueba identidad de request.
- No se atribuye una transferencia a prefetch por proximidad temporal.
- No se presenta submission/dispatch host como duración GPU.
- El import no convierte evidencia en `VERIFIED` por sí solo.

## Validación

Los fixtures sintéticos cubren el contrato JSONL, las familias CUPTI normalizadas, procedencia standalone, cobertura parcial y protección de la fuente. En MSI se ha completado la importación histórica y las auditorías de integridad/unicidad/tiempo descritas arriba. La importación emparejada de JSONL y Nsight de una misma inferencia real sigue pendiente.
