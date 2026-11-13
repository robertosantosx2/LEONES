# NEPENTHES · Tandem.cpp + Qwen3.5-35B-A3B · independent battery · 2026-11-13

**ID:** `NEPENTHES_Tandem.cpp_Qwen3.5-35B-A3B-IQ2_XXS_20261113`  
**Type:** independent execution of the 10-case NEPENTHES battery  
**Execution status:** 10/10 according to the runner's final output  
**Publication status:** partial evidence; the available terminal excerpt preserves detailed records for cases 6–10.

> **Publication scope.** The supplied primary file contains the complete printed records for cases 6–10 and the final confirmation of the results directory. It does not include records for cases 1–5, the complete manifest, original response JSON files, or the raw resource-sample file. This report does not reconstruct missing data and does not present the five published cases as the entire battery.

## 1. Objective and scope

Record an instrumented Qwen3.5-35B-A3B IQ2_XXS reasoning-battery run using **Tandem.cpp** and the **Nepenthes** methodology. The full battery ran ten sequential cases covering arithmetic, `two_sum`, and `binary_search`, with varying reasoning budgets and generation limits.

This is an independent run, not a controlled A/B comparison with `cafe-llama.cpp`. Engine, cache, execution order, and system-state differences prevent direct performance comparison.

## 2. Engine and server

- **Engine:** `Tandem.cpp`
- **Local repository:** `~/Descargas/tandem-research/engines/tandem.cpp`
- **Build recorded for the reference campaign:** `0.8.0-dev`, build `11962`; llama.cpp submodule `f5222f25c18da062ab2b8a2dbbfbf4feae398566`.
- **Endpoint:** `http://127.0.0.1:18085`
- **PID:** `10314`
- **Served model:** `$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`

Server startup arguments confirmed in the session:

```bash
-m "$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf" \
--host 127.0.0.1 --port 18085 \
-c 2048 -b 128 -ub 64 -t 8 -tb 8 -ngl 99 \
--cpu-moe --moe-cache-mib 512 -np 1
```

The server was already running before the runner was invoked. The runner does not start, stop, or reconfigure the server.

## 3. Model

- **Family:** Qwen3.5-35B-A3B
- **File:** `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`
- **Architecture:** `qwen35moe`
- **Parameters:** 35B total; approximately 3B active
- **Experts:** 256 total; 8 activated per token
- **Quantization:** IQ2_XXS, 2.0625 bpw
- **Reported local size:** 10,665,148,928 bytes (approximately 9.94 GiB)
- **Model SHA-256:** not included in this run's evidence.

## 4. Platform

- **Host:** MSI Thin 15 B12UC
- **Operating system:** Ubuntu
- **CPU:** Intel Core i7-12650H
- **RAM:** 14 GiB
- **Configured swap:** 32 GiB
- **GPU:** NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM, sm_86
- **Driver:** 580.178.04
- **CUDA runtime:** 13.0
- **CUDA toolkit:** 13.4.92

## 5. Protocol

- **Cases:** 10 in the full battery; the records published here cover cases 6–10.
- **Execution:** sequential, one slot.
- **Generation temperature:** 0.
- **Streaming:** disabled.
- **Requested reasoning format:** `deepseek`.
- **Thinking:** enabled through `chat_template_kwargs.enable_thinking=true`.
- **Requested reasoning budget:** varied by case (128 or 256 in the published records).
- **Monitoring:** nominal 1-second interval; 29–53 samples per request in the published cases.
- **Runner:** `run_battery.py`, with `--server-pid 10314`, `--monitor-interval 1`, and `--timeout 900`.
- **Output directory confirmed by the runner:** `~/NEPENTHES_TANDEM_QWEN35_20261113_full`.

Sending `reasoning_budget_tokens` or selecting a reasoning format does not by itself prove that the server enforces a semantic reasoning limit. It is recorded as a requested parameter, not as a verified effective limit.

## 6. Results for cases with available evidence

| Case | Task | Requested budget | max_tokens | Prompt | Cached | Generated | Prefill tok/s | Generation tok/s | finish |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 6 | two_sum | 256 | 1,024 | 93 | 89 | 1,024 | 50.81 | 36.67 | `length` |
| 7 | two_sum | 128 | 1,536 | 93 | 89 | 1,016 | 53.50 | 33.97 | `stop` |
| 8 | two_sum | 256 | 1,536 | 93 | 89 | 1,158 | 59.94 | 32.34 | `stop` |
| 9 | binary_search | 128 | 1,536 | 188 | 0 | 1,249 | 139.42 | 29.65 | `stop` |
| 10 | binary_search | 256 | 1,536 | 188 | 184 | 1,500 | 58.11 | 27.93 | `stop` |

These five cases generated 5,947 tokens. The unweighted mean of the five per-request generation rates was **32.11 tok/s**; median **32.34 tok/s**; range **27.93–36.67 tok/s**. This is not the mean for the full battery.

### Cache interpretation

- Cases 6–8: 89 of 93 input tokens were reported as cached.
- Case 9: 0 of 188 input tokens were cached; it is the only fully uncached prompt among these five.
- Case 10: 184 of 188 input tokens were reported as cached.

Prefill must therefore not be compared as though all cases were homogeneous cold-cache measurements. Case 9's prefill rate is not directly comparable with cases 6–8 and 10.

### Completion and truncation

Case 6 reached its exact 1,024-token generation limit and ended with `finish_reason=length`: it was truncated by the generation limit. Cases 7–10 ended with `stop`. A `stop` finish reason confirms generation termination, not algorithmic correctness.

Case 10 generated 1,500 of the allowed 1,536 tokens while ending with `stop`. Its proximity to the limit warrants review of the original response.

## 7. Resource monitoring (cases 6–10)

The following figures are per-request means reported by the monitor. Overall means use a simple mean of the five per-case means, not a sample-weighted mean.

| Case | Process CPU % | Process RSS (GB) | GPU % | Mean VRAM (MiB) | Mean temperature | Mean power |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 989.0 | 10.97 | 81.0 | 2,059 | 69.4 °C | 36.5 W |
| 7 | 993.2 | 11.03 | 75.9 | 2,059 | 71.8 °C | 35.6 W |
| 8 | 978.2 | 10.98 | 74.6 | 2,068 | 73.6 °C | 35.3 W |
| 9 | 993.4 | 11.01 | 67.5 | 2,073 | 74.3 °C | 33.2 W |
| 10 | 996.6 | 11.03 | 64.6 | 2,073 | 75.1 °C | 32.6 W |

Summary of per-case means:

- **Process CPU:** 990.1% (approximately 9.9 equivalent cores under the `psutil` convention).
- **Process RSS:** approximately 11.0 GB.
- **GPU utilization:** 72.7%.
- **VRAM:** 2,059–2,073 MiB; mean of the five means: 2,066 MiB.
- **GPU temperature:** mean of the five means: 72.8 °C; highest per-case mean: 75.1 °C.
- **GPU power:** mean of the five means: 34.7 W.
- **Samples:** 191 total (29 + 30 + 36 + 43 + 53).

RAM used, RAM available, swap, and disk I/O are system-wide counters and must not be attributed exclusively to the process. Across the published cases, per-case mean available RAM remained around 11.33 GB. Per-case mean swap occupancy increased from about 589 MB (case 6) to about 756 MB (case 10). Rising swap occupancy alone does not prove thrashing or attribute all swapping to the server. Swap and disk deltas are system-wide.

## 8. Functional quality

**Not evaluated from the published evidence.** The excerpt preserves reasoning/content character counts but not the original response text. It is therefore not possible here to verify:

- whether the `two_sum` implementation is correct;
- whether `binary_search` returns correct indices for edge cases;
- whether explanations are coherent;
- whether cases 7–10 end with complete solutions;
- whether case 6 was truncated before the solution was complete.

No functional score is assigned and the battery is not declared functionally passed.

## 9. Limitations and actions needed to close the campaign

1. Add records for cases 1–5.
2. Publish `run_manifest.json`, `summary.jsonl`, all ten original JSON files under `responses/`, and `resources/resource_samples.jsonl`.
3. Add server logs and SHA-256 hashes for the model and evidence archive.
4. Inspect the full responses and run correctness tests for `two_sum` and `binary_search`.
5. Verify whether the server applied the reasoning budget rather than inferring enforcement from the submitted value.
6. Keep cold- and warm-prefill measurements separate.

## 10. Published evidence

- [Original terminal excerpt: cases 6–10](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/evidence/terminal-tail-cases-06-10.txt)
- [Excerpt SHA-256](../../artifacts/benchmarks/tandem-qwen35-independent-2026-11-13/evidence/terminal-tail-cases-06-10.txt.sha256)
- [NEPENTHES methodology](tandem-qwen35-reasoning-budget-methodology-2026-11-12-en.md)
- [Engine + model report template](NEPENTHES-engine-model-report-template.md)

**Conclusion:** the available evidence confirms that the runner completed all ten cases and supports performance and monitoring analysis for cases 6–10. It does not support functional validation or complete ten-case statistics. The campaign is documented as an executed run with partial primary evidence, pending addition of the full results directory.
