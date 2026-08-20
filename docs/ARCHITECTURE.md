# LEONES architecture

## Purpose

This document explains the system without requiring knowledge of the development history.

LEONES is an experimental ecosystem for running useful local agentic AI on consumer hardware. The project prioritises Open software and, among Open alternatives, Copyleft.

The key engineering rule is **small, composable scripts**. Each script does one clearly defined job. A higher-level command may call several of them, but the lower-level scripts remain independently understandable and testable.

## The complete pipeline

```text
USER / MACHINE
      │
      ▼
┌──────────────────────┐
│ leones-hardware      │  identify machine
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ llmfit preselector   │  first hardware/model estimate
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ leones-model         │  identify + verify model
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ leones-infer         │  measure inference
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ leones-lotb          │  measure agentic tasks
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ leones-report        │  create Markdown result
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ leones-publish       │  validate and publish
└──────────┬───────────┘
           ▼
 GitHub / metaLEONES / web
```

`leones.py` may orchestrate this sequence, but it should contain as little domain logic as possible.

`llmfit` is deliberately a **preselector**, not a source of truth. Its estimates reduce the candidate space before LEONES applies identity/evidence, openness, task suitability and measured performance.

## Architecture layers

### 1. Knowledge

Buddy is a central candidate component because LEONES wants knowledge and context to remain controlled when the model, backend or hardware changes.

```text
Knowledge / context
        │
      Buddy
        │
        ▼
Agent / harness
        │
        ▼
Local inference API
        │
        ▼
Model + backend
        │
        ▼
Hardware
```

The layers must remain replaceable where practical.

### 2. Hardware-aware model preselection

`llmfit` occupies the first decision layer after hardware identification:

```text
hardware + user intent
          │
          ▼
        llmfit
          │
          ├── fit estimate
          ├── quality estimate
          ├── speed estimate
          ├── context fit
          ├── quantisation
          ├── run mode
          └── runtime
          │
          ▼
      TOP-N candidates
          │
          ▼
 LEONES evidence + Router
```

The output is explicitly an **estimate**. It must never be recorded as a LEONES measurement merely because it was produced locally.

The adapter should preserve the external values independently, for example:

- `llmfit_quality_estimate`;
- `llmfit_speed_estimate`;
- `llmfit_fit`;
- `llmfit_context_fit`;
- `llmfit_quantization`;
- `llmfit_run_mode`;
- `llmfit_memory_estimate`;
- `llmfit_runtime`;
- `llmfit_source_version`.

### 3. Inference

Inference measures the model/backend/hardware combination. It must not be confused with agentic performance.

Minimum concepts:

- model identifier;
- quantisation;
- model SHA-256 where available;
- backend and version/commit;
- prompt evaluation speed;
- generation speed;
- memory;
- total time;
- stability/errors.

### 4. Agentic evaluation

LOTB measures whether an agent can complete defined tasks:

- B01 — memory/locality;
- B02 — files;
- B03 — multistep task;
- B04 — recovery from failure;
- B05 — local coding.

A fast model is not automatically a good agent.

### 5. Evidence

A result must preserve enough technical information to be understood and reproduced. Third-party benchmark numbers are useful for research but are not official LEONES measurements.

## Hardware profiles

The project uses memory as a central classification variable:

- H0 — 8 GB: stress profile;
- H1 — 16 GB: first reference profile;
- H2 — 32 GB;
- H3 — 64 GB.

CPU and GPU are recorded separately. A profile describes a class of hardware; a result describes an actual experiment.

## Performance thresholds

The current usability reference is:

- **10 tok/s** — minimum LEONES usability threshold;
- **100 tok/s** — comparison ceiling, not a universal requirement.

Task completion time and success are equally important. LEONES therefore avoids reducing agentic UX to tok/s.

## metaLEONES

metaLEONES is the contribution protocol for real-world measurements.

```text
hardware → model → inference → LOTB → report.md → validation → GitHub
```

The report identifies the experiment, not the person.

Never publish names, emails, personal usernames, identifiable hostnames, serial numbers, UUIDs, MAC/IP addresses, exact location, personal paths, credentials or tokens.

Result states:

```text
reported → reproducible → verified
                 │
                 └── rejected
```

A `reported` result must never be presented as `verified`.

## Discovery and recommendations

LEONES also has a prospecting layer. It looks for new Open projects and prioritises Copyleft candidates, especially projects that can improve models, inference, harnesses, tools, skills or agentic UX.

Discovery is deliberately separate from acceptance:

```text
discover → inspect → classify → test → recommend → incorporate
```

Finding a project does not mean that LEONES endorses it.

## Automation

GitHub Actions may call the small scripts to:

- perform scheduled discovery;
- aggregate public results;
- regenerate statistics and charts;
- produce weekly/monthly reports;
- prepare community/social content.

Automation must not bypass privacy checks or turn unverified information into official results.

## Design rules for scripts

Every script should answer one question. Its documentation must state:

1. what it does;
2. what it does not do;
3. inputs;
4. outputs;
5. dependencies;
6. examples;
7. exit/error behaviour;
8. related scripts.

Prefer composition over duplication. If a script needs another capability, call the existing script or shared module rather than copying its implementation.

## Vocabulary

- **LEONES** — Local Ecosystem of Open Neural Expert Systems.
- **Buddy** — central candidate knowledge/context layer.
- **llmfit** — hardware-aware external preselector for the first model estimate.
- **LOTB** — agentic task battery.
- **metaLEONES** — protocol for anonymised real-machine reports.
- **CABE** — project vocabulary for whether a configuration fits.
- **RULA** — project vocabulary for whether a configuration runs.

The historical conversation is not required to understand these concepts; this repository documentation is the canonical explanation.
