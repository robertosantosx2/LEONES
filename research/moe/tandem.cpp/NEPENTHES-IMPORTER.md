# NEPENTHES — Nsight/CUPTI import into LEONES

## Scope

`scripts/nepenthes_nsys_import.py` provides three operations:
- **Inspection:** `--inspect-nsys SQLITE`, read-only; does not import rows.
- **Paired import:** NEPENTHES JSONL (`schema_version=1.0`) plus an Nsight Systems SQLite database from the same run.
- **Nsight-only import:** `--nsys-only SQLITE --output DB`, for historical captures with no associated JSONL.

The source SQLite database is opened read-only. The LEONES output database is independent and must not overwrite the source.

## Standalone import

```bash
python3 scripts/nepenthes_nsys_import.py \
  --nsys-only /path/to/qwen35-correlated-20261114.sqlite \
  --output /path/to/qwen35-nepenthes-nsys-only.sqlite
```

Migration `003_nepenthes_nsys_only.sql` creates `nepenthes_nsys_imports` and `nepenthes_nsys_activities`. It does not insert rows into `nepenthes_imports` or `nepenthes_events`, and it does not invent a `run_id`. The summary uses `mode=nsys_only`, `run_id=null`, and `jsonl=null`, and records the path, SHA-256, counts, coverage, and correlation policy.

## Paired import

```bash
python3 scripts/nepenthes_nsys_import.py \
  --jsonl /path/to/nepenthes.jsonl \
  --nsys-sqlite /path/to/nsys.sqlite \
  --output /path/to/nepenthes-import.sqlite
```

The import identity is derived from the JSONL SHA-256 unless `--import-id` is specified. Clock domains and correlations remain separate when no calibration or shared identifier exists.

## Tables and adapters

Migration 002 contains `nepenthes_imports`, `nepenthes_events`, and `nsys_activities` for the paired workflow. Migration 003 contains the separate Nsight-only tables.

The following activities are recognized:
- `KERNEL`, `CONCURRENT_KERNEL`
- `MEMCPY`, `MEMCPY2`
- `MEMSET`
- `RUNTIME`, `DRIVER`
- `GRAPH_TRACE`
- `SYNCHRONIZATION`
- `CUDA_EVENT`
- `OVERHEAD`

Names are resolved through `StringIds` when available. The original payload of each activity is preserved in `raw_json`. Additional CUPTI tables containing unsupported rows force coverage to `partial`; `complete_for_detected_cupti_tables` means only that all rows from the detected and supported CUPTI tables in that source were imported.

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
- `start_ns` null: 0; end earlier than start: 0; negative duration: 0.
- Applied migrations: `002_nepenthes_observability`, `003_nepenthes_nsys_only`.
- Provenance is isolated: one record in `nepenthes_nsys_imports`; zero records in `nepenthes_imports` and `nepenthes_events`.

### Reproducing the standalone validation

To repeat the import without touching the source capture or overwriting an existing database:

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

Acceptance criteria for this specific capture: integrity `ok`; empty `foreign_key_check`; one standalone import; 151,039 activities; zero paired imports and zero JSONL events. The eight expected counts are listed above. The temporary directory is created with private permissions; preserve the resulting database for later inspection.

### CUDA_EVENT particularity

The source table `CUPTI_ACTIVITY_KIND_CUDA_EVENT` contains 262 rows and all 262 `timestamp` values are zero (minimum and maximum 0). The importer preserves these values as `start_ns=0`, `end_ns=null`, and `duration_ns=null`. This matches the source and is not a loss introduced by normalization. These records must not be used to infer duration or chronology.

## Correlation and limitations

- NEPENTHES `request_id` is not CUPTI `correlationId`.
- NEPENTHES monotonic clocks and Nsight timestamps remain in separate domains.
- `correlation_id` can relate activities to CUDA APIs within the Nsight dataset; it does not prove request identity.
- A transfer is not attributed to prefetch based on temporal proximity.
- Host submission/dispatch is not presented as GPU execution duration.
- Importing does not turn evidence into `VERIFIED` by itself.

## Validation

Synthetic fixtures cover the JSONL contract, normalized CUPTI families, standalone provenance, partial coverage, and source protection. On the MSI, the historical import and the integrity/uniqueness/timing audits described above have been completed. A paired import of JSONL and Nsight from the same real inference is still pending.
