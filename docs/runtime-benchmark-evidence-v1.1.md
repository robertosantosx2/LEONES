# Runtime Benchmark Evidence V1.1

This is the operational contract for converting a real runtime execution into reusable LEONES evidence.

## Canonical implementation

- Schema: `schemas/runtime-benchmark-evidence.v1.1.json`
- Runner: `scripts/runtime_benchmark_evidence.py`
- Contract tests: `tests/test_runtime_benchmark_evidence_v1_1_contract.py`
- CI gate: `.github/workflows/jalon3-runtime-execution-contract.yml`

## Required identity

Every valid evidence object records:

- `execution_id`;
- UTC start/end timestamps;
- model id/name/revision;
- quantization and context length;
- model artifact path, size and SHA-256;
- prompt protocol and measurement scope;
- warm-up and measurement counts;
- runtime name/version/command;
- hardware identity and available telemetry;
- per-iteration measurements;
- aggregate statistics;
- complete stdout/stderr;
- process exit status;
- artifact path/size/SHA-256.

## Local latency semantics

For a local process such as `llama-cli`, `first_output_ms` and `ttft_ms` are scoped as `local_process_first_output`. They can include process startup and model loading.

They are **not** silently treated as hosted-API TTFT. Local and API latency datasets remain separate unless a later protocol explicitly defines a valid comparison.

## Measurement protocol

Warm-up executions are excluded from the measured sample. Every measured iteration is preserved individually. Aggregation provides mean, median, minimum, maximum and, with more than one sample, standard deviation.

Changing model, revision, quantization, artifact, runtime, runtime version/revision, backend, hardware, workload or protocol creates a new `execution_id`.

## Metrics

Per iteration, the contract supports:

- first-output latency / local TTFT;
- generation time;
- output token count;
- output tokens/s;
- total wall time;
- peak RAM;
- peak VRAM;
- power.

Optional telemetry is `null` when unavailable. It is never fabricated.

## Shell-free execution

Commands are supplied as JSON arrays and executed without `shell=True`. Exact argument boundaries are therefore preserved.

Example command payload:

```json
["llama-cli", "-m", "/path/to/model.gguf", "-p", "Explain reproducible benchmarks.", "-c", "4096", "-n", "256"]
```

## Validation

CI performs four engineering checks:

1. Python compilation of the runner;
2. Draft 2020-12 schema validation;
3. contract tests for timing, stdout/stderr separation, statistics and rejection rules;
4. repository-level traceability through the JALON 3 documentation.

Ordinary CI deliberately does **not** claim to perform a physical model benchmark. Physical execution belongs to the target host.

## Physical hand-off

Once the GitHub engineering gate is green, Debian/Ubuntu should only:

1. update to the approved GitHub revision;
2. verify the installed runtime/build;
3. verify the real model artifact and hash;
4. execute the approved shell-free command;
5. perform the configured warm-up;
6. perform the configured iterations;
7. preserve stdout/stderr and generated evidence;
8. validate and archive the result.

No protocol design should be required on the physical host.

## Methodological reference

Artificial Analysis is used as a conceptual reference for separating workload, latency, output speed and end-to-end response characteristics. LEONES preserves the distinction between local-runtime measurements and hosted-API measurements.
