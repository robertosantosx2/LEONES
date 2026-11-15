# NEPENTHES — roadmap to a fully functional release

**Status date:** 2026-11-15 (updated after C07).  
**Status:** CLI and instrumented-engine capture tested with a Qwen3.5-4B inference; full acceptance with Nsight, correlation, coverage, and overhead remains pending.

This roadmap separates implementation, CI validation, and physical validation. A task is not complete merely because a PR exists: it requires the evidence specified in its exit criteria.

## Legend

- [x] Implemented with sufficient evidence for the stated scope.
- [~] Implemented or partially validated; an acceptance test remains.
- [ ] Pending.

## Phase A — Engine instrumentation

- [x] Define the universal event contract and JSONL sink.
- [x] Implement concurrency-safe emission and a shutdown barrier.
- [x] Add JSONL format and sink lifecycle tests.
- [x] Integrate the deterministic probe applier on the pinned llama.cpp revision.
- [x] Build CUDA in CI for target architecture sm_86.
- [x] Run a real Qwen3.5-4B inference on the MSI with the patched binary; confirm emission of 3,683 engine events.
- [~] Audit semantics and coverage of each observed family; all events inside the window use `request_id=0`.
- [~] Audit actual event coverage by subsystem: request/routing, KV cache, transfer, kernel, sync, and allocation observed on Qwen3.5-4B; MoE cache, workers, prefetch, OOM/fallback, and ggml_op dispatch still lack specific acceptance.
- [ ] Measure instrumentation overhead against a control run using an identical protocol.
- [ ] Define and test JSONL rotation/size limits for long runs.

**Phase exit:** a real run with valid JSONL, expected events, accounted errors/losses, and measured overhead.

## Phase B — Installation and CLI

- [x] User-space installer requiring no root.
- [x] `nepenthes` command in `~/.local/bin`.
- [x] `doctor`, `self-test`, `run/capture`, `inspect`, and `verify` commands.
- [x] One-line wrapper with smoke/standard/full profiles.
- [x] `NEPENTHES_RUN_ID` and `NEPENTHES_TRACE_JSONL` variables for instrumented engines.
- [x] Host CPU/RSS capture and device-wide NVIDIA telemetry when available.
- [x] Logs, exit code, manifest, hashes, CSV, JSONL, SQLite, and HTML/Markdown/SVG reports.
- [x] Self-test run on MSI: 3 events, 1 sample, valid HTML and checksums.
- [x] Test `nepenthes run` with a harmless process: exit code 0, verifiable package.
- [x] Test controlled failure propagation: exit code 23 preserved and package valid.
- [x] Test `nepenthes run` with instrumented server and Qwen3.5-4B: real JSONL with 3,683 events, request_start/end, and exit code 0.
- [~] Verify `nepenthes verify` and fully audit the real inference package; Nsight was disabled in C06.
- [ ] Test smoke/standard/full profiles, `--nsys auto/required/off`, and Nsight absence/failure.
- [ ] Run and archive `nepenthes verify` on the C06 inference package.
- [ ] Test engine failure/early termination, Ctrl-C, child process, and partial capture without losing the manifest.
- [ ] Document update, reinstall, and uninstall.

**Phase exit:** a clean installation and reproducible wrapper that leaves a verifiable package even after a controlled failure.

## Phase C — LEONES importer

- [x] Paired JSONL + Nsight import implemented and covered by synthetic tests.
- [x] Preserve SHA-256 and original payload.
- [x] Separate clock domains and explicitly prohibit artificial correlation.
- [x] Read-only Nsight inspection.
- [x] Standalone Nsight-only import with migration 003 and separate tables.
- [x] Adapters for the eight families present in the MSI capture.
- [x] Real MSI import: 151,039 rows, SQLite integrity OK, no duplicates or basic timing anomalies.
- [x] CUDA_EVENT check: the 262 zero timestamps match the source and are preserved without fabricating intervals.
- [~] Validate paired import from a single wrapper execution.
- [ ] Test re-import/idempotency and behavior when the output database already exists.
- [ ] Test different Nsight/SQLite versions and unsupported CUPTI tables containing rows.
- [ ] Verify that output summary, coverage, and manifest expose partial errors rather than hiding them.

**Phase exit:** repeatable, traceable, and integrity-checked paired and standalone imports with honest coverage reporting.

## Phase D — Qwen3.5 capture and experimental validation

- [x] Preserve the historical Nsight capture from 2026-11-14 and its provenance.
- [x] Inspect and import the historical SQLite without paired JSONL.
- [x] Build the descriptive report for the historical capture.
- [x] Apply `tandem.patch`, `runtime.patch`, and probes to pinned llama.cpp revision `f5222f25c18da062ab2b8a2dbbfbf4feae398566`, then build CUDA sm_86 `llama-server` on the MSI. The shallow cafe-llama.cpp checkout was not used.
- [x] Run Qwen3.5-4B Q4_K_M CPU-only with context 512, 4 threads, batch 128, and ubatch 64; capture 3,683 events.
- [ ] Run a Qwen3.5-35B campaign with model and configuration recorded in the manifest.
- [ ] Capture NEPENTHES JSONL and Nsight SQLite simultaneously from the same execution (C06 used `--nsys off`).
- [~] KV cache observed: 49 events inside the C06 window. MoE cache, workers, and prefetch must be verified through explicit events; do not infer them from temporal proximity.
- [ ] Repeat the run at least three times with identical configuration and save controls; include an uninstrumented baseline.
- [ ] Compare overhead, tokens/s, host/GPU memory, kernels, and transfers.
- [ ] Archive logs, model identified by hash, commands, configuration, commit, JSONL, SQLite, NSYS report, response, and checksums.

**Phase exit:** a reproducible paired dataset sufficient to answer performance/lifecycle questions without over-interpreting correlations.

## Phase E — Reports and visualization

- [x] Reusable HTML template and PDF/PNG for the first Qwen3.5-4B report; historical Qwen3.5-35B summary with activity tables.
- [x] Interpretation rules for timestamps, correlation, and coverage.
- [~] HTML/Markdown/SVG report generated by CLI: validated in self-test; first Qwen3.5-4B dashboard generated from available aggregate metrics; automatic generation from real JSONL/SQLite remains pending.
- [ ] Timeline panel for CPU/RSS/GPU with request markers.
- [ ] Kernel distribution by name, duration, and stream.
- [ ] H2D/D2H/D2D transfers by bytes, direction, and Nsight duration.
- [ ] CUDA runtime/synchronization/graph activity by type.
- [ ] KV cache/MoE cache/worker/prefetch views based on real probes.
- [ ] Run and baseline comparison.
- [ ] CSV table export and reproducible queries from SQLite.

**Phase exit:** a report that exposes raw data, summaries, tables, and charts; every metric identifies its source, clock, unit, and attribution level.

## Phase E.1 — Semantic analysis and report quality (new priorities)

The C07 Qwen3.5-4B capture confirms that the importer can expose useful CUDA activity, but reports must decode Nsight enums and preserve attribution limits.

### Prioritized backlog

| Priority | Improvement | Benefit |
|---|---|---|
| **P0** | Semantic decoding of `cudaMemcpyKind` and memory types (`srcKind`/`dstKind`) using the enum tables in the capture itself. | Distinguish H2D, D2H, D2D, Host-to-Array, Unified Memory, and other modes; also identify pageable, pinned, device, array, or managed memory. |
| **P0** | Safe validation and presentation of unsigned sentinels in all reports and exports. | Avoid treating `-1` as an ordinary measurement when it represents `UINT64_MAX`; preserve the original value and its semantics. |
| **P1** | Latency histograms, percentiles, and outlier detection for transfers, runtime, overhead, and synchronization. | Detect long tails, anomalous calls, and dominant events hidden by averages. |
| **P1** | Semantic decoding of synchronization types. | Identify the observed wait class without automatically attributing time to blocked CPU or idle GPU. |
| **P1** | Combined timeline with independent clock domains and explicit calibration where available. | Visualize host, engine, and Nsight in related panels/timelines without inventing correlations or comparing incompatible timestamps. |
| **P2** | Nsight Compute integration for selective kernel profiling. | Analyze internal efficiency: occupancy, throughput, memory, stalls, and execution metrics beyond duration and frequency. |
| **P2** | Reproducible comparison across runs and against a baseline. | Detect regressions in KV cache, transfers, synchronization, kernels, and overall performance. |

### Mandatory separation of timing metrics

Reports must present these separately:

- CPU time inside CUDA calls (host API duration, when instrumented).
- Kernel execution time (Nsight GPU intervals).
- Transfer time (GPU memcpy/memset intervals).
- Synchronization time (observed synchronization activity and type).
- Total request time (server/engine clock).

**Interpretation rule:** these quantities must not be added directly to produce a supposed total time. They may overlap, represent different waits, or belong to different time domains. Every aggregate must declare source, clock, unit, window, and overlap policy.

### C07 evidence motivating this work

The C07 capture contains `ENUM_CUDA_MEMCPY_OPER` and `ENUM_CUDA_MEM_KIND` tables; therefore, the importer can resolve values using metadata from the SQLite itself instead of blindly hardcoding numeric labels. The observed distribution was:

| Operation | Source → destination memory | Operations | Bytes | Accumulated duration |
|---|---|---:|---:|---:|
| Host-to-Device (`HTOD`) | Pageable → Device | 330 | 945,171,456 (901.3 MiB) | 113.028 ms |
| Device-to-Host (`DTOH`) | Device → Pinned | 260 | 20,590,592 (19.63 MiB) | 2.025 ms |
| Host-to-Device (`HTOD`) | Pinned → Device | 261 | 11,206,352 (10.69 MiB) | 1.328 ms |
| Device-to-Host (`DTOH`) | Device → Pageable | 8 | 8,781,824 (8.37 MiB) | 0.990 ms |

The first category accounts for approximately 95.9% of bytes and 96.4% of accumulated memcpy duration in this capture. This is an investigation priority, not a causal conclusion: inspect distributions, sizes, and outliers before attributing the cost to pageable memory or a specific path.

## Phase F — Release and maintenance

- [x] Separate PRs by responsibility with explicit dependencies.
- [x] CI green on current commits of PRs #150–#153 and Tandem.cpp #1.
- [ ] Resolve reviews and merge PRs in dependency order: #150 → #151 → #152 → #153; integrate Tandem.cpp #1 in its repository according to review. Do not merge without authorization.
- [ ] Tag a version and publish release notes.
- [ ] Test installation from a release/tag, not only from a checkout.
- [ ] Define Linux/Python/CUDA/Nsight compatibility and a version matrix.
- [ ] Document privacy, permissions, overhead, and captured data.
- [ ] Define schema maintenance and backward compatibility.
- [ ] Declare NEPENTHES fully functional only after all gates above pass.

## Recommended immediate order

1. CLI test with a harmless process and package verification.
2. Build the instrumented Tandem.cpp engine on the MSI.
3. Run a real inference with `nepenthes run --profile full`.
4. Inspect engine JSONL and generated Nsight data.
5. Import the paired capture into LEONES and audit it.
6. Build the probe coverage matrix and measure overhead.
7. Repeat runs, produce a comparative report, and release.

## Definition of “fully functional”

NEPENTHES will be considered complete when a clean installation can wrap a real inference, activate engine probes, capture host/GPU/Nsight telemetry, preserve artifacts and hashes, import both JSONL events and CUPTI activities, generate a navigable report with tables and charts, pass its verifier, and provide reproducible results without fabricated attribution or correlation.
