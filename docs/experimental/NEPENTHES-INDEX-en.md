# NEPENTHES — Project Index

**Nepenthes is a methodology for experimenting with, measuring, and documenting local inference engines. It is not an inference engine.** Engines are identified separately—for example, `Tandem.cpp` and `cafe-llama.cpp`—and each report documents a specific combination of engine, model, configuration, platform, and campaign.

The goal is to make every run traceable and reproducible: preserve the original request and response, record the effective configuration, measure performance and resource use, evaluate functional correctness, and publish limitations alongside the primary data.

## What Nepenthes documents

Each campaign must clearly distinguish:

- **Engine:** repository, commit, version, build, backend, and runtime parameters.
- **Model:** name, architecture, quantization, size, metadata, and SHA-256 when available.
- **Platform:** CPU, RAM, swap, GPU/VRAM, driver, CUDA, and operating system.
- **Protocol:** prompt, generation parameters, repetitions, cache state, and execution conditions.
- **Results:** tokens/s, latency where measured, CPU/GPU/memory use, temperature, power, and errors.
- **Functional quality:** expected criteria, observed result, tests, and defects.
- **Primary evidence:** manifest, complete responses, resource samples, logs, hash inventory, and reproducible archive.

Unmeasured metrics must be identified as such. Cold-cache and warm-cache measurements must be kept separate, as must system-wide counters and process-attributed metrics. Sending a parameter to an API does not prove that the engine applied it.

## Methodology and documentation

| Resource | Description |
|---|---|
| [Nepenthes methodology](tandem-qwen35-reasoning-budget-methodology-2026-11-12-en.md) | Protocol, evidence structure, script usage, and interpretation rules. |
| [Engine + model report template](NEPENTHES-engine-model-report-template.md) | Reusable structure for documenting each engine/model combination. |

## Current reports and campaigns

### Qwen3.5-35B-A3B — November 2026

| Engine / campaign | Report | Evidence |
|---|---|---|
| **Tandem.cpp** — reasoning-budget battery, 2026-11-12 | [Battery report](tandem-qwen35-reasoning-budget-battery-2026-11-12.md) | [Scripts, monitoring, and artifacts](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/) |
| **cafe-llama.cpp** — independent run, 2026-11-13 | [Execution report](nepenthes-cafe-llama.cpp-qwen3.5-35b-a3b-2026-11-13.md) | [Complete primary data](../../artifacts/benchmarks/qwen35-35b-a3b-engine-comparison-2026-11-13/cafe-llama.cpp/) |

**Important interpretation note:** the cafe-llama.cpp run from 2026-11-13 is an independent test, not a controlled A/B comparison against Tandem.cpp. Its conditions and metrics—including prompt-cache state—must be read in its own report; they must not be presented as a direct performance comparison.

## Reproduction and inspection scripts

The scripts published for the current campaign are located here:

- [Nepenthes runner](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_NEPENTHES_independent_two_sum.py) — sends a request to an already-running server and records the test evidence.
- [Nepenthes inspector](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/inspect_NEPENTHES_independent_run.py) — inspects the saved evidence directory without querying the server.
- [Resource monitor](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py) — shared monitoring dependency.

See the [methodology](tandem-qwen35-reasoning-budget-methodology-2026-11-12-en.md) for requirements, commands, and usage precautions. The runner does not start, stop, or reconfigure the server; every run must use a new output directory.

## Publication conventions

1. Each report corresponds to a specific **engine + model + campaign** combination.
2. Engine and methodology names are not interchangeable: Nepenthes is the methodology; Tandem.cpp and cafe-llama.cpp are engines.
3. Original data is not replaced by summaries. Reports link to the primary evidence.
4. Conditions that prevent two runs from being compared must be explicitly stated.
5. Results should be auditable through logs, manifests, and hashes whenever available.

---

**Location:** `docs/experimental/NEPENTHES-INDEX-en.md`  
**Reference branch:** `benchmarks/tandem-qwen35-reasoning-battery-2026-11-12`
