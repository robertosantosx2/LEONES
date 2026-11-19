# NEPENTHES — roadmap to a complete functional release

**Language:** [English](NEPENTHES-ROADMAP-EN.md) · [Español](NEPENTHES-ROADMAP.md)

**Cut-off date:** 2026-11-15 (updated after C07).  
**Status:** CLI and instrumented-engine capture tested with a Qwen3.5-4B inference; full acceptance with Nsight, correlation, coverage and overhead remains pending.

This roadmap separates implementation, CI validation and physical validation. A task is not complete merely because a PR exists: it needs the evidence specified by its exit criterion.

## Legend

- [x] Implemented with sufficient evidence for the stated scope.
- [~] Implemented or partially validated; acceptance testing remains.
- [ ] Pending.

## Phase A — Engine instrumentation

- [x] Define the universal event contract and JSONL sink.
- [x] Implement concurrency-safe emission and shutdown barrier.
- [x] Add JSONL format and sink lifecycle tests.
- [x] Integrate deterministic probes against the pinned llama.cpp revision.
- [x] Build CUDA in CI for target architecture sm_86.
- [x] Run a real Qwen3.5-4B inference on the MSI with the patched binary; confirm 3,683 engine events.
- [~] Audit semantics and coverage of each observed event family; all events in the request window use `request_id=0`.
- [~] Audit subsystem coverage: request/routing, KV cache, transfers, kernels, sync and allocation observed; MoE cache, workers, prefetch, OOM/fallback and ggml_op dispatch still lack dedicated acceptance.
- [ ] Measure instrumentation overhead against a control run using an identical protocol.
- [ ] Define and test JSONL rotation/size limits for long runs.

**Phase exit:** real execution with valid JSONL, expected events, accounted errors/losses and measured overhead.

## Phase B — Installation and CLI

- [x] Rootless user-space installer.
- [x] `nepenthes` command under `~/.local/bin`.
- [x] `doctor`, `self-test`, `run/capture`, `inspect` and `verify` commands.
- [x] One-line wrapper with smoke/standard/full profiles.
- [x] `NEPENTHES_RUN_ID` and `NEPENTHES_TRACE_JSONL` for instrumented engines.
- [x] Host CPU/RSS capture and global NVIDIA telemetry when available.
- [x] Logs, exit code, manifest, hashes, CSV, JSONL, SQLite and HTML/Markdown/SVG reports.
- [x] MSI self-test: 3 events, 1 sample, valid HTML and checksums.
- [x] Harmless-process run: exit code 0 and verifiable package.
- [x] Controlled failure: exit code 23 preserved and package valid.
- [x] Instrumented server + Qwen3.5-4B: real JSONL with 3,683 events, request_start/end and exit code 0.
- [~] Verify the real inference package completely; Nsight was disabled in C06.
- [ ] Test smoke/standard/full profiles, `--nsys auto/required/off`, and Nsight absent/failure cases.
- [ ] Run and archive `nepenthes verify` on the C06 inference package.
- [ ] Test engine failure/early termination, Ctrl-C, child processes and partial capture without losing the manifest.
- [ ] Document update, reinstall and uninstall.

**Phase exit:** clean installation and reproducible wrapper that leaves a verifiable package, including after a controlled failure.

## Phase C — LEONES importer

- [x] Paired JSONL + Nsight import implemented with synthetic tests.
- [x] Preserve SHA-256 and original payload.
- [x] Keep clock domains separate; explicitly prohibit artificial correlation.
- [x] Read-only Nsight inspection.
- [x] Standalone Nsight-only import with migration 003 and separate tables.
- [x] Adapters for the eight families present in the MSI capture.
- [x] Real MSI import: 151,039 rows, SQLite integrity OK, no duplicates or basic temporal anomalies.
- [x] CUDA_EVENT check: all 262 zero timestamps match source and are retained without fabricated intervals.
- [~] Validate a real paired import from one wrapper execution.
- [ ] Test re-import/idempotency and existing output database behavior.
- [ ] Test different Nsight/SQLite versions and unsupported CUPTI tables containing rows.
- [ ] Ensure summary, coverage and output manifest expose partial failures.

**Phase exit:** repeatable, traceable, intact paired and standalone imports with honest coverage reporting.

## Phase D — Qwen3.5 capture and experimental validation

- [x] Preserve historical Nsight capture from 2026-11-14 and its provenance.
- [x] Inspect and import historical SQLite without paired JSONL.
- [x] Build descriptive report for the historical capture.
- [x] Apply `tandem.patch`, `runtime.patch` and probes to pinned llama.cpp revision `f5222f25c18da062ab2b8a2dbbfbf4feae398566`; build CUDA sm_86 `llama-server` on MSI. The shallow `cafe-llama.cpp` checkout was not used.
- [x] Run Qwen3.5-4B Q4_K_M CPU-only, context 512, 4 threads, batch 128 and ubatch 64; capture 3,683 events.
- [ ] Run Qwen3.5-35B campaign with model and configuration recorded in manifest.
- [ ] Capture NEPENTHES JSONL and Nsight SQLite simultaneously in the same execution (C06 used `--nsys off`).
- [~] KV cache observed: 49 events in C06 request window. Verify MoE cache, workers and prefetch through explicit events; do not infer them from temporal proximity.
- [ ] Repeat at least three times with identical configuration and controls; include an uninstrumented baseline.
- [ ] Compare overhead, tokens/s, host/GPU memory, kernels and transfers.
- [ ] Archive logs, model hash, commands, configuration, commit, JSONL, SQLite, NSYS report, response and checksums.

**Phase exit:** reproducible paired dataset sufficient to answer performance/lifecycle questions without overstating correlation.

## Phase E — Reports and visualization

- [x] Reusable HTML template and PDF/PNG for the first Qwen3.5-4B report; historical Qwen3.5-35B activity tables.
- [x] Interpretation rules for timestamps, correlation and coverage.
- [~] CLI HTML/Markdown/SVG report: self-test validated; first Qwen3.5-4B dashboard built from available aggregates; automatic generation from real JSONL/SQLite still pending.
- [ ] Timeline panel for CPU/RSS/GPU and request markers.
- [ ] Kernel distribution by name, duration and stream.
- [ ] H2D/D2H/D2D transfers by bytes, direction and Nsight duration.
- [ ] CUDA runtime/synchronization/graph activity by type.
- [ ] KV-cache/MoE-cache/worker/prefetch views based on real probes.
- [ ] Run-to-run and baseline comparison.
- [ ] CSV table export and reproducible SQLite queries.

**Phase exit:** navigable raw data, summaries, tables and charts; every metric identifies source, clock, unit and attribution level.

## Phase E.1 — Semantic analysis and report quality (new priorities)

C07 confirms that the importer can expose useful CUDA activity, but reports must decode Nsight enums and preserve attribution limits.

| Priority | Improvement | Benefit |
|---|---|---|
| **P0** | Semantically decode `cudaMemcpyKind` and memory types (`srcKind`/`dstKind`) using enum tables from the capture itself. | Distinguish H2D, D2H, D2D, Host-to-Array, Unified Memory and other modes; also identify pageable, pinned, device, array or managed memory. |
| **P0** | Validate and safely present unsigned sentinels in every report and export. | Avoid treating `-1` as an ordinary measurement when it represents `UINT64_MAX`; preserve the original value and semantics. |
| **P1** | Latency histograms, percentiles and outlier detection for transfers, runtime, overhead and synchronization. | Detect long tails, anomalous calls and dominant events hidden by averages. |
| **P1** | Semantically decode synchronization types. | Identify the observed wait category without automatically attributing it to blocked CPU time or idle GPU time. |
| **P1** | Combined timeline with independent clock domains and explicit calibration when available. | Visualize host, engine and Nsight without inventing correlations or comparing incompatible timestamps. |
| **P2** | Nsight Compute integration for selective kernel profiling. | Analyze occupancy, throughput, memory behavior, stalls and execution metrics beyond duration/frequency. |
| **P2** | Reproducible comparison across runs and baseline. | Detect regressions in KV cache, transfers, synchronization, kernels and overall performance. |

### Mandatory separation of time metrics

Reports must present these separately:

- CPU time inside CUDA API calls (host-side API duration, when instrumented).
- Kernel execution time (Nsight GPU intervals).
- Transfer time (GPU memcpy/memset intervals).
- Synchronization time (observed synchronization activity and type).
- Total request time (server/engine clock).

**Interpretation rule:** do not simply add these values to produce a supposed total duration. They may overlap, represent different waits, or belong to different clock domains. Every aggregate must declare its source, clock, unit, window and overlap policy.

### C07 evidence motivating this work

C07 contains `ENUM_CUDA_MEMCPY_OPER` and `ENUM_CUDA_MEM_KIND`; the importer can resolve values using metadata in the SQLite itself rather than hard-coding numeric labels.

| Operation | Source → destination memory | Operations | Bytes | Accumulated duration |
|---|---|---:|---:|---:|
| Host-to-Device (`HTOD`) | Pageable → Device | 330 | 945,171,456 (901.3 MiB) | 113.028 ms |
| Device-to-Host (`DTOH`) | Device → Pinned | 260 | 20,590,592 (19.63 MiB) | 2.025 ms |
| Host-to-Device (`HTOD`) | Pinned → Device | 261 | 11,206,352 (10.69 MiB) | 1.328 ms |
| Device-to-Host (`DTOH`) | Device → Pageable | 8 | 8,781,824 (8.37 MiB) | 0.990 ms |

The first category accounts for approximately 95.9% of bytes and 96.4% of accumulated memcpy duration in this capture. This is an investigation priority, not a causal conclusion: inspect distributions, sizes and outliers before attributing the cost to pageable memory or a specific path.

## Phase F — Release and maintenance

- [x] Separate PRs by responsibility with explicit dependencies.
- [x] CI green on current commits of PRs #150–#153 and Tandem.cpp #1.
- [ ] Resolve reviews and merge in order #150 → #151 → #152 → #153; integrate Tandem.cpp #1 after review. Do not merge without authorization.
- [ ] Tag a version and publish release notes.
- [ ] Test installation from release/tag, not only from a checkout.
- [ ] Define Linux/Python/CUDA/Nsight compatibility matrix.
- [ ] Document privacy, permissions, overhead and captured data.
- [ ] Define schema maintenance and backward compatibility.
- [ ] Declare NEPENTHES fully functional only after all gates pass.

## Recommended immediate order

1. CLI run with harmless process and package verification.
2. Build instrumented Tandem.cpp engine on MSI.
3. Real inference with `nepenthes run --profile full`.
4. Inspect engine JSONL and generated Nsight data.
5. Paired LEONES import and audit.
6. Probe coverage matrix and overhead measurement.
7. Repetitions, comparative report and release.

## Definition of “fully functional”

NEPENTHES is complete when a clean installation can wrap a real inference, activate engine probes, capture host/GPU/Nsight, preserve artifacts and hashes, import JSONL and CUPTI activities, generate a navigable report with tables/charts, pass verification, and provide reproducible results without fabricated attribution or correlation.

## Campaign register

Experimental status, C00–C09 IDs, first instrumented inference results and criteria for subsequent campaigns are maintained in [NEPENTHES-CAMPAIGNS-EN.md](NEPENTHES-CAMPAIGNS-EN.md).
