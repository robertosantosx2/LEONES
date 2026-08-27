# Runtime Benchmark Evidence V1.1

LEONES adopts the useful parts of the Artificial Analysis methodology while keeping local-runtime evidence distinct from hosted API measurements.

Artificial Analysis measures real-world end-to-end inference experience, not theoretical maximum hardware performance. Its language-model API methodology separates workload size, load scenario, TTFT, output speed and end-to-end response time, and uses repeatable API parameters and standardized token counting for cross-model comparisons. See https://artificialanalysis.ai/methodology and https://artificialanalysis.ai/methodology/performance-benchmarking.

## LEONES mapping

| Artificial Analysis concept | LEONES local evidence |
| --- | --- |
| Model / provider / endpoint | model / runtime / artifact |
| Workload type | prompt protocol + context + output limit |
| Single prompt | one local process execution per iteration |
| Parallel prompts | future concurrency profile; not mixed with single-request results |
| TTFT | local first-output latency; explicitly scoped as local-process timing |
| Output speed | tokens/s parsed from runtime output when available |
| End-to-end response time | total process/request time |
| Median / distribution | per-iteration records plus aggregate summary |
| Provider configuration | exact runtime version, backend, command and hardware |
| Point-in-time result | execution_id + UTC timestamps |
| Artifact identity | path + size + SHA-256 |

## Important comparability rule

A local `llama-cli` run is **not** directly equivalent to an Artificial Analysis hosted API TTFT. The local first-output measurement includes local process startup and model loading unless the runtime is already resident behind a server. Therefore LEONES records the measurement scope and does not silently merge local and API latency series.

For cross-runtime local comparisons, use the same model artifact, prompt protocol, context, output limit, warm-up policy, iteration count and hardware. For API comparisons, use a separate hosted-endpoint protocol.

## Canonical fields

The JSON contract is `schemas/runtime-benchmark-evidence.v1.1.json`.

Required identity:

- model id/name/revision
- quantization
- artifact path/size/SHA-256
- context length
- runtime name/version/command
- hardware
- prompt protocol
- warm-up count
- measurement count
- execution_id
- UTC timestamps

Required evidence:

- stdout/stderr
- exit code
- per-iteration total time
- first-output latency / TTFT when measurable
- output speed when the runtime reports it
- memory and VRAM when measurable
- power when measurable
- aggregate mean/median/min/max and standard deviation when enough samples exist

## First llama.cpp run

Prepare a shell-free command JSON, for example:

```json
["llama-cli", "-m", "/path/to/model.gguf", "-p", "Explain why reproducible benchmarks matter.", "-c", "4096", "-n", "256", "--temp", "0"]
```

Then run:

```bash
python3 scripts/runtime_benchmark_evidence.py \
  --command-json artifacts/llama-cpp-command.json \
  --output artifacts/real-llama-cpp-evidence.json \
  --artifact /path/to/model.gguf \
  --model-id <stable-model-id> \
  --model-name <model-name> \
  --model-revision <immutable-revision> \
  --quantization Q4_K_M \
  --context 4096 \
  --prompt-protocol-id leones-local-v1 \
  --prompt 'Explain why reproducible benchmarks matter.' \
  --warmup 2 \
  --iterations 5 \
  --runtime llama.cpp
```

The generated evidence is suitable for later ingestion into the LEONES evidence layer. It must not be hand-edited after measurement; if corrected, rerun the measurement and generate a new `execution_id`.

## Validation gate

A result is valid only when all measurement iterations exit successfully and the required identity/provenance fields are present. Missing optional telemetry such as power or VRAM is recorded as unavailable rather than fabricated.
