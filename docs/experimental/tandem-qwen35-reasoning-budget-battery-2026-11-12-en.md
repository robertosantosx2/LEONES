# Summary Results · Tandem.cpp Qwen3.5-35B-A3B IQ2_XXS · 2026-11-12

## Run identity

- Model: Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf, reported local size 9.94 GiB.
- Tandem.cpp: commit d684d4de171d8c6413e34c95fb5703492dcd2561.
- llama.cpp submodule: f5222f25c18da062ab2b8a2dbbfbf4feae398566.
- Build: 0.8.0-dev build 11962, fingerprint b11962-f5222f25c.
- Endpoint: 127.0.0.1:18086.
- Parameters: context 2048, batch 128, ubatch 64, threads 8/8, ngl 99, CPU-MoE, 512 MiB expert cache, one slot.
- Hardware: MSI Thin 15 B12UC; i7-12650H; RTX 3050 Laptop 4 GiB (sm_86); 14 GiB RAM; 32 GiB swap; driver 580.178.04; CUDA runtime 13.0; nvcc 13.4.92; Ubuntu kernel 7.0.0-43-generic.

## Measurement summary

| Case | Budget | max_tokens | Completion | tok/s | Finish |
|---|---:|---:|---:|---:|---|
| 17 × 23 | 64 | 256 | 70 | 35.62 | stop |
| 17 × 23 | 128 | 384 | 134 | not recorded here | stop |
| 17 × 23 | 256 | 512 | 262–263 | 34.58 / 33.11 | stop |
| two_sum | 128 | 512 | 512 | 33.07 | length |
| two_sum | 128 | 768 | 768 | 32.51 | length |
| two_sum | 256 | 1024 | 1024 | 33.27 | length |
| two_sum | 128 | 1536 | 1165 | 32.58 | stop |
| two_sum | 256 | 1536 | 1201 | 32.32 | stop |
| binary_search | 128 | 1536 | 1435 | 34.79 | stop |
| binary_search | 256 | 1536 | 1536 | 33.20 | length |

## Thinking diagnosis

With thinking enabled and no explicit budget, reasoning outputs were observed to consume the entire max_tokens allowance without producing final content (finish_reason length). The run without thinking did produce a final answer. The Qwen3-Coder parser separates content preceding </think> into reasoning_content; if the closing marker is not generated before the generation ends, content remains empty. The reasoning_budget_tokens control forces the closing marker when the budget is exhausted.

## MSI resource behavior

### What was and was not measured

The battery records per-request generation metrics (input/output tokens, duration, speed, and finish reason). The evidence collector, however, captured system and process snapshots at a particular point in time; it did not collect a time series of CPU/RAM/VRAM/SSD usage associated with each request. The snapshot below therefore describes the server's loaded state during the campaign, not the exact peaks for each row. These values must not be interpreted as independent measurements for every prompt.

### Snapshot of the machine with the model loaded

| Resource | Available snapshot | Technical interpretation |
|---|---|---|
| RAM | 14 GiB total; 3.1 GiB used; 1.4 GiB free; 11 GiB in buff/cache; 11 GiB available | No physical-memory pressure is apparent in this snapshot: Linux could reclaim a substantial portion of the cache. Looking only at “free” memory understates the available memory. |
| Swap | 32 GiB configured; approximately 1.2 GiB occupied | Some pages were in swap, but occupancy does not prove swapping activity during generation or thrashing. No per-request time-series swap-in/swap-out counters were saved. |
| VRAM | 1,953 MiB of 4,096 MiB occupied; server process around 1,930 MiB | The server maintained a relatively modest GPU footprint, leaving approximately 2.1 GiB unused in this snapshot. This is consistent with the CPU-MoE strategy; by itself, it does not establish expert hit rate or the effective placement of each expert. |
| GPU | RTX 3050 Laptop, 4 GiB, sm_86; observed temperature 44 °C | No time series of utilization, power, clock, or temperature per request was preserved. |
| CPU | Intel Core i7-12650H; server configured with 8 threads and 8 batch threads; `--cpu-moe` | The CPU-MoE path places expert work on the CPU and host memory, while other operations use the GPU. The collected evidence contains no per-run CPU utilization, frequency, or load percentage. |
| SSD / storage | The local GGUF is approximately 9.94 GiB and the server loads it from that path | No read/write, latency, IOPS, or free-space measurements were taken during the battery. Linux page cache may affect subsequent reads, but its per-prompt impact was not measured. |
| Server process | PID 12228; port 18086; context 2048; one slot; expert cache configured to 512 MiB | The 512 MiB expert cache is a configuration parameter, not a measurement of effectively resident memory or hit rate. The server remained loaded between requests; it was not restarted for each case. |

**Overall interpretation.** The clearest signal is that the 35B model ran with an observed GPU footprint of around 1.9 GiB, relying on CPU-MoE and host memory on an RTX 3050 with 4 GiB. The reported available RAM (11 GiB) did not indicate severe pressure at the time of the snapshot. The 1.2 GiB of occupied swap is worth recording, but without activity counters it does not support a claim that generations were actively paging. There is also insufficient data to claim that the SSD was a bottleneck or to quantify CPU usage.

### Per-run resources: evidence scope

The server remained resident on port 18086 and handled requests sequentially using one slot. The table associates each run with its generation result and makes explicit that per-request resource telemetry is unavailable. Approximate times are calculated as completion / tok/s when both values are available; they are not independent timing measurements.

| Case | Budget | Completion | Speed | Approx. generation time | RAM / VRAM / CPU / swap / SSD per request |
|---|---:|---:|---:|---:|---|
| 17 × 23 | 64 | 70 | 35.62 tok/s | 1.97 s | Not captured individually; only the shared server snapshot above is available as context. |
| 17 × 23 | 128 | 134 | Not recorded | Cannot calculate | Not captured individually. |
| 17 × 23 | 256, repeat A | 262 | 34.58 tok/s | 7.58 s | Not captured individually. |
| 17 × 23 | 256, repeat B | 263 | 33.11 tok/s | 7.94 s | Not captured individually. |
| two_sum | 128 | 512 | 33.07 tok/s | 15.48 s | Not captured individually. |
| two_sum | 128 | 768 | 32.51 tok/s | 23.62 s | Not captured individually. |
| two_sum | 256 | 1,024 | 33.27 tok/s | 30.78 s | Not captured individually. |
| two_sum | 128 | 1,165 | 32.58 tok/s | 35.76 s | Not captured individually. |
| two_sum | 256 | 1,201 | 32.32 tok/s | 37.16 s | Not captured individually. |
| binary_search | 128 | 1,435 | 34.79 tok/s | 41.25 s | Not captured individually. |
| binary_search | 256 | 1,536 | 33.20 tok/s | 46.27 s | Not captured individually. |

These times are arithmetic estimates based on the average speed reported by the server; they may differ from wall-clock time due to prefill, preparation, queuing, and API latency. The table does not imply that RAM, VRAM, or CPU usage remained constant during each generation: they simply were not sampled at sufficient resolution to determine that.

### What to instrument in a future repetition

To compare the physical resource behavior of each run, add timestamped sampling correlated with the request ID:

- GPU: `nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.free,temperature.gpu,power.draw,clocks.gr --format=csv -l 1`.
- CPU and memory: sample `/proc/stat`, `/proc/meminfo`, and `/proc/<PID>/status`, or use `pidstat -rud -p <PID> 1`.
- Swap: deltas of `pswpin` and `pswpout` in `/proc/vmstat`, not just occupied size.
- SSD: `/proc/diskstats` deltas for the device containing the model, together with free space before and after.
- Record start/end time, request ID, budget, completion, and API metrics in the same event file.

This makes it possible to calculate peak and average resource use per request and detect whether long generations increase CPU, RAM, VRAM, swap, or I/O. In this battery, those relationships remain working hypotheses rather than measured findings.

## Instrumentation for future runs

Scripts have been added to record resources during **each request**, with an independent sampling window and a local case identifier:

- [Instrumented battery runner](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_battery.py)
- [Linux/NVIDIA monitor](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py)
- [Usage guide and measurement limitations](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/RESOURCE_MONITORING.md)

The runner writes `resource_metrics` into each response JSON and `summary.jsonl`, as well as raw samples to `resources/resource_samples.jsonl`. It includes host RAM and server RSS, swap, system and process CPU, NVIDIA utilization and VRAM, GPU temperature/power/clock, and block-device I/O deltas. It also identifies the mount containing the GGUF.

**Important:** this instrumentation is ready for future campaigns; it does not alter historical results or reconstruct telemetry that was not captured in November. Before running a full battery, the guide recommends validating with `--limit 1`. Disk and swap counters are system-wide and may include activity unrelated to the server; these limitations are documented.

## Evidence and reproducible files

The evidence archive generated on November 12, 2026 was added to this Git branch, and its SHA-256 checksum was verified locally before publication.

- [Evidence archive (TAR.GZ)](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/evidence/tandem-qwen35-evidence-20261112-235030.tar.gz)
- [SHA-256 checksum](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/evidence/tandem-qwen35-evidence-20261112-235030.tar.gz.sha256)
- [Reproduction scripts](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/)
- [Battery methodology](tandem-qwen35-reasoning-budget-methodology-2026-11-12-en.md)

The archive contains the records and snapshots collected by the evidence script. It does not include the GGUF model weights.
