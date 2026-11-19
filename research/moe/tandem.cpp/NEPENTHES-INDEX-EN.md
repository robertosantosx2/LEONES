# NEPENTHES — implementation, validation and evidence index

**Language:** [English](NEPENTHES-INDEX-EN.md) · [Español](NEPENTHES-INDEX.md)

**Status date:** 2026-11-15 (after the first instrumented Qwen3.5-4B inference).  
**Overall status:** CLI operational; CUDA-instrumented engine built on a pinned base; first real inference emitted engine JSONL. Paired Nsight capture, robust correlation, coverage audit and overhead measurement remain open.

## Executive summary

NEPENTHES currently has four LEONES workstreams and an instrumentation integration in Tandem.cpp:

1. Universal instrumentation and JSONL sink in Tandem.cpp (PR #1).
2. LEONES importer for JSONL + Nsight/CUPTI (PR #151).
3. User-space installer, one-line CLI, host/GPU capture and report package (PR #152).
4. Historical Nsight-only import with isolated provenance (PR #153).

LEONES PRs #150–#153 are open and unmerged. PR #153 is a draft stacked on #152; #152 is stacked on #151; #151 is stacked on #150. Tandem.cpp PR #1 is also open and unmerged.

## Physical validation on the MSI

- CUDA build of the instrumented engine on pinned llama.cpp base `f5222f25c18da062ab2b8a2dbbfbf4feae398566`, after applying `tandem.patch`, `runtime.patch` and the deterministic probe applier.
- First real Qwen3.5-4B Q4_K_M inference through the instrumented server, CPU-only, captured with `nepenthes run`: 3,683 engine events, 3,117 inside the request window.
- 49 KV-cache events inside the request window; 2,540 transfers, 290 kernels and 226 synchronization events inside that window.
- Monotonic request duration 1.864918 s, consistent with the server's 1,864.85 ms; 10 prompt tokens, 16 generated tokens, prefill 21.50 tok/s and decode 10.72 tok/s.
- All events in the window have `request_id=0`; this is temporal segmentation, not robust request-ID correlation.
- User-space installation succeeded; `nepenthes doctor` and `nepenthes self-test` passed.
- Historical Nsight SQLite was inspected and imported standalone: 151,039 activities.
- Imported SQLite: `integrity_check=ok`, no foreign-key errors, unique IDs and no basic temporal anomalies.
- Historical source SHA-256: `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`; source was not modified.

## Not yet demonstrated

Complete probe coverage, Nsight capture in the same execution, paired JSONL+Nsight import, request-to-kernel correlation, instrumentation overhead, and quantitative optimization recommendations.

## Source of truth and change status

| Area | PR / branch | Status |
|---|---|---|
| Tandem.cpp universal instrumentation | [Tandem.cpp #1](https://github.com/robertosantosx2/tandem.cpp/pull/1), `nepenthes/universal-observability-20261114` | Open; CI success |
| Index and documentation | [LEONES #150](https://github.com/robertosantosx2/LEONES/pull/150), `research/nepenthes-universal-collector-20261115` | Open; CI success |
| JSONL + Nsight importer | [LEONES #151](https://github.com/robertosantosx2/LEONES/pull/151), `feat/nepenthes-nsys-importer-20261115` | Open; CI success |
| Installer and CLI | [LEONES #152](https://github.com/robertosantosx2/LEONES/pull/152), `feat/nepenthes-cli-installer-20261115` | Open, draft; CI success |
| Nsight-only importer | [LEONES #153](https://github.com/robertosantosx2/LEONES/pull/153), `feat/nepenthes-nsys-only-20261115` | Open, draft; CI success |

CI validates the committed tree and defined contracts; it does not replace physical engine tests.

## Capability status

| Capability | Status | Evidence / limitation |
|---|---|---|
| Universal event contract and JSONL sink | Implemented | Tandem.cpp PR #1 |
| Concurrent sink shutdown barrier | Implemented and CI-tested | Does not imply physical MSI capture |
| Deterministic probe application | Implemented | CUDA build; runtime coverage still needs auditing |
| User-space installer | Implemented and executed | MSI installation under `~/.local` |
| One-line `nepenthes run` | Implemented and tested with instrumented engine | Real Qwen3.5-4B JSONL; Nsight disabled in that test |
| Doctor and self-test | Passed | MSI: 3 events, 1 sample, HTML report |
| CPU/RSS process-tree sampling | Implemented | Real engine profile still needed |
| NVIDIA global sampling via nvidia-smi | Implemented | Full inference capture still needed |
| Nsight optional/required/off | Implemented | Full wrapper capture with Nsight still needed |
| CSV/JSONL/SQLite/Markdown/HTML/SVG package | Implemented; inference acceptance partial | Real engine JSONL exists; full package audit remains |
| Hash and structure verification | Implemented | Self-test passed; verify on real inference pending |
| Paired JSONL + Nsight importer | Implemented and CI-tested | Real same-run pair pending |
| Nsight schema inspection | Implemented and executed | MSI: eight CUPTI tables recognized |
| Nsight-only import | Implemented, CI success and executed | MSI: 151,039 rows, integrity passed |
| Provenance, hashes and partial coverage | Implemented | Standalone import has `run_id=null`, no JSONL |
| Request-to-kernel correlation across clocks | Deliberately not implemented | Requires shared IDs and calibration |
| Historical Qwen3.5-35B report | Documented | Historical Nsight-only data |
| Qwen3.5-4B first capture | Captured | Real CPU-only instrumented inference; Nsight off |
| Probe coverage matrix | Partial | Request/routing, KV, transfer, kernel, sync and allocation observed; MoE/workers/prefetch/OOM not accepted |
| Repeatable battery and run comparison | Pending | Requires paired captures and manifests |

## Roadmap

See the detailed [roadmap](NEPENTHES-ROADMAP-EN.md) and [campaign register](NEPENTHES-CAMPAIGNS-EN.md).

1. Review and resolve the PR stack; merge only in dependency order and with explicit authorization.
2. Run end-to-end MSI tests: doctor, self-test, harmless smoke command, then instrumented engine; verify logs, exit code and package.
3. Capture an instrumented engine with engine JSONL + host + Nsight under the same RUN_ID; audit losses and overhead.
4. Validate paired import, hashes, coverage and correlation limits.
5. Build a probe coverage matrix for request/graph, KV, MoE cache, workers, prefetch, alloc/free, OOM/fallback and transfers.
6. Produce comparative reports distinguishing observation, estimation and measurement.
7. Release reproducibly with clean installation, tests, manifest, checksums and uninstall/update procedure.

## Evidence rules

- `CI_PASS`: automated tests for the commit passed.
- `INSTALLED`: installer completed on the MSI.
- `SELF_TEST_PASS`: diagnostic test package is valid.
- `CAPTURED`: a real engine execution and retained artifacts exist.
- `MEASURED`: value derived from an identified real capture.
- `ESTIMATED` must never be presented as measured.
- Never join NEPENTHES `request_id` to CUPTI `correlationId`, or monotonic clocks to Nsight timestamps, without a demonstrated correlation mechanism.
- nvidia-smi GPU utilization/memory is device-wide; do not attribute it to a process without evidence.
- Host submission spans are not GPU execution durations.

## Historical Qwen3.5-35B capture

See the [historical report](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115-EN.md). The standalone import contains 151,039 activities across eight detected CUPTI tables. The 262 CUDA_EVENT rows have timestamp zero and are retained as point records without an inferred interval.
