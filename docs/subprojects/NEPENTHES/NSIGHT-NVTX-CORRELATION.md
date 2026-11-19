# NEPENTHES — NVTX request correlation and clock calibration

## Runtime marker contract

CUDA builds that find NVTX v3 emit instantaneous markers:

- `nepenthes.request.start token=<uint64> request=<native-id>`
- `nepenthes.request.end token=<uint64> request=<native-id>`

The JSONL sink records a matching `nvtx_marker` event with the same correlation token, phase label, and host-monotonic call bracket in `value0/value1`. The marker itself is an exact identity event; it does not make the GPU work inside its time window exact-attributed.

## Nsight import

The importer reads `NVTX_EVENTS`, resolves text IDs when possible, and parses only the explicit NEPENTHES marker format. It matches markers to JSONL by `(correlation_token, phase)`, never by temporal proximity.

For each matched marker, the midpoint of the host-monotonic call bracket is paired with the Nsight NVTX timestamp. The report stores:
- matched marker-pair count;
- host-monotonic to Nsight offset at first/last pair;
- drift in ns and ppm when at least two distinct host times exist;
- maximum half-bracket uncertainty;
- each matched token/phase pair.

Host-only `clock_calibration` events do not calibrate Nsight. Nsight-only imports have no host clock calibration.

## Windowed attribution

Start/end NVTX markers for the same token define an explicit request window in the Nsight clock domain. A CUDA kernel/memcpy/memset activity is assigned `attribution_level=windowed` only when exactly one complete request window contains the activity interval.

- One matching window → token + `windowed`.
- Multiple overlapping windows → no token, `overlapping_request_windows`.
- No complete window → no token, `outside_or_missing_request_window`.
- The NVTX marker row itself carries exact marker identity.

This does not infer by proximity and does not claim exact CUPTI correlation. Activities that cross request boundaries or outlive the marker window remain unattributed. CUPTI external correlation IDs are a separate future layer.

## Nsight-only mode

Nsight-only import can recover tokenized NVTX windows and apply windowed attribution among Nsight activities because those timestamps share the Nsight clock. It cannot produce host↔Nsight clock calibration or claim a paired NEPENTHES run.

## Validation

Synthetic fixtures cover marker parsing, host↔Nsight offset/drift, unique-window attribution, outside-window activities, and overlapping-window ambiguity. The C07 real Nsight capture and the CUDA/NVTX CI build remain required acceptance gates.
