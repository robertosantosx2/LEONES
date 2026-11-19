# NEPENTHES llama.cpp trace importer

The standalone importer validates and summarizes the JSONL runtime trace emitted by the native llama.cpp NEPENTHES sink. It does not rewrite or delete the source trace.

## Usage

```bash
python3 scripts/nepenthes_llama_trace_import.py \
  "$HOME/nepenthes-run.jsonl" \
  --output "$HOME/nepenthes-run.summary.json"
```

For an interrupted process that did not write its final `sink_summary` record, opt in explicitly:

```bash
python3 scripts/nepenthes_llama_trace_import.py trace.jsonl \
  --output trace.summary.json \
  --allow-incomplete
```

The importer writes the summary atomically and records the input filename, size and SHA-256. The original JSONL remains the source of truth.

## Producer contract currently used by llama.cpp RC1

The native RC1 JSONL sink currently emits `schema_version: "1.0"` and `source: "llama.cpp"`. Required event fields are:

- `run_id`, unique `event_id`, `timestamp_unix_ns`, `monotonic_ns`, `request_id`;
- `event_kind`, `label`, `value0`, `value1`, `duration_ns`, `flags`.

The producer uses unsigned 64-bit values for timestamps, IDs, durations and values. The importer rejects booleans, negative values and malformed JSONL records. `flags` is restricted to the 16-bit range.

The final `sink_summary` record is mandatory for a complete capture. Its `events_drained` count must match the number of parsed event records; `dropped_events` and `write_errors` must both be zero. Missing summary, dropped records, writer errors or count mismatches make the capture incomplete. Use `--allow-incomplete` only for an interrupted trace; it never upgrades the result to complete.

## Explicit correlation and host clock fields

Schema 1.0 may include these optional fields:

- `correlation_token`: null or a positive unsigned 64-bit integer.
- `attribution_level`: null, `exact`, `windowed`, `device_wide` or `estimated`.
- `clock_domain`: `steady_clock` for the current llama.cpp source.

An `exact` attribution requires a token. A token without `exact` attribution is rejected. The importer never correlates events by temporal proximity. Token start/end balance is reported independently from native `request_id` balance.

A `clock_calibration` event requires a non-zero `timestamp_unix_ns` and `clock_domain=steady_clock`. The importer sorts calibration points by monotonic time and reports start/end wall-to-monotonic offsets and drift in ppm. Host-only calibration does not calibrate Nsight's clock.

Ordinary high-frequency events may use `timestamp_unix_ns=0`; the monotonic clock remains authoritative for within-run ordering and durations.

## Typed schema 1.1 is a separate importer contract

The paired JSONL + Nsight importer, `scripts/nepenthes_nsys_import.py`, also accepts typed schema 1.1 events. It validates and persists fields such as backend, memory kind, memcpy kind, raw memcpy enum, synchronization type and KV operation, while preserving the complete original event JSON.

Do not infer that the standalone summary importer accepts every typed schema 1.1 field merely because the paired importer does. The native RC1 sink currently emits schema 1.0 with the optional correlation fields above. If the producer is upgraded to emit schema 1.1, this standalone importer must be extended and tested in the same change.

## Privacy and semantic limits

The importer rejects prompt, completion, response, text and token-payload fields. Unknown `event_kind` values are counted rather than silently discarded.

It does not infer GPU kernel duration from host dispatch spans, does not treat asynchronous transfer submission as device completion, and does not correlate `request_id=0` internal events to requests. GPU activity and device telemetry continue to come from Nsight Systems/CUPTI and NVML/AIPerf respectively.
