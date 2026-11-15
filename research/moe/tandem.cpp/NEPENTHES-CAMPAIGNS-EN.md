# NEPENTHES — validation and experimentation campaigns

**Language:** [English](NEPENTHES-CAMPAIGNS-EN.md) · [Español](NEPENTHES-CAMPAIGNS.md)

**Cut-off:** 2026-11-15.  
**Rule:** a campaign is marked complete only for the scope demonstrated by its artifacts. Building, running an inference, capturing Nsight and importing a synchronized pair are separate gates.

## Campaign summary

| ID | Campaign | Status | Evidence / limitation |
|---|---|---|---|
| C00 | MoE/runtime probes | Partial / prior research | LEONES PR #147; runtime/cache, scheduler, I/O, PSI, CPU and NVIDIA telemetry probes. Not universal coverage. |
| C01 | FAST PATH / CAPACITY PATH | Documentation/partial implementation | LEONES PR #149; performance and out-of-core execution plan plus Nsight SQLite inspector. No paired inference evidence. |
| C02 | Universal contract + JSONL sink | Implemented and CI-tested | Tandem.cpp PR #1; event contract, concurrent sink and probe application. |
| C03 | Installer, CLI and package | Basic functional validation complete | LEONES PR #152; doctor, self-test, harmless smoke and exit-code-23 propagation. |
| C04 | Historical Qwen3.5-35B Nsight-only import | Imported and audited | 151,039 activities across eight CUPTI families; SQLite integrity passed. Historical source has no paired JSONL. |
| C05 | Instrumented CUDA build on pinned base | Complete | llama.cpp pinned at `f5222f25c18da062ab2b8a2dbbfbf4feae398566`; Tandem/runtime patches and probes applied; CUDA sm_86 llama-server built. |
| C06 | Real inference with instrumented engine | Complete for CPU-only smoke | Qwen3.5-4B Q4_K_M; 3,683 engine events, 3,117 in request window, 49 KV events in window. Nsight disabled. |
| C07 | Paired engine + Nsight capture | Pending | Same execution/RUN_ID, paired import and demonstrated correlation/clock mapping. |
| C08 | Comparative performance and recommendations | Pending | Baseline/control, repetitions, overhead, bytes/latencies and GPU metrics. |

## C03 — CLI and process wrapper

- User-space installation under `~/.local`, no root.
- `nepenthes doctor` and `nepenthes self-test`: passed.
- Smoke with an uninstrumented Python process: exit code 0 and verified package.
- Controlled failure: child exit code 23 propagated to parent; hashes, events and HTML retained.

Instrumented-engine acceptance is partially completed in C06; the full cycle with Nsight and `nepenthes verify` on a paired capture remains open.

## C04 — Qwen3.5-35B-A3B IQ2_XXS: historical Nsight

Source: `qwen35-correlated-20261114.sqlite`; standalone import, not paired with NEPENTHES.

- 151,039 activities: kernel 8,982; memcpy 44,488; memset 9; runtime 84,116; graph trace 5,207; synchronization 7,864; CUDA event 262; overhead 111.
- SQLite integrity passed; no broken foreign keys or duplicates.
- All 262 CUDA_EVENT timestamps are zero in the source and are preserved without inventing duration.

Report: [historical Qwen3.5 report](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115-EN.md).

## C05 — Instrumented CUDA engine build

Pinned base: llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566` (2026-10-28). Applied in order: `tandem.patch`, `nepenthes/runtime.patch`, then `apply_runtime_probes.py`. Application was clean, `git diff --check` was clean, and CUDA sm_86 `llama-server` built successfully.

JSONL sink and request_start/request_end markers appear in `libllama-server-impl.so`. This proves compilation and hook inclusion, not complete probe coverage. The shallow `cafe-llama.cpp` checkout was not used because its commit did not match the pinned revision.

## C06 — First real Qwen3.5-4B inference

**RUN:** `20261115_114657_bash_b5fc455f` · **Model:** Qwen3.5-4B Q4_K_M.  
**Engine:** instrumented server on pinned base. **Configuration:** CPU-only (`--n-gpu-layers 0`), context 512, 4 threads, batch 128, ubatch 64, local port 18086. **Nsight:** disabled (`--nsys off`).

### Performance

| Metric | Value |
|---|---:|
| Prompt evaluated / tokens generated | 10 / 16 |
| Prefill / decode | 21.50 / 10.72 tok/s |
| Server time | 1,864.85 ms |
| Monotonic request_start → request_end | 1.864918 s |

The response ended at `n_predict=16` and contained a reasoning block; it did not complete the requested literal. The HTTP request and generation completed successfully (`INFERENCE_TEST=SUCCESS`).

### Engine events

| Type | Total JSONL | Within request |
|---|---:|---:|
| transfer | 2,920 | 2,540 |
| kernel | 454 | 290 |
| sync | 232 | 226 |
| kv_cache | 55 | 49 |
| allocation | 9 | 9 |
| free | 10 | Not included in the reported temporal breakdown |
| routing | 1 | 1 |
| request_start / request_end | 1 / 1 | 1 / 1 |

Total engine events: 3,683; request window: 3,117. Every event in the window has `request_id=0`: this is temporal delimitation of one request, not robust ID-based attribution.

The 2,540 transfers are labelled H2D/D2H even though the model ran CPU-only. Do not assume they represent GPU compute traffic; audit their semantics and backend. KV events are mainly `apply_ubatch`, `seq_rm` and `seq_rm.range`; UINT64_MAX values are retained as raw data until their source-code semantics are confirmed. The shutdown log warns of differences between expected and observed CUDA0/CUDA_Host buffer sizes; inference still completed, and this requires investigation.

This capture contains no Nsight data or stack samples; it cannot provide a real flame graph, per-kernel GPU timings or instrumentation overhead.

## Next campaigns

### C07 — Paired capture

1. Record commit, model hash and exact configuration.
2. Enable NEPENTHES JSONL and Nsight in the same RUN_ID.
3. Verify artifacts, manifest, exit code and checksums.
4. Import the pair into LEONES without mixing uncalibrated clocks.
5. Audit subsystem coverage and event loss.

### C08 — Controlled performance

- Compare an uninstrumented baseline with the instrumented variant; warm up and run at least three repetitions.
- Fix model/hash, prompt, output, context, quantization, commit, batch/ubatch, threads, offload, thinking and cache.
- Record TTFT, prefill/decode, RAM/VRAM, swap, power if measured, H2D/D2H/D2D bytes, kernel durations and waits.
- Report median, dispersion and overhead. Change one parameter at a time.
- Recommend tuning only when measured improvement does not cause an unacceptable regression.

### C09 — Reports

Timeline with explicit clock domains; latency and size distributions; KV/MoE tables and timeline; flame graph only with stack samples; run comparison; HTML, Markdown, CSV, SQLite, SVG/PNG and checksums.

## Global completion criterion

NEPENTHES is not complete until a clean installation can wrap a real inference, produce engine events and host/GPU/Nsight telemetry, preserve artifacts, import the paired capture, generate reproducible reports and pass verification. Correlation, coverage and overhead limitations must be explicit.
