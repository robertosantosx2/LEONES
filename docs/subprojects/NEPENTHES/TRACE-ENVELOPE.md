# NEPENTHES shared trace envelope

**Status:** host-only validator implementation is in [LEONES PR #210](https://github.com/robertosantosx2/LEONES/pull/210), open and ready for review. Exact code/test HEAD `262d3f8db254d27b099d6d0dc4a92826bdbd253c` passed all 10 GitHub Actions checks, including 27 focused importer tests and the full repository suite (600 passed, 8 subtests passed). The current PR head adds only INDEX/documentation updates after that code/test HEAD. This contract is not accepted until PR review and merge; it does not claim that a TensorFold runtime producer exists.

## Ownership and entry point

LEONES owns one common JSONL envelope validator in `scripts/nepenthes_trace_envelope.py`. The existing `scripts/nepenthes_llama_trace_import.py` remains the compatibility entry point and aggregator; it delegates envelope checks to the shared module. TensorFold uses the same entry point with an explicit source selector:

```bash
python3 scripts/nepenthes_llama_trace_import.py tensorfold-trace.jsonl \
  --source tensorfold --output tensorfold-trace.summary.json
```

The default source remains `llama.cpp`. There is no TensorFold-specific importer or alternate schema.

## Closed source registry

The registry is explicit and fail-closed. A source must be added to `SOURCE_PROFILES` in a reviewed change before it can be imported.

| Source | Registered | Accepted clock domain | Notes |
|---|---:|---|---|
| `llama.cpp` | Yes | `steady_clock` | Existing compatibility profile; default CLI source |
| `tensorfold` | Yes | `steady_clock` | Matches the TensorFold 1.2.10 integration contract |
| `tandem.cpp` | Yes | `steady_clock` | Preserves the distinct source identity of the llama.cpp-derived connector |
| Any other value | No | None | Rejected before records are accepted |

The selected source is an expected identity, not a coercion: every event and the final `sink_summary` must contain exactly that source. An event/summary mismatch fails closed. A caller cannot pass an arbitrary source name to extend the registry.

## Common event envelope

Schema `1.0` requires these fields for every ordinary event:

| Field | Type / constraint |
|---|---|
| `schema_version` | Exact string `1.0` |
| `run_id` | Non-empty string; one value per file |
| `event_id` | Non-empty string; unique within the trace including summary |
| `source` | Exact registered source selected for this import |
| `timestamp_unix_ns` | Unsigned 64-bit integer |
| `monotonic_ns` | Unsigned 64-bit integer |
| `request_id` | Unsigned 64-bit integer; zero means no request attribution |
| `event_kind` | Non-empty string |
| `label` | String |
| `value0`, `value1` | Unsigned 64-bit integers |
| `duration_ns` | Unsigned 64-bit integer; zero when no duration is measured |
| `flags` | Unsigned 16-bit integer |

Optional common fields:

- `correlation_token`: null or positive unsigned 64-bit integer.
- `attribution_level`: `exact`, `windowed`, `device_wide` or `estimated`.
- `clock_domain`: when present, must be declared by the selected source profile.

Common semantic rules:

- `exact` requires an explicit non-zero `correlation_token`; a token with any other attribution level is rejected.
- `clock_calibration` requires a non-zero wall-clock timestamp and the declared `steady_clock` domain.
- No request/kernel relationship is inferred from timestamp proximity.
- `request_id=0` remains unassociated with a request.
- Unknown non-empty event-kind strings are retained/countable rather than silently discarded; connectors must still emit only semantically observed operations.
- Booleans are not integers for any numeric field. Negative and out-of-range values are rejected.

## Source-specific rules

The registry records each connector's accepted clock domain and source-specific lifecycle semantics. All three contracts use `steady_clock`. TensorFold and Tandem.cpp require a non-zero `request_id` on `request_start` and `request_end`; `request_id=0` remains valid for internal events. llama.cpp retains its existing behavior. The profile boundary prevents one connector from inheriting another connector's assumptions implicitly.

No source-specific event-kind allowlist is imposed in this slice: all registered connectors map observations to the common event vocabulary, and the importer preserves unknown non-empty labels/kinds for forward compatibility. Any future source-specific semantic constraint must be added to its profile and covered by positive and negative fixtures; it must not weaken common envelope checks.

Engine-native details belong in namespaced metadata or a source-specific summary extension only after the summary schema is explicitly versioned. The current canonical summary is intentionally exact-shape and rejects extra fields.

## Final sink summary

A complete file ends with exactly one `sink_summary` record. It contains exactly:

- `schema_version`, `run_id`, `event_id`, `source`, `timestamp_unix_ns`;
- `event_kind=sink_summary`;
- `events_drained`, `dropped_events`, `write_errors`.

All summary counters/timestamps are unsigned 64-bit integers. The summary source and run ID must match the event stream. Its event ID must be unique. It must be the final non-empty record, and `events_drained` must equal the parsed event count. Drops, writer errors or a drained-count mismatch make the capture incomplete. Missing summary is rejected unless `--allow-incomplete` is explicitly selected; that option never upgrades an incomplete capture.

## Privacy

The validator rejects records containing prompt, completion, response, text, token, token-ID, input-text or output-text fields. Do not add credentials, environment dumps, local paths, hostnames, request content or model inputs to the event envelope.

## Evidence boundary

The shared validator and its fixtures are host-only. Passing this importer does not prove that a connector emits correct runtime events, that a request lifecycle is instrumented, that a CUDA operation completed, or that Nsight correlation/overhead is accepted. TensorFold runtime implementation is a later slice after #207 acceptance and separate host-only connector tests.
