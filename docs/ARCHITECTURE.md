# LEONES architecture

## Purpose

LEONES is an experimental ecosystem for running useful local agentic AI on consumer hardware. The project prioritises Open software and, among Open alternatives, Copyleft.

The key engineering rule is **small, composable scripts**. Each script does one clearly defined job. A higher-level command may orchestrate several of them, but execution must not be duplicated across competing runners.

## Canonical execution pipeline

The operational path is:

```text
USER / MACHINE
      │
      ▼
Hardware identification
      │
      ▼
LLMFit / external candidate estimates
      │
      ▼
LEONES model identity + evidence
      │
      ▼
runtime-selection.v1
      │
      ▼
existing Agentic Runner
      │
      ▼
trusted RuntimeAdapter
      │
      ▼
physical runtime
      │
      ▼
measurement
      │
      ▼
grader / task result
      │
      ▼
evidence + validation
      │
      ▼
recommendation / MANADA publication
```

**There is one execution boundary.** `benchmarks.agentic.runner` is the canonical runner. Task-specific adapters and CLI bridges may prepare inputs or translate a selected plan, but they must delegate execution to the existing runner boundary rather than introduce a second runner architecture.

`leones.py` and higher-level commands may orchestrate this sequence, but they should contain as little domain and execution logic as possible.

## Runner boundary

The canonical runner provides:

- append-only execution traces;
- execution configuration and task identity;
- selected-runtime preparation through `RuntimeAdapter`;
- selected-runtime execution through an injected executor;
- tool-call budgeting and trace events;
- canonical result construction;
- explicit separation of lifecycle status from evidence provenance.

`runtime-selection.v1` remains declarative. Selection does not execute a model and does not invent measurements. A trusted adapter is the only component that translates an authorised selection into an executable runtime specification.

The A01 path follows the same boundary:

```text
selection output
      ↓
runtime_gate
      ↓
run_a01_selected.py
      ↓
A01 runtime adapter
      ↓
existing agentic runner contracts
      ↓
trusted runtime command
      ↓
A01 grader + measurement
```

A convenience script is not a competing runner merely because it is executable from the shell. It is a bridge when it delegates to the canonical execution components.

## Evidence rule

A result must preserve enough technical information to be understood and reproduced. Third-party benchmark numbers are useful for research but are not official LEONES measurements.

Evidence provenance is separate from result status:

```text
estimated / reported / measured
                 │
                 ▼
        explicit validation
                 │
                 ▼
             verified
```

The runner may emit `measured` only when actual runtime execution evidence exists. It must never promote evidence to `verified` automatically; independent verification remains a separate operation.

For physical runtime benchmarks, the measurement protocol freezes the workload, runtime, model artifact, hardware, execution parameters, repetition count, provenance and acceptance rules. Failed runs remain evidence of failure and are not silently discarded.

## Hardware-aware model preselection

`llmfit` occupies the first decision layer after hardware identification. It is a **preselector**, not a source of truth:

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

Its estimates must remain distinct from measured LEONES performance. External ODS/Magnitude and other benchmark sources follow the same provenance rule.

## Inference and agentic evaluation

Inference measures the model/backend/hardware combination. It must not be confused with agentic task performance. Relevant concepts include model identity, quantisation, artifact identity, runtime/version, prompt evaluation speed, generation speed, memory, total time and errors.

LOTB measures whether an agent can complete defined tasks. A fast model is not automatically a good agent; task completion and success therefore remain first-class results alongside tok/s.

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

## MANADA

**MANADA** is the contribution protocol for real-world measurements and community observations.

```text
hardware → model → inference → LOTB → report.md → validation → GitHub
```

The report identifies the experiment, not the person. Never publish names, emails, personal usernames, identifiable hostnames, serial numbers, UUIDs, MAC/IP addresses, exact location, personal paths, credentials or tokens.

## Discovery and recommendations

Discovery is deliberately separate from acceptance:

```text
discover → inspect → classify → test → recommend → incorporate
```

Finding a project does not mean that LEONES endorses it.

## External knowledge sources

The principal documented sources include FreeToken, LLMFit, AirLLM, ODS, Magnitude and local runtimes. These sources are knowledge/discovery inputs. Their claims remain separated from LEONES measurements under the four-layer knowledge contract:

```text
source → evidence → estimate → LEONES measurement
```

ODS and Magnitude are external deployment/agent profiles, not internal truth sources. Their native benchmark paths remain distinct from LEONES physical measurements unless their output is explicitly imported with provenance.

## Automation

GitHub Actions may validate contracts, run deterministic tests, perform scheduled discovery, aggregate public results and prepare reports. CI must not pretend its runner hardware is the user's target machine, bypass privacy checks or turn unverified information into official results.

## Design rules for scripts

Every script should answer one question and document:

1. what it does;
2. what it does not do;
3. inputs;
4. outputs;
5. dependencies;
6. examples;
7. exit/error behaviour;
8. related scripts.

Prefer composition over duplication. If a script needs execution capability, reuse the canonical runner/adapter boundary instead of copying it.

## Documentation navigation

```text
README.md
   ↓
docs/README.md
   ↓
subsystem README
   ↓
phase / integration / source contract
   ↓
validation
   ↓
completed guide / code / workflow
```

See `DOCUMENTATION_PROTOCOL.md` for the mandatory closure rule.

## Vocabulary

- **LEONES** — Local Ecosystem of Open Neural Expert Systems.
- **Buddy** — central candidate knowledge/context layer.
- **llmfit** — hardware-aware external preselector for the first model estimate.
- **LOTB** — agentic task battery.
- **MANADA** — protocol for anonymised real-machine reports and community observations.
- **CABE** — project vocabulary for whether a configuration fits.
- **RULA** — project vocabulary for whether a configuration runs usefully.
