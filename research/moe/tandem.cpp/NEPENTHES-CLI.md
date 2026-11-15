# NEPENTHES: installer, CLI, and capture package

## Purpose

NEPENTHES is installed in user space and invoked before the inference engine. It launches the requested command, enables instrumentation in an engine that has already been compiled with NEPENTHES probes, collects available host/GPU telemetry, and generates a results package. Installation does not require root and does not modify drivers, CUDA, models, or engine binaries.

## Installation and diagnostics

```bash
./scripts/install_nepenthes.sh
export PATH="$HOME/.local/bin:$PATH"
nepenthes doctor
nepenthes self-test
```

The installer places `nepenthes` in `~/.local/bin` and resources in `~/.local/share/nepenthes`. It includes the CLI, importer, and migrations 002/003. Python 3.10+ is required.

## Invocation

```bash
nepenthes run --profile full -- ./llama-server -m /path/to/model.gguf -c 1024
```

The command after `--` is executed as a child process. NEPENTHES preserves stdout/stderr in the session log, samples CPU/RSS for the process tree, records device-wide NVIDIA telemetry when `nvidia-smi` is available, and propagates the engine's exit code.

Before launch, it sets `NEPENTHES_RUN_ID` and `NEPENTHES_TRACE_JSONL`. An instrumented Tandem.cpp engine can emit internal events to `raw/engine-events.jsonl`; the host collector writes `raw/host-events.jsonl`, and both streams are consolidated into `raw/events.jsonl`. An uninstrumented engine can still be monitored for host/GPU telemetry, but it does not produce internal engine events. The CLI does not patch or rebuild the engine.

## Profiles and Nsight

- `smoke`: lightweight sampling.
- `standard`: standard sampling (default).
- `full`: more frequent sampling and automatic Nsight capture when available.

Controls:
- `--nsys auto`: select automatically according to profile and availability.
- `--nsys required`: fail before launch if Nsight is unavailable.
- `--nsys off`: disable Nsight, not the engine event sink.
- `--interval SECONDS`: change the sampling interval.

Nsight may add overhead or fail because of driver incompatibility, permissions, or configuration. NEPENTHES does not elevate privileges automatically. Native artifacts are preserved in `raw/`.

## Output package

```text
RUN_ID/
  manifest.json
  session.log
  environment/
  raw/
    host-events.jsonl
    engine-events.jsonl
    events.jsonl
    nsys.sqlite
    nsys.nsys-rep
  data/
    samples.csv
    observations.sqlite
    summary.json
    nsys-import.json
    nepenthes-import.sqlite
  reports/
    index.html
    report.md
  checksums.sha256
```

Files that depend on instrumentation or Nsight are included only when those sources are available. The HTML/Markdown report is built from the samples and activities actually collected; SVG plots must not be mistaken for simulated data. `nepenthes verify RUN_DIR` validates package hashes and structure.

## MSI validation status — 2026-11-15

- User-space installer: successful; command installed at `~/.local/bin/nepenthes`.
- `nepenthes doctor`: successful; Linux, Python, procfs, `nvidia-smi`, and Nsight Systems were detected in the recorded validation.
- `nepenthes self-test`: successful; 3 events, 1 sample, 3 event rows, `events_valid=true`, `report_html=true`, `checksums=true`, and `errors=[]`.
- Real run with an instrumented engine: completed with Qwen3.5-4B Q4_K_M in CPU-only mode through `nepenthes run`; 3,683 engine events were captured, including `request_start/request_end`, and the process exited with code 0.
- Capture C06 used `--nsys off`; therefore, it does not yet demonstrate an integrated Nsight run or replace acceptance of a paired JSONL+Nsight capture.
- Real historical Nsight-only import: 151,039 activities imported and audited; see the [Qwen3.5 historical report](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

**Still pending:** run `nepenthes verify` and audit the complete package from real inference C06; perform a paired JSONL+Nsight capture from the same run; measure overhead and complete the coverage matrix. The self-test and historical Nsight-only import do not replace these tests.

## Limitations

`nvidia-smi` telemetry is device-wide. Internal events require an instrumented binary. Nsight capture adds overhead. Do not join `request_id` with CUPTI `correlationId`, or mix clocks, without calibration. Individual kernel durations come from Nsight/CUPTI.
