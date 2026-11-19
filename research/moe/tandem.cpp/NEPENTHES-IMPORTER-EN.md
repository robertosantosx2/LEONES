# NEPENTHES — Nsight/CUPTI import into LEONES

**Language:** [English](NEPENTHES-IMPORTER-EN.md) · [Español](NEPENTHES-IMPORTER.md)

## Scope

`scripts/nepenthes_nsys_import.py` supports three operations:

- **Inspection:** `--inspect-nsys SQLITE`, read-only, without importing rows.
- **Paired import:** NEPENTHES JSONL (`schema_version=1.0`) plus Nsight Systems SQLite from the same execution.
- **Nsight-only import:** `--nsys-only SQLITE --output DB`, for historical captures without associated JSONL.

The source SQLite is opened read-only. The LEONES output database is independent and must not overwrite the source.

## Standalone import

```bash
python3 scripts/nepenthes_nsys_import.py \
  --nsys-only /path/qwen35-correlated-20261114.sqlite \
  --output /path/qwen35-nepenthes-nsys-only.sqlite
```

Migration `003_nepenthes_nsys_only.sql` creates `nepenthes_nsys_imports` and `nepenthes_nsys_activities`. It does not insert into `nepenthes_imports` or `nepenthes_events`, and does not invent a `run_id`. The summary uses `mode=nsys_only`, `run_id=null`, `jsonl=null`, and records path, SHA-256, counts, coverage and correlation policy.

## Paired import

```bash
python3 scripts/nepenthes_nsys_import.py \
  --jsonl /path/nepenthes.jsonl \
  --nsys-sqlite /path/nsys.sqlite \
  --output /path/nepenthes-import.sqlite
```

Import identity is derived from the JSONL SHA-256 unless `--import-id` is supplied. Clock domains and correlations remain separate when no calibration or shared identifier exists.

## Tables and adapters

Migration 002 contains `nepenthes_imports`, `nepenthes_events` and `nsys_activities` for paired imports. Migration 003 contains independent Nsight-only tables.

Recognized activity families:

- `KERNEL`, `CONCURRENT_KERNEL`
- `MEMCPY`, `MEMCPY2`
- `MEMSET`
- `RUNTIME`, `DRIVER`
- `GRAPH_TRACE`
- `SYNCHRONIZATION`
- `CUDA_EVENT`
- `OVERHEAD`

Names are resolved through `StringIds` when available. Each activity's original payload is retained in `raw_json`. Additional CUPTI tables containing unsupported rows force coverage to `partial`; `complete_for_detected_cupti_tables` means only that every row in the detected and supported CUPTI tables in that source was imported.

## Real MSI import evidence — 2026-11-15

Source: `~/NEPENTHES_QWEN35_CORRELATED_20261114/qwen35-correlated-20261114.sqlite`.  
Destination: `qwen35-nepenthes-nsys-only-20261115.sqlite`.

- Source SHA-256: `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`.
- Imported rows: **151,039** across eight families.
- Distribution: kernel 8,982; memcpy 44,488; memset 9; runtime 84,116; graph trace 5,207; synchronization 7,864; CUDA event 262; overhead 111.
- Coverage: `complete_for_detected_cupti_tables`; unsupported tables with rows: 0.
- Destination SQLite: approximately 82 MiB.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: empty.
- Unique IDs: 151,039/151,039; unique source_table/activity_id pairs: 151,039/151,039.
- Null `start_ns`: 0; end before start: 0; negative duration: 0.
- Migrations applied: `002_nepenthes_observability`, `003_nepenthes_nsys_only`.
- Provenance is isolated: one record in `nepenthes_nsys_imports`; zero in `nepenthes_imports` and `nepenthes_events`.

### CUDA_EVENT detail

The source `CUPTI_ACTIVITY_KIND_CUDA_EVENT` table contains 262 rows and all 262 `timestamp` values are zero (minimum and maximum are zero). The importer preserves them as `start_ns=0`, `end_ns=null`, `duration_ns=null`. This matches the source and is not data lost during normalization. Do not use these records to infer ordering or duration.

## Correlation and limitations

- NEPENTHES `request_id` is not CUPTI `correlationId`.
- NEPENTHES monotonic clocks and Nsight timestamps remain separate domains.
- `correlation_id` can relate CUDA activities to CUDA APIs within Nsight; it does not prove request identity.
- A transfer is not attributed to prefetch based on temporal proximity.
- Host submission/dispatch is not presented as GPU execution duration.
- Importing data does not by itself turn evidence into `VERIFIED`.

## Validation

Synthetic fixtures cover the JSONL contract, normalized CUPTI families, standalone provenance, partial coverage and source protection. The historical MSI import and the integrity/uniqueness/time audits above have been completed. A paired import of JSONL and Nsight from the same real inference remains pending.
