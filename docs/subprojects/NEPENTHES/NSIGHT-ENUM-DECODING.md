# NEPENTHES — decodificación semántica de enums Nsight

## Objetivo

Decodificar los campos de operaciones de copia CUDA y tipos de memoria usando exclusivamente las tablas enum presentes en cada exportación SQLite de Nsight Systems. No se codifican correspondencias numéricas asumidas.

## Tablas y campos

- `ENUM_CUDA_MEMCPY_OPER` → `copyKind` / `memcpyKind`.
- `ENUM_CUDA_MEM_KIND` → `srcKind` y `dstKind`.

El importador inspecciona `PRAGMA table_info`, reconoce columnas numéricas y textuales habituales y conserva la tabla, columnas, número de filas y mapa decodificado en `enum_tables_json`. Si la estructura no se puede resolver, informa `unmapped_schema`; si un valor no tiene etiqueta, lo conserva como desconocido. No sustituye etiquetas ausentes por números supuestos.

## Persistencia

La migración idempotente 004, aplicada por `ensure_enum_schema`, añade a `nsys_activities` y `nepenthes_nsys_activities`:

- `copy_kind_value`, `copy_kind_name`
- `src_kind_value`, `src_kind_name`
- `dst_kind_value`, `dst_kind_name`
- `enum_decode_status`

Los campos numéricos originales permanecen en `raw_json`; también se conserva `_nepenthes_enum_decoding` con tabla fuente, valor y etiqueta. Los metadatos completos de las tablas enum quedan en `enum_tables_json` tanto en importación emparejada como Nsight-only.

Estados:
- `decoded`: todos los valores aplicables tienen etiqueta.
- `partial`: al menos uno se decodificó y otro no.
- `unknown_value_or_missing_enum_table`: hay campos aplicables, pero no se pudo resolver ninguno.
- `not_applicable`: la actividad no contiene estos campos.

## Centinelas unsigned

Un valor `-1` no se convierte en una etiqueta ordinaria ni se descarta. Se conserva exactamente en `raw_json` y en el valor SQLite firmado; el estado queda parcial/desconocido si no existe una entrada enum correspondiente. La interpretación como `UINT64_MAX` solo debe afirmarse cuando el tipo/campo de origen lo justifique, nunca por proximidad o intuición.

## Cobertura y límites

- El decodificador actual cubre operación memcpy y memoria origen/destino.
- Los tipos de sincronización y otras familias enum quedan para la siguiente iteración.
- No se infiere correlación request↔actividad Nsight ni se mezclan dominios de reloj.
- La existencia de una tabla enum no demuestra que toda la captura use esa tabla correctamente; la procedencia y el valor original siempre se conservan.
- La validación con SQLite C07 real y la revisión de versiones Nsight siguen siendo gates independientes de los fixtures sintéticos.

## Pruebas

Los fixtures prueban decodificación desde tablas enum sintéticas, importación emparejada, importación Nsight-only, inspección de esquema y preservación de un sentinel desconocido `-1`.
