# NEPENTHES: installer, CLI and capture package

**Language:** [English](NEPENTHES-CLI-EN.md) · [Español](NEPENTHES-CLI.md)

## Purpose

NEPENTHES is installed in user space and invoked before the engine. It launches the requested command, activates instrumentation in an engine already built with NEPENTHES probes, collects available host/GPU telemetry and creates a result package. Installation requires no root privileges and does not modify drivers, CUDA, models or engine binaries.

## Installation and diagnostics

```bash
./scripts/install_nepenthes.sh
export PATH="$HOME/.local/bin:$PATH"
nepenthes doctor
nepenthes self-test
```

The CLI is installed under `~/.local/bin` and resources under `~/.local/share/nepenthes`. The installer includes the CLI, importer and migrations 002/003. Python 3.10+ is required.

## Invocation

```bash
nepenthes run --profile full -- ./llama-server -m /path/model.gguf -c 1024
```

The command after `--` runs as a child process. NEPENTHES preserves stdout/stderr in the session log, samples CPU/RSS for the process tree, records global NVIDIA telemetry when `nvidia-smi` is available, and propagates the engine's exit code.

Before launch, it defines `NEPENTHES_RUN_ID` and `NEPENTHES_TRACE_JSONL`. An instrumented Tandem.cpp engine can emit internal events to `raw/engine-events.jsonl`; the host collector writes `raw/host-events.jsonl`; both streams are consolidated into `raw/events.jsonl`. An uninstrumented engine can still be monitored at host/GPU level but emits no internal engine events. The CLI does not patch or rebuild the engine.

## Profiles and Nsight

- `smoke`: lightweight sampling.
- `standard`: standard sampling (default).
- `full`: more frequent sampling and automatic Nsight capture when available.

Controls:
- `--nsys auto`: automatic selection based on profile and availability.
- `--nsys required`: fail before launch if Nsight is unavailable.
- `--nsys off`: disable Nsight, not the engine sink.
- `--interval SECONDS`: change sampling interval.

Nsight can add overhead or fail because of driver incompatibility, permissions or configuration. NEPENTHES does not elevate privileges automatically. Native artifacts are retained under `raw/`.

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

Files requiring instrumentation or Nsight appear only when available. HTML/Markdown reports are built from collected samples and activities; SVG charts must not be mistaken for simulated data. `nepenthes verify RUN_DIR` validates package hashes and structure.

## MSI validation status — 2026-11-15

- Installed branch: `feat/nepenthes-nsys-only-20261115`, commit `6889e967`.
- Installer succeeded; command installed at `~/.local/bin/nepenthes`.
- `nepenthes doctor`: passed; Linux 7.0.0-43, Python 3.14.4, procfs, `/usr/bin/nvidia-smi`, Nsight Systems at `/usr/local/cuda-13.4/bin/nsys`.
- `nepenthes self-test`: passed; run `20261115_084802_self-test_2ee4af8e`; 3 events, 1 sample, 3 event rows, `events_valid=true`, `report_html=true`, `checksums=true`, `errors=[]`.
- Real Nsight-only import: 151,039 activities; see the [historical Qwen3.5 report](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115-EN.md).

**Pending:** a real instrumented-engine run through `nepenthes run`, checking activation variables, exit code, engine events, Nsight and `nepenthes verify` on the resulting package. The self-test does not replace this test.

## Limitations

`nvidia-smi` telemetry is device-wide. Internal probes require an instrumented binary. Nsight adds overhead. Do not join `request_id` to CUPTI `correlationId`, or mix clocks, without calibration. Individual kernel durations come from Nsight/CUPTI.
