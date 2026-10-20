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

## Recorded three-runtime Qwen3.5-4B run — 2026-10-20

A three-trial, single-request API snapshot was recorded on Ubuntu with an RTX 3050 Laptop GPU. The run uses a 32-token completion cap and excludes the separate warm-up record. Because TensorFold used MLX-4bit while llama.cpp and RustingStrata used GGUF Q4_K_M, treat this as a practical runtime comparison, not a strict same-artifact benchmark.

- Detailed report: [`docs/benchmarks/qwen35-4b-three-runtimes-2026-10-20.md`](benchmarks/qwen35-4b-three-runtimes-2026-10-20.md)
- Per-trial CSV: [`docs/benchmarks/qwen35-4b-three-runtimes-2026-10-20.csv`](benchmarks/qwen35-4b-three-runtimes-2026-10-20.csv)
- TensorFold median: 54.708 output tok/s; 0.7066 s total request time; 0.1303 s TTFT.
- llama.cpp CUDA median: 47.646 output tok/s; 0.8680 s total request time; comparable client-side TTFT unavailable.
- RustingStrata median: 0.8384 s total request time; its API did not expose internal output tok/s or TTFT. The report labels 32 / total request time only as an estimate, not as internal decode throughput.

All nine measured requests returned HTTP 200 and 32 completion tokens. The benchmark script's final report step had a Python syntax error after measurement; the report and CSV were reconstructed from the existing per-trial JSONL without rerunning the engines. Full raw JSONL and server logs remain in the original local run directory and are not claimed to be committed in this repository.


## Follow-up four-runtime Qwen3.5-4B run — 2026-10-20

A separate four-runtime run was completed on the same Ubuntu workstation (Intel Core i7-12650H, 14 GiB RAM, RTX 3050 Laptop GPU with 4 GiB VRAM). It used context 256, temperature 0, a 32-token completion cap, one uncounted warm-up per engine and three measured requests per engine. All 12 measured requests returned HTTP 200 and 32 completion tokens.

- Detailed report: [Qwen3.5-4B four-runtime benchmark](benchmarks/qwen35-4b-four-engines-2026-10-20.md).
- Per-trial CSV: [four-runtime measurements](benchmarks/qwen35-4b-four-engines-2026-10-20.csv).
- TensorFold median: 54.747 output tok/s; 0.7079 s total request time; 0.1308 s TTFT.
- llama.cpp CUDA median: 47.551 output tok/s; 0.8860 s total request time; client-side TTFT unavailable.
- RustingStrata median: 0.8416 s total request time; internal output speed, prefill and TTFT were not exposed by its API.
- Mistral.rs median: 6.202 output tok/s; 6.2367 s total request time; TTFT unavailable.
- TensorFold used MLX-4bit; the other three runtimes used GGUF Q4_K_M. Treat the run as a practical comparison, not a same-artifact microbenchmark.

The benchmark script's report-generation step failed after the measurements due to an unmatched closing parenthesis. The report and CSV were reconstructed from the existing JSONL; engines were not rerun to fix report generation. The full raw JSONL and server logs remain in the local run directory and are not claimed to be uploaded here.
