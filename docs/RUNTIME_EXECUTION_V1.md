# runtime-execution.v1

## Purpose

`runtime-execution.v1` is the physical-execution contract that sits between the declarative V1.1 runtime selection layer and the evidence layer.

It is intentionally stricter than `runtime-benchmark.v1`: a benchmark record may describe a completed measurement, but a runtime execution artifact must preserve enough information to reproduce, audit and verify the exact execution that produced it.

The invariant is:

```text
selection
  -> frozen execution plan
  -> host preflight
  -> runner
  -> physical execution
  -> raw stdout/stderr + exit status
  -> measured observations
  -> runtime-execution.v1
  -> runtime-benchmark.v1
  -> evidence
```

No declaration, estimate, benchmark copied from another source, or adapter metadata can be promoted to physical execution evidence.

## Contract invariants

1. **One execution, one `execution_id`.** A retry is a new execution, never an overwrite.
2. **The selection plan is frozen.** The artifact records a SHA-256 hash of the exact plan used.
3. **The model is immutable by identity.** Record model ID, revision, quantization, format and the exact artifact SHA-256.
4. **The runtime is immutable by identity.** Record runtime ID, adapter, exact installed version, backend and entrypoint kind.
5. **The host is explicit.** Record OS/version/kernel, architecture, CPU, RAM, GPU/VRAM and memory bandwidth when available.
6. **The command is preserved.** Record the exact argv and working directory. Secrets must never be written into the artifact.
7. **The protocol is frozen before measurement.** The artifact records protocol ID/version, warm-up count, measurement count and aggregation rule.
8. **Raw process evidence is retained.** stdout/stderr are stored as separate artifacts and their SHA-256 hashes are recorded in the execution record.
9. **Observed metrics are separate from estimates.** `estimated_tps` is never accepted as a physical measurement field.
10. **Failure is evidence too.** Failed/aborted executions retain the same identity and raw process evidence, but cannot become successful performance measurements.
11. **Derived metrics remain derived.** TTFT, TPOT, tokens/s, memory and power must identify their observation source and calculation when they are not directly emitted by the runtime.
12. **Evidence is append-only.** A corrected or repeated execution produces a new artifact and a new `execution_id`.

## Required identity

### Execution

- `schema_version`: `runtime-execution.v1`
- `execution_id`
- `execution_status`: `planned | started | completed | failed | aborted`
- `selection.selection_status`
- `selection.selection_plan_hash`: `sha256:<64 hex>`

### Runtime

- `id`
- `adapter`
- exact installed `version`
- `backend`
- `entrypoint_kind`

The version must come from the physical host, not from the registry placeholder `declared-by-host`.

### Model/artifact

- model ID
- model revision/commit
- quantization
- format
- architecture where known
- artifact URI/path
- artifact SHA-256
- artifact size

For a directory or multi-file model, hash a canonical manifest containing relative paths, sizes and per-file SHA-256 values; record the manifest hash as the artifact hash.

## Host fingerprint

At minimum:

- OS and version
- kernel
- CPU model
- architecture
- total RAM
- GPU model(s), if present
- VRAM, if available
- memory bandwidth, if available

Do not substitute generic hardware classes for physical identity. A statement such as `RTX 4060 class` belongs to analysis, not execution evidence.

## Workload contract

The workload must be deterministic enough to compare runs:

- stable `prompt_id`
- target input tokens
- target output tokens
- context length
- concurrency
- chat template identity when applicable
- decoding parameters
- seed when the runtime supports deterministic sampling
- stop conditions

A benchmark that changes prompt, context, quantization, decoding or concurrency is a different workload, not a continuation of the same result.

## Measurement protocol

The execution artifact records the frozen protocol:

- `protocol_id`
- `protocol_version`
- warm-up runs
- measurement runs
- aggregation rule
- `frozen=true`

The protocol is frozen before the final measurement set. This follows the source methodology: development evaluation and final evaluation must be separated, and the final test protocol must not be optimized after seeing results. fileciteturn0file0L1172-L1207

## Process evidence

The runner must preserve:

- exact argv
- working directory
- allowed environment variable names, not secret values
- start timestamp
- finish timestamp
- exit code
- stdout artifact + SHA-256
- stderr artifact + SHA-256

The raw streams are authoritative observations. Parsed metrics are derived from them unless the measurement source is an OS/device counter explicitly identified in the record.

## Metrics

Primary metrics for the first physical protocol:

- TTFT in milliseconds
- TPOT in milliseconds/token
- output tokens/second
- input token count
- output token count
- peak RAM
- peak VRAM when available
- power in watts when a trustworthy counter exists

For a service runtime, add request/s, concurrency and p50/p95/p99 latency once the serving protocol is introduced. The reference LLM study explicitly recommends TTFT, TPOT, tokens/s, memory, hardware, runtime version and workload rather than a single tokens/s number. fileciteturn0file0L381-L414

## Relationship with runtime-benchmark.v1

`runtime-execution.v1` is the physical evidence envelope. `runtime-benchmark.v1` is the normalized benchmark boundary used by LEONES.

Conversion is allowed only when:

- execution status is `completed`;
- the process exited successfully;
- model/runtime/host identity is present;
- the exact artifact hash is present;
- stdout/stderr hashes are present;
- the protocol is frozen;
- at least one physical observation exists;
- no estimate is being represented as a measurement.

The normalized benchmark must retain the `execution_id` and artifact hashes so that every measured value can be traced back to raw execution evidence.

## Failure semantics

- `failed`: the runtime process executed but did not produce a valid completed measurement.
- `aborted`: the runner deliberately stopped execution or the host became unavailable.
- `completed`: process completed and the measurement protocol produced valid observations.

A failed execution is never silently retried under the same ID.

## Security boundary

The execution artifact must not contain:

- API keys
- passwords
- tokens
- cookies
- private SSH material
- full process environments

Only an explicit allowlist of environment variable names may be recorded. If a command contains a secret, the execution must be marked invalid and repeated with a sanitized command representation.

## Immutability rule

The final JSON artifact is hashed after creation:

`provenance.artifact_hash = sha256:<hash>`

If any field changes after completion, the artifact hash changes and the original evidence is considered superseded rather than edited.

## What Debian will do

When Debian is available, there should be no architecture work left:

1. verify host fingerprint;
2. verify exact model artifact and hash;
3. resolve the frozen runtime selection plan;
4. run host preflight;
5. execute the exact command;
6. capture stdout/stderr and exit code;
7. run warm-up;
8. run the frozen measurement set;
9. collect metrics;
10. write `runtime-execution.v1`;
11. validate the artifact against the schema;
12. convert it to `runtime-benchmark.v1`;
13. bridge it to evidence;
14. preserve the raw artifacts.

The Debian phase therefore becomes **execute → measure → preserve evidence**, exactly as intended.
