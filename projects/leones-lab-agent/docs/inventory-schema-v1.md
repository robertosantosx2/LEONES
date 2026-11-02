# LEONES Lab Agent — Inventory JSON schema v1

This document defines the stable fields emitted by:

- lab-agent inventory --json
- lab-agent models --json
- lab-agent doctor --json

All commands write one JSON object to standard output. Diagnostic errors are written to standard error. The schema version is an integer and changes only when a breaking field or meaning change is introduced.

## Inventory object

Top-level fields:

| Field | Type | Meaning |
|---|---|---|
| schema_version | integer | Currently 1 |
| tools | array | Executables found in PATH or explicitly supported local paths |
| models | array | Model cache entries and discovered weight files |
| components | array | Local components such as Magnitude and ODS |

## Tool record

| Field | Type | Meaning |
|---|---|---|
| name | string | Executable name |
| path | string | Resolved executable path |

A discovered executable is not proof that a server is running or that it supports a particular model.

## Model record

| Field | Type | Meaning |
|---|---|---|
| name | string | Repository/model identifier or weight filename |
| source | string | Discovery source, currently Hugging Face or ODS |
| path | string | Local path inspected |
| format | string | Detected weight-file format(s) |
| state | string | Evidence state |
| weight_bytes | integer | Sum of detected weight-file sizes in bytes |

A CACHE_ENTRY has weight_bytes=0 because no recognized weight file was confirmed. WEIGHTS_PRESENT means files with recognized extensions were found; it does not prove integrity, compatibility, loadability, or execution.

## Component record

| Field | Type | Meaning |
|---|---|---|
| name | string | Component name |
| installed | boolean | Presence detected in the inspected locations |
| active | boolean or null | Service state if queried; null means unknown/not queried |
| detail | string | Human-readable scope and limitation |

## Evidence states

The lifecycle is deliberately monotonic and evidence-based:

1. DISCOVERED — a configuration/catalogue reference exists.
2. CACHE_ENTRY — a local cache entry exists.
3. WEIGHTS_PRESENT — one or more recognized weight files exist.
4. AVAILABLE — a compatible engine confirms it can access the model.
5. LOAD_VERIFIED — the engine confirms successful model loading.
6. RUNNING — an inference process is confirmed active.
7. MEASURED — a benchmark has recorded metrics and protocol.

Version 0.3.0 currently emits CACHE_ENTRY and WEIGHTS_PRESENT only. It must not infer a later state from an earlier one.

## Doctor object

The doctor JSON object has:

- schema_version
- os
- kernel
- cpu
- logical_cpus
- memory_total_kib
- memory_available_kib
- gpu
- cuda_toolkit

The memory values are KiB integers or null. GPU information comes from nvidia-smi. cuda_toolkit describes nvcc availability/version; it is not a CUDA runtime compatibility test.

## Compatibility policy

New optional fields may be added without incrementing schema_version. Renaming fields, changing a field type, or changing the semantics of an existing field requires a new schema version. Consumers should ignore unknown fields.
