# NEPENTHES — Software P0 status (importer)

**Date:** 2026-11-20  
**Scope:** GitHub / CI only (no MSI)

## Accepted in `main`

1. **Dynamic Nsight enum decoding**
   - Tables: `ENUM_CUDA_MEMCPY_OPER`, `ENUM_CUDA_MEM_KIND`
   - Columns: `copy_kind_value/name`, `src_kind_value/name`, `dst_kind_value/name`, `enum_decode_status`
   - Unknown values and unsigned sentinels preserved in `raw_json` without fabricated labels
   - Implementation: `scripts/nepenthes_nsys_import.py` (`load_enum_tables`, `decode_activity_enums`, `ensure_enum_schema`)

2. **Explicit NVTX correlation**
   - Reads `NVTX_EVENTS`, extracts request/batch tokens
   - Host↔Nsight clock calibration with bracket uncertainty
   - Attribution only as `windowed` when a single explicit window contains the activity interval
   - Overlapping windows rejected; many-to-many batch membership; no temporal proximity inference
   - Process/thread scoping (including globalTid → process recovery when globalPid absent)

3. **Tests** (`tests/test_nepenthes_nsys_import.py`)
   - Known enum mapping (HTOD, …)
   - Sentinel preservation (`-1` / UINT64_MAX)
   - Reimport rejection without overwrite
   - Paired NVTX clock calibration
   - Overlapping window rejection
   - Batch many-to-many and cross-thread rejection
   - Schema migration idempotency

## Obsolete branches

- `feat/nepenthes-nsys-enum-decode-20261119`
- `feat/nepenthes-nsys-nvtx-correlation-20261119`

These diverged from `main` (main is ahead with fuller implementation). Do not use them as status source.

## Still physical (MSI) — does not block software P0

- Additional enum validation against the exact Nsight SQLite version on MSI
- C07 batch (Tandem.cpp)
- C08 AIPerf-first overhead gate
- LEONES issue #212 end-to-end correlation

## Authority

Master document: [NEPENTHES-INDEX.md](NEPENTHES-INDEX.md).  
This note reconciles the software checklist only.
