# NEPENTHES shared multi-engine trace envelope

> **Authority:** `research/moe/tandem.cpp/NEPENTHES-INDEX.md` is the only source of truth for project priorities, status and architecture. This file is a technical annex for LEONES issue #207; it does not create a roadmap or acceptance state.

## Shared implementation

- `scripts/nepenthes_trace_envelope.py` owns the common JSONL envelope fields, privacy rejection, unsigned integer bounds, correlation/attribution invariants, canonical summary shape and closed connector registry.
- `scripts/nepenthes_llama_trace_import.py` remains the compatibility entry point. Its `import_trace(path)` default remains `source="llama.cpp"`; existing callers and output fields are preserved.
- The same importer entry point accepts a registered connector explicitly: `import_trace(path, source="tensorfold")`. This does not create a TensorFold-specific importer, runner or evidence pipeline.

## Closed source profiles

Only sources registered in `SOURCE_PROFILES` are accepted. A caller cannot register or pass an arbitrary source name at runtime.

| Source | Registered clock domain | Source-specific semantics |
|---|---|---|
| `llama.cpp` | `steady_clock` | Existing request/correlation and clock-calibration behavior is retained |
| `tensorfold` | `steady_clock` | Initial TensorFold contract; request identity must be per HTTP request, not per keep-alive connection |

The profiles intentionally share `steady_clock` today because that is what both reviewed contracts specify. A future difference requires a reviewed contract change and explicit tests; it must not be inferred from an engine name.

## Common event envelope

Required event fields: `schema_version`, `run_id`, `event_id`, `source`, `timestamp_unix_ns`, `monotonic_ns`, `request_id`, `event_kind`, `label`, `value0`, `value1`, `duration_ns`, `flags`.

Optional fields: `correlation_token`, `attribution_level`, `clock_domain`.

The validator enforces schema 1.0, non-empty run/event IDs, source equality with the selected registered profile, exact field sets, unsigned 64-bit values, unsigned 16-bit flags, allowed attribution levels and explicit-token rules. Boolean values are not integers for this contract. Prompt/completion/text/token payload fields are rejected.

An `exact` attribution requires a positive explicit unsigned 64-bit `correlation_token`; a token with any other attribution level is rejected. `windowed`, `device_wide` and `estimated` do not establish request-to-kernel causality. No temporal-proximity correlation is performed.

## Canonical sink summary

The final record is exactly:

- `schema_version`, `run_id`, `event_id`, `source`, `timestamp_unix_ns`
- `event_kind="sink_summary"`
- `events_drained`, `dropped_events`, `write_errors`

All counters/timestamps are unsigned 64-bit values. The summary must match the selected source and run ID, have a unique non-empty event ID, and be the final non-empty JSONL record. A missing summary is incomplete unless the existing explicit interrupted-capture option is used. Queue drops, writer errors or a drained-count mismatch prevent `capture_complete=true`.

## Source-native details

Engine-specific operation names and measurements remain bounded labels/values or namespaced metadata in the producer contract. They do not expand the common top-level envelope or introduce a second importer. A source-specific rule may tighten validation, but may not weaken common privacy, identity, integer, lifecycle, summary or correlation invariants.

## Host-only verification

Run the focused tests in CI:

```sh
python -m unittest tests.test_nepenthes_llama_trace_import tests.test_nepenthes_trace_envelope
```

These fixtures establish software-level envelope compatibility only. They do not establish runtime instrumentation, GPU capture, Nsight correlation, C07, C08 or physical engine acceptance.
