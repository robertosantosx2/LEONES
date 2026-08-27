# JALON 2 — Physical evidence bridge

The physical runtime path is now separated from the evidence contract. A real
`llama.cpp` log is converted by `scripts/jalon2_llama_cpp_evidence.py` into
`runtime-benchmark-evidence.v1.1` without inventing missing measurements.

## Contract

The bridge preserves:

- execution id and explicit UTC start/end timestamps;
- model identifier, quantization, artifact SHA-256 and size;
- prompt protocol, context, warm-up and output limit;
- exact timed command as an argv array;
- runtime version, binary and binary SHA-256;
- host, OS, kernel, CPU, cores/threads and RAM;
- TTFT/prompt-eval time when emitted by llama.cpp;
- generation time, output tokens and tokens/s when emitted by llama.cpp;
- wall time and maximum RSS from `/usr/bin/time`;
- exit status and the original captured log.

The parser deliberately leaves unavailable metrics as `null`. It does not
turn wall time into a synthetic tokens/s measurement.

## Physical run integration

The physical runner should emit these provenance lines before inference:

```text
execution_id=...
timestamp_utc=...
host=...
os=...
kernel=...
cpu=...
cpu_threads=...
physical_cores=...
runtime=llama.cpp
runtime_version=...
runtime_package=...
runtime_binary=...
runtime_binary_sha256=...
model=...
model_size_bytes=...
model_sha256=...
threads=...
threads_batch=...
ctx_size=...
n_predict=...
warmup=enabled
perf=enabled
single_turn=enabled
prompt_sha256=...
```

The runner must append `timestamp_end_utc=...` **after** the runtime process
has completed. This timestamp is intentionally explicit; the evidence writer
must not use evidence-generation time as execution time.

The inference command should be wrapped by `/usr/bin/time -v` so wall time
and maximum resident set size are retained. llama.cpp should be invoked with
`--perf` so prompt/generation performance can be parsed when supported by the
installed build.

## Example conversion

```bash
python3 scripts/jalon2_llama_cpp_evidence.py \
  --log artifacts/runs/jalon2/jalon2-ubuntu-qwen3-0.6b-q4km-YYYYMMDDTHHMMSSZ.log \
  --timestamp-end 2026-08-27T14:06:15Z \
  --out artifacts/jalon2/runtime-benchmark-evidence.v1.1.json
```

The end timestamp above is only an example. For a real evidence record it must
come from the physical runner at process completion.

## Gate

Before merging the bridge:

```bash
python3 -m pytest tests -q
python3 -m pytest tests/test_jalon2_llama_cpp_evidence.py -q
```

A valid JALON 2 evidence record is the one produced by the physical run and
validated against `schemas/runtime-benchmark-evidence.v1.1.json`; existing
SmolLM2 evidence must not be mixed with the Qwen3 physical run.
