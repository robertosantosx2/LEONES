# NEPENTHES llama.cpp trace importer

The importer validates and summarizes the JSONL runtime trace produced by llama.cpp when NEPENTHES_TRACE_JSONL is enabled.

## Usage

```bash
python3 scripts/nepenthes_llama_trace_import.py \
  "$HOME/nepenthes-run.jsonl" \
  --output "$HOME/nepenthes-run.summary.json"
```

For an interrupted process that did not write its final sink_summary record, explicitly opt in:

```bash
python3 scripts/nepenthes_llama_trace_import.py trace.jsonl \
  --output trace.summary.json \
  --allow-incomplete
```

The importer does not modify the original trace. It writes a JSON summary atomically and records the input SHA-256.

## Validation

- Requires schema version 1.0 and source llama.cpp.
- Requires a single run_id, unique event_id values, non-negative integer timestamps/values and a final sink_summary.
- Verifies events_drained against parsed event count.
- Rejects prompt, completion, response, text and token payload fields.
- Preserves unknown event_kind values in counters rather than silently discarding them.
- Reports event-kind/label counts, duration min/max/mean, request start/end balance, monotonic timestamp min/max, dropped events and writer errors.
- capture_complete is true only when the final sink summary exists, no events were dropped, no writer errors occurred and the drained count matches the imported event count.

Queue loss, writer errors, missing summaries or count mismatches are surfaced as incomplete capture quality, never normalized into a successful run. Request lifecycle imbalance is reported separately because a server may be shut down while a request is still active.

## Scope

The importer intentionally does not infer GPU kernel duration from host dispatch spans, does not treat asynchronous transfer submission as device completion, and does not correlate request_id=0 internal events to requests. Energy and device telemetry continue to come from the separate NVML/AIPerf inputs.


## Correlation and clock fields (schema 1.0 extension)

The importer accepts the optional event fields:

- correlation_token: null or a positive unsigned 64-bit integer.
- attribution_level: null, exact, windowed, device_wide or estimated.
- clock_domain: steady_clock for the current llama.cpp source.

An exact attribution record must carry a token. A token without exact attribution is rejected. The importer does not infer correlation from temporal proximity. Request token start/end balance is reported independently from native request_id balance.

clock_calibration events must include a non-zero timestamp_unix_ns and clock_domain=steady_clock. The importer sorts calibration points by monotonic_ns, reports start/end wall-to-monotonic offsets and drift in ppm, and explicitly reports that Nsight is not calibrated by host-only events. Ordinary high-frequency events may use timestamp_unix_ns=0; the monotonic clock remains authoritative for within-run ordering and duration.

Older schema 1.0 traces without these optional fields remain accepted. The original JSONL is preserved and its SHA-256 remains part of the summary.
