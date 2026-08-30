# JALÓN 5 — Physical Runtime Execution v1

## Purpose

Convert the closed JALÓN 4 decision into a reproducible physical execution boundary without creating a second benchmark architecture.

JALÓN 5 does **not** redefine model selection, task benchmarks, Artificial Analysis methodology, or evidence. It consumes the existing LEONES contracts and produces execution input for the already-defined measurement/evidence chain.

## Canonical chain

```text
LEONES → ODS | Magnitude decision
          ↓
selection / execution plan
          ↓
physical-host preflight
          ↓
runtime launch
          ↓
independent task benchmark
          ↓
runtime-benchmark.v1
          ↓
evidence.v1 / Atlas bridge
```

## Boundary

The repository may prepare and validate everything that does not require the physical machine. The physical host is required only for:

- actual hardware detection;
- installed driver/runtime detection;
- model artifact availability;
- runtime launch;
- real execution;
- real latency/throughput/memory measurements;
- preservation of execution logs and hashes.

CI must never manufacture physical measurements.

## Runtime policy

The first physical runners are **llama.cpp, vLLM and SGLang** when the selected workload and hardware support them. Existing adapters/executors remain authoritative; JALÓN 5 must not introduce a parallel runtime-selection mechanism.

Every physical execution must retain:

- runtime name and version;
- model id/revision;
- quantization;
- hardware and driver facts;
- exact launch command or a hashable equivalent;
- context and generation parameters;
- execution id;
- UTC start/finish timestamps;
- raw runtime output/log reference;
- benchmark result;
- evidence hash/provenance.

## CPD gate

A physical runner is **CPD-gated** when it declares that execution requires the physical host and refuses to represent a local/CI dry run as measured evidence.

A preparation command may emit a plan. `--execute` is an explicit physical-execution boundary, not permission to invent or simulate measurements.

## Measurement rule

The JALÓN 4 task-completion benchmark suite is the workload authority. Runtime speed metrics remain supporting efficiency measurements. A faster runtime does not override task success.

`estimated`, `reported`, `observed`, `configured`, and `measured` remain separate states.

## Evidence rule

Only successful physical execution may create `measured` evidence. A failed, skipped, unavailable, simulated, or CI-only run is never promoted to measured evidence.

## Definition of Done

JALÓN 5 is complete only when a real physical host has produced at least one reproducible execution through the canonical LEONES path, with preserved raw evidence and validation passing. Until then, repository work is preparation/contract work and must not be marked completed.

## Current stage

**PREPARED — PHYSICAL HOST REQUIRED FOR EXECUTION.**

The next Ubuntu intervention is deliberately narrow: run the repository preflight, identify the available runtime/model/hardware path, execute one controlled smoke benchmark, and preserve the resulting evidence before scaling out.
