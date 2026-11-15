# NEPENTHES — implementation, validation, and evidence index

**Status date:** 2026-11-15 (real historical Nsight-only validation completed).  
**Overall status:** functional CLI; CUDA-instrumented engine built on a pinned base; first real inference with engine JSONL; and end-to-end validation of a historical Nsight-only import completed. A paired capture with Nsight, robust correlation, and a coverage/overhead audit of an instrumented run are still outstanding.

## Quick start: install, run, and collect results

> **Distribution status:** the current installer lives inside the LEONES tree. To install it today, you must have that tree available; there is not yet a published standalone NEPENTHES distribution that can be installed without downloading LEONES. Installation is user-space and does not require cloning or building the engines you want to run. Splitting NEPENTHES into a separate repository/release is future work.

### 1. Requirements

- Linux.
- Python 3.10 or newer.
- An executable inference engine and its usual dependencies.
- For NVIDIA telemetry: `nvidia-smi` available.
- For detailed CUDA captures: Nsight Systems compatible with the driver and environment.
- For internal events: an engine binary compiled with NEPENTHES probes. A regular binary can still be run, but it does not emit internal events.

Installation does not require root, install drivers or CUDA, or patch/rebuild the engine.

### 2. Install

From the root of the LEONES checkout containing the installer:

```bash
./scripts/install_nepenthes.sh
export PATH="$HOME/.local/bin:$PATH"
nepenthes doctor
nepenthes self-test
```

The command installs the executable at `~/.local/bin/nepenthes` and resources under `~/.local/share/nepenthes`. `doctor` checks detectable tools and capabilities; `self-test` creates a test capture and validates its artifacts. Neither replaces a real engine run.

### 3. Run an engine

Example with llama.cpp; replace paths and arguments with those from your installation:

```bash
nepenthes run --profile full --nsys auto -- \
  /path/to/llama-server \
  -m /path/to/model.gguf \
  -c 1024
```

Everything after `--` is the engine command and its arguments. NEPENTHES launches the process, preserves its standard output and error in the session package, samples CPU/RSS for the process tree, collects device-wide NVIDIA telemetry when `nvidia-smi` is available, and propagates the engine's exit code.

Available profiles: `smoke` (lightweight), `standard` (default), and `full` (more frequent sampling and automatic Nsight when available). Nsight can be controlled with `--nsys auto`, `--nsys required`, or `--nsys off`. With `required`, execution fails before launching the engine if Nsight is unavailable.

**Important:** NEPENTHES does not instrument an engine's internals by itself. Internal events require a binary compiled with NEPENTHES probes. Without them, only available external telemetry sources (host and, if present, NVIDIA) are collected. Nsight availability does not guarantee that every activity class will be present.

### 4. What results are produced

Each run creates a session directory (RUN_ID). The actual path is displayed/recorded by the run; keep it as `RUN_DIR`. The package may contain:

| Path | Contents |
|---|---|
| `manifest.json` | Run identity, configuration, and provenance |
| `session.log` | Output and errors from the launched process |
| `environment/` | Collected environment data |
| `raw/engine-events.jsonl` | Internal events from an instrumented engine, if emitted |
| `raw/host-events.jsonl` | Host collector samples and events |
| `raw/events.jsonl` | Consolidated event stream, when generated |
| `raw/nsys.sqlite`, `raw/nsys.nsys-rep` | Nsight capture, if enabled and completed |
| `data/samples.csv` | Tabular samples |
| `data/observations.sqlite` | Structured observations |
| `data/summary.json` | Run summary |
| `data/nsys-import.json`, `data/nepenthes-import.sqlite` | Nsight import results, when applicable |
| `reports/index.html`, `reports/report.md` | Navigable HTML report and Markdown summary |
| `checksums.sha256` | Checksums of included artifacts |

Optional artifacts appear only when their source is available and capture completes. Missing files must not be interpreted as zero values or as evidence that an activity did not occur.

### 5. Verify and collect the package

Use the actual session path created by NEPENTHES:

```bash
RUN_DIR="/actual/path/to/RUN_ID"
nepenthes verify "$RUN_DIR"
```

If verification succeeds, preserve the entire directory: it contains the manifest, primary data, reports, and checksums. To share or archive it without modifying the originals:

```bash
tar -czf "nepenthes-$(basename "$RUN_DIR").tar.gz" \
  -C "$(dirname "$RUN_DIR")" "$(basename "$RUN_DIR")"
sha256sum "nepenthes-$(basename "$RUN_DIR").tar.gz"
```

Prefer delivering the complete compressed archive, its SHA-256, and the exit code from `nepenthes verify`. For technical analysis, also preserve the model/identifier and quantization, exact engine arguments, binary version/commit, capture profile, and any Nsight limitations. Do not share model weights unless necessary and you have the right to distribute them.

### 6. What can be concluded

- **Instrumented engine:** supports analysis of internal events emitted by probes, in addition to available external telemetry.
- **Uninstrumented engine:** supports process, host, and available device-wide NVIDIA telemetry; it cannot expose internal engine events that it does not emit.
- **Nsight-only:** supports importing and analyzing activities present in an Nsight capture without fabricating a NEPENTHES run or correlations with missing JSONL.
- **Report:** reflects only collected data. `nvidia-smi` global metrics are device-wide, not necessarily attributable to the process; correlation across clocks or identifiers is declared only when a validated mechanism exists.

See [NEPENTHES-CLI.md](NEPENTHES-CLI.md) for all options and [NEPENTHES-IMPORTER.md](NEPENTHES-IMPORTER.md) for the import contract.

## Executive summary

NEPENTHES currently has four work blocks in LEONES and an instrumentation integration in Tandem.cpp:

1. Universal instrumentation and JSONL sink in Tandem.cpp (PR #1).
2. LEONES importer for JSONL + Nsight/CUPTI (PR #151).
3. User-space installer, one-line CLI, host/GPU capture, and report package (PR #152).
4. Historical Nsight-only import with isolated provenance (PR #153).

Current PR status: LEONES #150 remains open and is currently not mergeable; #151 is closed and integrated into branch `research/nepenthes-universal-collector-20261115` (not into `main`); #152 and #153 are closed and integrated into `main`. Tandem.cpp #1 remains open and unmerged. Do not confuse historical PRs with the current integration state.

**Physical MSI validation completed so far:**
- Local CUDA build of the instrumented engine on pinned llama.cpp `f5222f25c18da062ab2b8a2dbbfbf4feae398566`, after applying `tandem.patch`, `runtime.patch`, and the deterministic probe applier.
- First real Qwen3.5-4B Q4_K_M inference through the instrumented server, CPU-only, captured by `nepenthes run`; 3,683 engine events and 3,117 inside the request_start/request_end window.
- 49 KV cache events inside the request window; 2,540 transfers, 290 kernels, and 226 synchronizations inside the window.
- Monotonic request time 1.864918 s, consistent with the server's 1,864.85 ms; 10 prompt tokens, 16 generated tokens, prefill 21.50 tok/s, and decode 10.72 tok/s.
- Every event in the window has `request_id=0`; segmentation is temporal, not robust per-request correlation.
- User-space installation successful.
- `nepenthes doctor`: environment detected correctly.
- `nepenthes self-test`: successful; 3 events, 1 sample, HTML, checksums, and event integrity valid.
- Historical Nsight SQLite inspection and subsequent standalone import: 151,039 activities.
- End-to-end revalidation from LEONES `main` at `d548a37cc4f05632eba946495ad9d98bdf862c63`: CLI `--nsys-only` exit code 0 and independent destination `qwen35-nsys-only.sqlite` (~90 MiB).
- Independent destination audit: exact distribution across eight CUPTI families, 151,039 unique IDs, unique table/activity pairs, matching SHA-256 and provenance, zero unsupported rows, `integrity_check=ok`, and empty `foreign_key_check`.
- Revalidation import ID: `qwen35-real-nsys-only-20261115`; `run_id=null`, `jsonl=null`, no fabricated correlation.
- The Nsight source retains SHA-256 `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`; it was not modified.

**Not yet demonstrated:** coverage of every probe, Nsight capture during the same run, paired JSONL+Nsight import, request-to-kernel correlation, overhead measurement, and a complete coverage audit.

## Source of truth and changes

| Area | PR / branch | Current status |
|---|---|---|
| Tandem.cpp universal instrumentation | [Tandem.cpp #1](https://github.com/robertosantosx2/tandem.cpp/pull/1), `nepenthes/universal-observability-20261114` | Open, unmerged |
| Index and documentation | [LEONES #150](https://github.com/robertosantosx2/LEONES/pull/150), `research/nepenthes-universal-collector-20261115` | Open; GitHub reports `mergeable=false` |
| JSONL + Nsight importer | [LEONES #151](https://github.com/robertosantosx2/LEONES/pull/151), `feat/nepenthes-nsys-importer-20261115` | Merged into research branch, not `main` |
| Installer and CLI | [LEONES #152](https://github.com/robertosantosx2/LEONES/pull/152), `feat/nepenthes-cli-installer-20261115` | Merged into `main` |
| Nsight-only importer | [LEONES #153](https://github.com/robertosantosx2/LEONES/pull/153), `feat/nepenthes-nsys-only-20261115` | Merged into `main` (merge `838de99`); CI 7/7 on functional HEAD `9e0383e` |

The seven workflows associated with functional HEAD `9e0383e7d84334bb2935c229722c9b7a80ac02af` of LEONES #153 completed successfully. Subsequent commits on this branch only correct documentation; GitHub has not associated new workflows with those commits. The statuses of #150, #151, and #152 are listed separately above. CI validates automated contracts; it does not replace physical engine testing.

## Capability status

| Capability | Status | Evidence / limitation |
|---|---|---|
| Universal event contract and JSONL sink | Implemented | Tandem.cpp PR #1; CI success |
| Sink shutdown barrier and concurrency | Implemented and CI-tested | Does not imply a real MSI capture |
| Deterministic probe application in Tandem.cpp | Implemented in patch | CUDA CI build; runtime coverage measurement pending |
| User-space installer | Implemented and executed | MSI: successful installation under `~/.local` |
| One-line `nepenthes run` CLI | Implemented and tested with instrumented engine | Real Qwen3.5-4B: engine JSONL, exit code 0, and 3,683 events; Nsight disabled in this test |
| Doctor and self-test | Executed successfully | MSI: 3 events, 1 sample, HTML report |
| CPU/RSS sampling for process tree | Implemented | Self-test; real engine profile pending |
| NVIDIA global sampling via nvidia-smi | Implemented | Doctor detects nvidia-smi; full inference capture pending |
| Optional/required/off Nsight capture | Implemented | Real wrapper run with Nsight on MSI pending |
| CSV/JSONL/SQLite/Markdown/HTML/SVG package | Implemented; inference acceptance partial | Real engine JSONL captured; full package verification and audit of inference package pending |
| Hash and structure verification | Implemented | Self-test passed; verification on real capture pending |
| Paired JSONL + Nsight importer | Implemented and CI-tested | Real paired run validation pending |
| Nsight schema inspection | Implemented and executed | MSI: 8 CUPTI tables recognized |
| Nsight-only import | Implemented, CI success, historical real E2E passed | MSI: 151,039 rows; 8/8 detected CUPTI tables imported; 0 unsupported rows; provenance, uniqueness, and integrity audit passed |
| Provenance, hashes, and partial coverage | Implemented | Standalone import with `run_id=null`, no JSONL |
| Request-to-kernel correlation across clocks | Deliberately not implemented | Requires common IDs and calibration; must not be inferred by proximity |
| Historical Qwen3.5-35B report | Documented | Historical Nsight-only capture, no paired JSONL |
| First Qwen3.5-4B capture | Captured; campaign report | Real CPU-only inference with instrumented engine; Nsight off; request_id=0 |
| Probe coverage matrix per run | Partial | Qwen3.5-4B confirms request, routing, KV, transfer, kernel, sync, and allocation; MoE/workers/prefetch/OOM not yet accepted |
| Repeatable test suite and cross-run comparison | Pending | Requires paired captures and manifests |

## Roadmap

The detailed operational roadmap is in [NEPENTHES-ROADMAP.md](NEPENTHES-ROADMAP.md).

1. **Close the PR tree:** review, resolve comments, and merge in dependency order with explicit authorization.
2. **MSI end-to-end test:** `doctor`, `self-test`, `run --profile smoke` with a harmless command, then an instrumented engine; verify logs, exit code, and package.
3. **Real instrumented capture:** Qwen3.5 or another patched Tandem engine, JSONL + host + Nsight in the same RUN_ID; validate losses and overhead.
4. **Paired import:** validate tables, hashes, coverage, and correlation limits in LEONES.
5. **Probe coverage:** matrix for request/graph, KV, MoE cache, workers, prefetch, alloc/free, OOM/fallback, and transfers.
6. **Comparative reports:** tables and charts with time series, kernels, transfers, memory, and performance, distinguishing observation, estimation, and measurement.
7. **Reproducible release:** clean installation, tests, documentation, manifest, checksums, and uninstall/update procedure.

## Historical Qwen3.5-35B capture

Full report: [NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

The MSI Nsight-only import contains 151,039 activities:
- kernel 8,982; memcpy 44,488; memset 9; runtime 84,116;
- graph trace 5,207; synchronization 7,864; CUDA event 262; overhead 111.

Declared coverage: `complete_for_detected_cupti_tables`, with 8 detected tables, 151,039 imported rows, and zero unsupported rows/tables. This does not mean every category Nsight could produce is present in the file. The independent audit confirmed 151,039 unique IDs, 151,039 unique table/activity pairs, `integrity_check=ok`, and an empty `foreign_key_check`. The 262 CUDA_EVENT records have `timestamp=0` in both source and imported SQLite; they are preserved as point events without a time interval. They are not used to reconstruct duration.

## Evidence rules

- `CI_PASS` means automated tests for the commit passed.
- `INSTALLED` means the installer completed on the MSI.
- `SELF_TEST_PASS` means the self-diagnostic produced a valid test package.
- `CAPTURED` requires a real engine run and preserved artifacts.
- `MEASURED` is used only for values derived from an identified real capture.
- `ESTIMATED` is never presented as measured.
- Do not join NEPENTHES `request_id` with CUPTI `correlationId`, or monotonic clocks with Nsight timestamps, without a demonstrated correlation mechanism.
- `nvidia-smi` GPU utilization/memory is device-wide; do not attribute it to a process without evidence.
- Host submission spans are not GPU execution duration.
