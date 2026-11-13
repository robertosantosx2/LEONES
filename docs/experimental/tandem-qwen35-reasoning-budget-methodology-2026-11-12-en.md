# NEPENTHES: Reproducible Methodology · Tandem.cpp / Qwen3.5-35B-A3B · 2026-11-12

**Status:** documentation and scripts published. Original binary/JSON logs and the complete host snapshot are to be added when the collector is run on the MSI.

## Objective

Separate two variables in comparable experiments:

1. **Same engine, different model:** keep the engine, build, server parameters, and host unchanged; change only the model.
2. **Same model, different engine:** keep exactly the same GGUF and host; change the engine. Configure the alternative engine with the same context, template, quantization, and equivalent parameters.

The runner does not start, stop, or reconfigure processes. It only sends requests to an already-running OpenAI-compatible endpoint.

## Fixed test battery

Requests use temperature 0, stream false, reasoning_format deepseek, and enable_thinking true.

| Task | Budget | max_tokens |
|---|---:|---:|
| Arithmetic 17 × 23 | 64 | 256 |
| Arithmetic 17 × 23 | 128 | 384 |
| Arithmetic 17 × 23 | 256 | 512 |
| two_sum | 128 | 512 |
| two_sum | 128 | 768 |
| two_sum | 256 | 1024 |
| two_sum | 128 | 1536 |
| two_sum | 256 | 1536 |
| binary_search | 128 | 1536 |
| binary_search | 256 | 1536 |

Literal prompts are embedded in `run_battery.py`. The matrix reproduces the distinct combinations recorded in the campaign; repetitions that returned the same ID are not counted as independent samples.

## Scripts

All scripts are in this experiment's `repro` directory:

- [run_battery.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_battery.py): common client. Saves the complete JSON for each request/response, `summary.jsonl`, `run_manifest.json`, and captures `/health` and `/props`.
- [repeat_same_engine_new_model.sh](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/repeat_same_engine_new_model.sh): changes the model while keeping the endpoint/engine.
- [repeat_same_model_new_engine.sh](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/repeat_same_model_new_engine.sh): changes the engine while keeping the GGUF.
- [collect_evidence.sh](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/collect_evidence.sh): copies existing logs and metadata and captures system, GPU, CUDA, process, and commit information. Generates a tar.gz and SHA256SUMS.

## Requirements

- Ubuntu/Linux.
- Python 3.10 or later (standard library only).
- `curl`, `tar`, `sha256sum`, `lscpu`, `free`, `swapon`; `nvidia-smi` and `nvcc` when installed.
- An already-running server with an OpenAI-compatible API.
- The model must be loaded before running the battery.

## A. Repeat with the same engine and a different model

Example for a different model served by Tandem.cpp at the existing endpoint:

~~~bash
cd /path/to/repro

MODEL_ID='model-alias-in-the-API' \
MODEL_PATH="$HOME/models/another-model.gguf" \
BASE_URL='http://127.0.0.1:18086' \
ENGINE_LABEL='tandem.cpp' \
bash repeat_same_engine_new_model.sh
~~~

Do not change the build, server configuration, or environment during the comparison. Record any unavoidable difference (maximum supported context, template, offload, quantization, or cache).

## B. Repeat with the same model and a different engine

First, manually start the alternative engine and load the same GGUF file. Then run:

~~~bash
cd /path/to/repro

BASE_URL='http://127.0.0.1:PORT' \
ENGINE_LABEL='name-and-version-of-alternative-engine' \
MODEL_ID='model-alias-in-the-API' \
MODEL_PATH="$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
bash repeat_same_model_new_engine.sh
~~~

The alternative server must accept the API extensions used by the battery: `reasoning_format`, `reasoning_budget_tokens`, and `chat_template_kwargs.enable_thinking`. If it does not implement them, the script will record the error; the run must not be treated as an equivalent comparison.

## Local evidence collection

Run on the MSI:

~~~bash
bash collect_evidence.sh
~~~

The collector saves existing Qwen35 logs, build logs, system state, `nvidia-smi`, `nvcc`, versions, endpoint status, and commits. It does not copy GGUF weights or stop services. To also calculate the GGUF SHA-256 (a full read of the file, approximately 10 GiB):

~~~bash
HASH_MODEL=1 bash collect_evidence.sh
~~~

The result is a directory, a `.tar.gz` archive, and its checksum. Attach the `.tar.gz` to the conversation to add the original binary artifacts to LEONES. Do not replace missing files with empty files.

## Metrics to compare

For each response: `prompt_tokens`, `completion_tokens`, `cached_tokens`, `prompt_ms`, `predicted_ms`, `prompt_per_second`, `predicted_per_second`, `finish_reason`, final content, `reasoning_content` length, response ID, and HTTP errors. Keep cold and warm prefill separate; do not mix cache hits with independent samples.

For robust results, run at least three independent repetitions per case, with different IDs, and publish the median, range, and standard deviation. This repetition recommendation applies to future campaigns; the original 2026-11-12 results must not be described as three repetitions if they were not.

## Variable control

- Fix the model and SHA-256 (when calculated), engine/commit/build, and arguments.
- Fix temperature, prompt, reasoning budget, and `max_tokens`.
- Fix context, batch, ubatch, threads, GPU layers, CPU-MoE, cache, and template.
- Record RAM, swap, VRAM, temperature, driver, CUDA, kernel, and competing processes.
- Do not run both tests simultaneously.
- Do not compare truncated outputs as complete responses.
- Do not infer expert-cache hit rate from the configured cache size.

## Safety and limitations

The scripts only interact with servers that the operator has already started. They contain no logic to kill processes, download models, or change server parameters. Model weights are not uploaded to the repository.

## Additional independent run: cafe-llama.cpp · 2026-11-13

An exploratory run of the same Qwen3.5-35B-A3B-IQ2_XXS GGUF was added using **cafe-llama.cpp** and the Nepenthes methodology. This is recorded as an independent test, not as a controlled engine comparison: 89/93 prompt tokens were cached during prefill, and equivalence of API extensions/configuration with Tandem.cpp has not been demonstrated.

### Specific scripts and usage procedure

Both scripts are in the `repro/` directory:

- [`run_NEPENTHES_independent_two_sum.py`](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_NEPENTHES_independent_two_sum.py): sends a test request and records the response together with host telemetry. **It does not start, stop, or reconfigure the server.**
- [`inspect_NEPENTHES_independent_run.py`](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_independent_run.py): reads the files saved by the runner. It does not need the server to remain active and does not run the model again.

#### 1. Prepare the environment

Clone the repository (or update an existing copy) and check out the branch containing this experiment:

~~~bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
git checkout benchmarks/tandem-qwen35-reasoning-battery-2026-11-12
git pull --ff-only
~~~

In an existing clone, use:

~~~bash
cd /path/to/LEONES
git fetch origin
git switch benchmarks/tandem-qwen35-reasoning-battery-2026-11-12
git pull --ff-only
~~~

The runner requires Python 3 and the shared `resource_monitor.py` monitor, which must exist at:

~~~text
artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py
~~~

It uses the Python standard library; no pip packages need to be installed.

#### 2. Check the existing server

Before running the runner, manually start `cafe-llama.cpp` with the model and parameters you want to evaluate. The script does not start it for you. Check that the endpoint responds:

~~~bash
curl -fsS http://127.0.0.1:18086/health
~~~

Find the server PID:

~~~bash
pgrep -af 'llama-server.*18086'
~~~

Identify the correct PID and verify that it belongs to the expected executable:

~~~bash
PID=21313
readlink -f "/proc/$PID/exe"
tr '\0' ' ' < "/proc/$PID/cmdline"
echo
~~~

Replace `21313` with the actual PID. Do not use an old PID without checking it: the operating system may have reused it for another process.

#### 3. Run the Nepenthes test

From the `repro/` directory, run:

~~~bash
cd artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro

python3 run_NEPENTHES_independent_two_sum.py \
  --pid "$PID" \
  --base-url http://127.0.0.1:18086 \
  --port 18086 \
  --model "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --output "$HOME/cafe-llama.cpp-qwen35-nepenthes-$(date +%Y%m%d-%H%M%S)"
~~~

Parameters:

- `--pid`: required; PID of the `llama-server` process already handling the request.
- `--base-url`: base URL of the OpenAI-compatible API. Default: `http://127.0.0.1:18086`.
- `--port`: port used by the resource monitor; it must correspond to the tested server.
- `--model`: GGUF path; by default it points to the Qwen3.5-35B-A3B IQ2_XXS specified in this report.
- `--output`: new directory for this run. Do not reuse a populated directory: the runner refuses to overwrite evidence.
- `--max-tokens`, `--reasoning-budget-tokens`, and `--timeout`: change the generation maximum, the budget field sent, and the timeout. The default budget is 128; sending it does not prove that the server enforces it.
- `--monitor-script`: optional; specifies another path to `resource_monitor.py` if it is not at the repository location documented above.

The task asks for a Python `two_sum` implementation with O(n) complexity, negative numbers, duplicates, distinct indices, and `None` when no solution exists. The runner uses temperature 0, `reasoning_format=deepseek`, `enable_thinking=true`, and `stream=false`.

#### 4. Inspect the results

Copy the exact path printed by the runner and pass it to the inspector:

~~~bash
python3 inspect_NEPENTHES_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-YYYYMMDD-HHMMSS"
~~~

To also display the generated final text and reasoning exposed separately by the API:

~~~bash
python3 inspect_NEPENTHES_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-YYYYMMDD-HHMMSS" \
  --show-content
~~~

The inspector does not modify the data. It reports run identity, build, model, timings, tokens, resource metrics, and the number of monitoring samples.

#### 5. Files produced by the runner

Inside the directory specified by `--output`:

- `manifest.json`: configuration, process identity, `/health`, `/props`, submitted request, and interpretation notes.
- `responses/independent-two-sum.json`: complete response, derived metrics, any errors, and resource summary.
- `resources/resource_samples.jsonl`: time-series monitoring samples.

Keep the entire directory for reproducibility. Do not manually edit the original JSON files; store annotations in a separate file. The inspection script requires the three files above.

### Recorded result (2026-11-13 run)

- Status: successful HTTP request, `finish_reason=stop`, no request error.
- Input/output: 93 prompt tokens, 1,060 generated tokens; 89 prompt tokens reported as cached.
- Reported speed: 26.62 prompt tok/s and 31.03 generation tok/s. Prompt speed is not a cold measurement: most tokens were cached.
- GPU: mean utilization 89.8%, stable VRAM at 2,001 MiB, mean temperature 55.86 °C, and mean power 32.21 W.
- Process CPU: 99.74% average; system CPU: 6.97% average.
- System swap-in: 90,112 bytes; swap-out: 0 bytes. Swap and disk counters are system-wide and are not attributed exclusively to the process.
- Quality: hash-map `two_sum` implementation is correct, O(n), and handles negatives, duplicates, and distinct indices. The response contains two editorial defects in its tests: the case labelled as a duplicates test uses [3, 2, 4], and a comment in the negative-number test first shows an incorrect sum before explaining the correct result.
- `reasoning_budget_tokens=128` was sent in the request; acceptance of the field does not prove that the server enforced that limit.

The original data from this run must remain in its evidence directory and be added to the repository as artifacts, together with the manifest, complete response, resource samples, logs, and hashes. The scripts above allow the experiment to be repeated and reviewed; they do not replace the original data.

### Comparative interpretation

Tandem.cpp and cafe-llama.cpp results remain separate campaigns. Do not calculate a performance ranking or attribute differences to the engine until independent repetitions and equivalent conditions are available—especially prompt-cache state, template, reasoning extensions, context, and runtime parameters.

## Reusable Nepenthes structure: engine + model

Nepenthes identifies the **test methodology**. Each run is identified by its specific **engine + model** pair; the engine is the runtime under evaluation (for example, `cafe-llama.cpp` or `Tandem.cpp`) and the model is the exact artifact (family, size, quantization, and hash when available).

Documentation is organized into three levels:

1. **Methodology:** this document defines the shared protocol, variables, controls, telemetry, and script usage.
2. **Engine + model template:** [NEPENTHES-engine-model-report-template.md](NEPENTHES-engine-model-report-template.md). Copy it for each new combination; it requires the engine identity, model identity, configuration, run, results, quality, and limitations to be recorded.
3. **Execution report:** one specific document per combination and campaign. The first example is [cafe-llama.cpp + Qwen3.5-35B-A3B · 2026-11-13](nepenthes-cafe-llama.cpp-qwen3.5-35b-a3b-2026-11-13.md).

### Identification convention

Always use this format:

`NEPENTHES_<ENGINE>_<MODEL>_<YYYYMMDD>`

The human-readable report title must express both components, for example: **cafe-llama.cpp + Qwen3.5-35B-A3B**. Do not create a report named only after the model or only after the engine.

### Scripts and operational workflow

- `run_NEPENTHES_*.py`: sends the request or battery to an already-running server, collects the response and telemetry, and creates a new evidence directory. It never starts, stops, or reconfigures the engine.
- `inspect_NEPENTHES_*.py`: reads the evidence directory created by the runner, presents metrics, and can display content. It does not query the server again or modify results.
- Engine-specific scripts may differ in arguments and tasks. The template and report must always document the exact command used, including PID/endpoint, model path, output directory, and script version.
- Before repeating a test, use a new output directory. Do not overwrite or edit the original JSON files.

Example for this cafe-llama.cpp campaign:

~~~bash
python3 run_NEPENTHES_independent_two_sum.py \
  --pid "$PID" \
  --base-url http://127.0.0.1:18086 \
  --port 18086 \
  --model "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
  --output "$HOME/cafe-llama.cpp-qwen35-nepenthes-$(date +%Y%m%d-%H%M%S)"
~~~

Inspect the result:

~~~bash
python3 inspect_NEPENTHES_independent_run.py \
  "$HOME/cafe-llama.cpp-qwen35-nepenthes-YYYYMMDD-HHMMSS" \
  --show-content
~~~

Each pair's report must link to the runner, inspector, and preserved evidence directory/archive. Figures must not be transferred from one engine/model combination to another, and independent campaigns must not be presented as controlled comparisons.


## Complementary technical references: hybrid MoE inference

These sources provide technical context for designing and evaluating NEPENTHES campaigns on Mixture-of-Experts models. They are research and architecture references; **they do not replace the measurement protocol or establish that their mechanisms are implemented in the engines under test**.

- [TensorFold-MoE: sparse-MoE inference architecture](../../research/moe/TensorFold-MoE.md) — a synthesis of SSD/RAM/VRAM hierarchies, offloading, concurrent CPU/GPU execution, routing traces, pre-gating, and speculative decoding. It explicitly distinguishes proposed integrations from existing features and external results from measurements on the MSI.
- [LEONES MoE research](../../atlas/MoE-investigacion.md) — context on routing skew, expert working sets, live cache versus static placement, miss cost, per-layer/token telemetry, and the MEASURED status of engines on the reference hardware.
- [Ostinato: Fast CPU-GPU MoE Inference for Local Agents via Resident Experts in Every Forward Pass (arXiv:2611.11533)](https://arxiv.org/abs/2611.11533) — a hybrid-execution study that keeps resident experts on GPUs during both prefill and decode, sends cold routes to the CPU, and selects a prefill path according to input length. The paper evaluates agent sessions with DeepSeek-V4-Flash and Qwen3-235B-A22B on a workstation with four RTX 4090D GPUs; its figures must not be extrapolated to the MSI's 4-GiB RTX 3050.

### Using these references in NEPENTHES

When evaluating an MoE engine, record—when exposed by the engine—per-layer/token routing distributions, resident expert sets, cache hits/misses, RAM↔VRAM movement, CPU and GPU work, PCIe transfers, and separate behavior for short prefill, long prefill, and decode. If instrumentation is unavailable, mark those metrics unavailable: do not infer cache hit rate from cache capacity or infer the working set from tok/s.

Keep three policies distinct: (1) static hot-expert placement, (2) dynamic live cache with replacement, and (3) hybrid execution of cold experts on CPU/over PCIe. Ostinato adds a specific hypothesis for agent sessions: resident experts can also serve short prefills after tool outputs. Treat this as a hypothesis to validate for each engine+model pair and workload, not as a universal property of MoE.

Cite published results with their hardware, model, quantization, workload, and version. Do not merge them with NEPENTHES measurements or present them as local results. For cross-engine comparisons, keep the model and cache state constant and document any differences in API, template, routing, or offload policy.


## NEPENTHES MoE probes: instrumentation and diagnosis

The battery now integrates a second per-request probe: [moe_runtime_probe.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/moe_runtime_probe.py). It runs alongside `resource_monitor.py`; it does not modify or restart the server. Its interval is controlled by `--monitor-interval` (for the next campaign, start at 0.5 s and keep it identical across comparisons).

### Automatically collected signals

| Probe | Metrics | Bottlenecks it helps identify |
|---|---|---|
| llama-server process | `/proc/PID/io`: bytes/chars read and written, I/O calls; `schedstat`: runtime and wait time; threads, RSS/HWM, and file descriptors | Model/expert reads, scheduler pressure, memory growth, or excessive threads |
| Kernel PSI | `/proc/pressure/cpu`, `memory`, `io` (`some/full avg10`) | Time tasks are stalled by CPU, memory, or I/O contention; complements utilization percentages |
| CPU | Current frequency aggregated across available cores | Frequency drops, thermal/power limits, or platform variation |
| GPU/VRAM | Utilization, memory, temperature, power, clocks, and PCIe RX/TX throughput from `nvidia-smi` | Underused GPU, VRAM pressure, host↔device traffic, and possible PCIe-bound phases |
| API and response | Tokens, prefill/decode, prompt cache, timings, and completion already collected by the runner | Separating TTFT/prefill from generation and prompt-cache effects from expert-cache effects |

Per-request samples are saved to `resources/moe_runtime_samples.jsonl`; summaries are added as `moe_runtime_metrics` in each response JSON and in `summary.jsonl`. The probe records valid sample counts and limitations. PSI is host-wide and PCIe is device-wide, not process-attributed: do not attribute either exclusively to llama-server. PCIe fields depend on driver support; unavailable fields remain unmeasured.

### Expert routing and cache: offline probe

[inspect_NEPENTHES_moe_trace.py](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_moe_trace.py) analyzes two sources without querying or modifying the server:

- **Verbose engine log:** aggregates hits, misses, CPU misses (if reported by the engine), hit rate, and uploaded MiB when matching `llama_moe_cache` lines are present. Example:

  ```bash
  python3 inspect_NEPENTHES_moe_trace.py \
    --server-log "$HOME/tandem-nepenthes-qwen35-18085.log" \
    --output "$HOME/moe-cache-summary.json"
  ```

- **MCT1 routing trace:** for builds implementing `LLAMA_MOE_CACHE_TRACE`, summarizes routing events and observed tokens per layer, distinct selected experts, coverage, entropy, and most frequently selected experts:

  ```bash
  python3 inspect_NEPENTHES_moe_trace.py \
    --trace "$HOME/tandem-moe.trace" \
    --server-log "$HOME/tandem-nepenthes-qwen35-18085.log" \
    --output "$HOME/moe-routing-summary.json"
  ```

**Compatibility verified for the reference Tandem.cpp build:** its llama.cpp submodule commit `f5222f25c18da062ab2b8a2dbbfbf4feae398566` contains aggregated `llama_moe_cache` hit/miss/uploaded-byte statistics, but does not contain `LLAMA_MOE_CACHE_TRACE` or the MCT1 format. Therefore, the first full run can measure aggregate cache behavior if the log retains those lines; it cannot attribute routing or hits per layer. The MCT1 parser is ready for a future compatible build, but must not be enabled or reported as available on the current build. The current upstream [moe-cache-tune.py](https://github.com/ggml-org/llama.cpp/blob/master/scripts/moe-cache-tune.py) documents MCT1 and cache replay; that does not mean Tandem's pinned commit includes it.

### Interpreting signals and locating bottlenecks

- **PCIe / expert-miss bottleneck:** slow generation, sustained PCIe activity, and a cache log with many misses/uploaded MiB. Confirm with a controlled cache/placement variation; global PCIe throughput alone does not establish causality.
- **CPU/RAM bottleneck:** high process CPU, stable or falling frequency, CPU/memory PSI pressure, and rising RSS/swap. Distinguish actual memory pressure from simple swap occupancy.
- **GPU/compute bottleneck:** sustained GPU utilization, low PSI wait, and low PCIe throughput during decode; vary batch, offload, and kernels separately.
- **Storage bottleneck:** process read deltas and elevated I/O PSI, especially on cold load. Do not mix GGUF loading with warm generation.
- **Routing imbalance:** can only be claimed with per-layer/token routing traces; entropy, coverage, and expert concentration estimate skew, not execution cost.
- **Prefill versus decode:** keep short and long prompts separate; measure TTFT/prefill and decode tokens/s separately. Prompt cache and expert cache are distinct mechanisms.

Do not infer hit rate from cache size, expert transfers from GPU utilization, or per-layer compute from global utilization. Missing signals must be marked `unavailable`/unmeasured. Telemetry has overhead: cadence, tools, and versions must be fixed and declared in every campaign.

### Validation before the full battery

First run one request with `--limit 1 --monitor-interval 0.5`; verify `moe_runtime_metrics` and `resources/moe_runtime_samples.jsonl` appear, the PID matches the server, and multiple samples were collected. Then inspect the Tandem log with the script above. If no cache lines are present, mark cache probing unavailable; do not restart the server just to force a logging option. Run the full battery only after this validation.
