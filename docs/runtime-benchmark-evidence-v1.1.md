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


## Robust telemetry and paired instrumentation conditions

The runner records median, p25, p75, IQR and MAD in addition to mean/min/max/stdev. During each child execution it samples process RSS and system RAM from procfs, and GPU-0 device-wide VRAM/power with a configurable low-frequency NVML/nvidia-smi loop. These scopes are explicit:

- `peak_process_rss_mb`: peak RSS of the directly launched child process, not its complete descendant tree.
- `peak_system_ram_used_mb`: system-wide used RAM; not attributed to the inference process.
- `peak_vram_mb_device_wide`: device-wide GPU memory, not process-attributed.
- `mean_power_w` / `peak_power_w`: sampled device-wide power, not energy or process-attributed power.

The legacy `peak_memory_mb`, `peak_vram_mb` and `power_w` fields remain for compatibility; use the explicitly scoped new fields for overhead acceptance. Missing samples remain null.

The runner accepts instrumentation metadata:
- `condition`: `off`, `jsonl`, `nsys` or `combined`.
- `pair_id`: stable identifier shared by the four conditions in one paired repetition.
- `profile`: NEPENTHES capture profile.
- `dataset_sha256`, `hardware_id`, `sampling_config` and sampling intervals.

## C08 — formal overhead gate

Run at least three independent paired repetitions per condition, with at least one warm-up and three measured iterations in each evidence file. Keep model artifact SHA-256, engine revision, prompt hash/protocol, context, sampling, backend, hardware and telemetry intervals identical. Change only the instrumentation condition.

Conditions:
1. `off`: runtime sink off, Nsight off.
2. `jsonl`: JSONL sink on, Nsight off.
3. `nsys`: Nsight on, JSONL sink off (NVTX markers may be captured by Nsight independently).
4. `combined`: JSONL sink and Nsight on.

Example command for each evidence file:

```bash
python3 scripts/runtime_benchmark_evidence.py \
  --command-json artifacts/command.json --output artifacts/off-pair-01.json \
  --artifact /path/to/model.gguf --model-id model-id --model-name model-name \
  --model-revision immutable-model-revision --quantization Q4_K_M --context 4096 \
  --prompt-protocol-id nepenthes-c08-v1 --prompt 'fixed prompt' \
  --warmup 1 --iterations 5 --condition off --pair-id pair-01 \
  --profile standard --engine-revision ENGINE_SHA --hardware-id msi-rtx3050
```

Repeat with the same `pair-id` for jsonl, nsys and combined, changing only the instrumentation condition and the corresponding runtime flags.

Then compare all evidence files:

```bash
python3 scripts/nepenthes_overhead_gate.py \
  --evidence artifacts/*-pair-*.json --profile standard \
  --min-pairs 3 --max-decode-overhead 5 --warn-decode-overhead 8 \
  --output artifacts/c08-overhead-report.json
```

The comparator rejects missing conditions, mismatched pair IDs, failed runs, incompatible model/protocol/runtime/hardware/sampling fingerprints and fewer than three pairs. It reports paired percentage deltas using median, IQR and MAD. Decode overhead is `(baseline_tokens_per_second - instrumented_tokens_per_second) / baseline_tokens_per_second * 100`.

For `standard`:
- Median decode overhead ≤5%: accepted target.
- >5% and ≤8%: exception required; do not claim low-overhead acceptance.
- >8%: blocked.

The comparator reports TTFT, generation/total time, process RSS, system RAM, device-wide VRAM and sampled power separately. Device-wide memory/power are not process attribution. Full/diagnostic profiles are informational and are not labelled low-overhead.

The harness and comparator are implemented and synthetically tested in GitHub. C08 itself remains pending until real paired runs are executed on the MSI; no overhead percentage is claimed before those measurements.
