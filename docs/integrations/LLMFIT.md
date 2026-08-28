# LLMFit → LEONES

## Purpose

LLMFit is the **first-pass model-fit estimator** in RC1. LEONES consumes its output; it does not reproduce its hardware detector or fit engine.

Upstream: [AlexsJones/llmfit](https://github.com/AlexsJones/llmfit)

## Current upstream capabilities

The current LLMFit documentation describes:

- hardware detection;
- model fit ranking;
- estimated speed;
- quality/context dimensions;
- JSON output for automation;
- `fit`, `recommend --json`, `info`, `bench`, and `doctor` commands;
- local providers including Ollama, llama.cpp, MLX, Docker Model Runner and LM Studio;
- real benchmark collection that can replace estimates with community measurements.

That makes a large amount of the hardware/model-fit problem already solved upstream.

## LEONES responsibility

LEONES adds the missing governance boundary:

```text
LLMFit estimate
     ↓
provenance preserved
     ↓
LEONES candidate
     ↓
Atlas/evidence
     ↓
ODS or Magnitude decision
     ↓
physical execution
     ↓
LEONES measurement
```

The integration must never silently turn an LLMFit estimate into a LEONES measurement.

## Minimal adapter

`scripts/integrations/llmfit.py` intentionally does only two things:

1. normalize captured fit data;
2. enforce that the provenance remains `estimated`.

It does **not**:

- install LLMFit;
- invoke LLMFit;
- detect hardware itself;
- benchmark models;
- select ODS/Magnitude;
- rewrite Atlas evidence.

Those responsibilities remain outside this boundary.

## Why this is minimal

LLMFit already has a CLI/automation surface and a real benchmark feature. Reimplementing those capabilities in LEONES would violate the RC1 rule of using upstream capabilities before building duplicates.

The next integration step is therefore an execution-level adapter only after the contract and local fixture are stable.

## Ubuntu gate

No Ubuntu execution is required for the current adapter.

Ubuntu becomes necessary only when we need to demonstrate:

- LLMFit's actual hardware detection on the target machine;
- an actual model-fit decision;
- a real ODS/Magnitude installation;
- or a physical benchmark.

Until then, contracts and fixtures are sufficient.
