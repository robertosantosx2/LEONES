# LEONES Reference Harness Router

## Purpose

Define the common contract that connects model selection, evidence, local runtimes and agent harnesses without making any upstream project a mandatory LEONES dependency.

## Decision pipeline

```text
USER INTENT + HARDWARE
        |
        v
   llmfit estimate
        |
        v
 Atlas identity/evidence
        |
        +-- JGB / openness
        +-- hardware fit
        +-- measured performance
        +-- CABE / RULA
        |
        v
 candidate plan
        |
        +--------------+--------------+
        v                             v
    ODS runtime            Magnitude runtime/profile
        |                             |
        +--------------+--------------+
                       v
               Harness selection
                 |      |      |
               Buddy   DSH   future
                 |      |      |
                 +------+------+ 
                        v
                  LOTB / task run
                        v
              inference + agent metrics
                        v
                   LEONES result
```

## Roles

| Layer | Responsibility | Upstream status |
|---|---|---|
| llmfit | first hardware/model estimate | external preselector |
| Atlas | identity and evidence boundary | canonical LEONES data |
| CABE/RULA | fit/run classification | canonical LEONES classification |
| Magnitude | hardware profiling and runtime selection support | reference integration |
| ODS | local AI server/runtime surface | reference integration |
| Buddy | knowledge/context and agent harness candidate | reference harness |
| DeepSeek Harness | agent harness candidate | reference harness |
| LOTB | reproducible agentic evaluation | canonical LEONES evaluation |

## Hard separation rules

1. `llmfit` output is an estimate, never a LEONES measurement.
2. Third-party benchmark data remains external evidence.
3. CABE/RULA never replaces `tokens_per_second`; both are retained.
4. ODS/Magnitude/Buddy/DeepSeek Harness must be replaceable through adapters.
5. Runtime adapters report backend, version/commit, model, quantisation, hardware and errors.
6. Harness adapters report task, tools, trajectory, outcome, time, cost where available, safety events and artefacts.
7. Failed runs are results too; they are not silently discarded.
8. No adapter publishes directly to canonical Atlas without the validation gate.
9. Privacy rules apply before any result leaves the local machine.

## Canonical adapter interface

Conceptually every integration implements:

```text
probe() -> capabilities
prepare(plan) -> prepared_run
run(task, prepared_run) -> raw_result
normalize(raw_result) -> leones_result
cleanup(prepared_run)
```

`probe()` is read-only. `prepare()` may download/configure resources. `run()` performs the experiment. `normalize()` maps upstream output into the LEONES result schema. `cleanup()` leaves no credentials or temporary private data in published artefacts.

## Selection policy

The router ranks candidates in this order:

1. hard constraints: OS, memory, accelerator, context and required tools;
2. evidence validity and model identity;
3. task suitability;
4. openness/JGB policy;
5. expected fit from llmfit;
6. observed LEONES performance;
7. CABE/RULA classification;
8. runtime/harness compatibility;
9. user priorities such as latency, quality, cost or privacy.

An estimate narrows the search space, but observed results outrank estimates for the same configuration.

## Initial implementation scope

Do not copy upstream source. Add thin LEONES adapters and contract tests:

- `leones/adapters/llmfit.py`
- `leones/adapters/magnitude.py`
- `leones/adapters/ods.py`
- `leones/adapters/buddy.py`
- `leones/adapters/deepseek_harness.py`
- `leones/router.py`

Adapters degrade cleanly when an optional upstream component is absent.

## Acceptance gates

### G1 — static contract

All adapters expose the same lifecycle and produce schema-valid normalized results.

### G2 — offline integration

Mock upstream responses normalize deterministically. No network or model download is required.

### G3 — local smoke

A real installed runtime can be probed and execute one minimal inference/task where hardware permits.

### G4 — reproducibility

The result records exact upstream version/commit, model revision, runtime and hardware profile.

### G5 — privacy

Tests reject publication when forbidden host/user identifiers, paths, addresses, credentials or tokens occur.

### G6 — empirical validation

Real runs are compared against the initial estimate and the delta is retained as evidence rather than silently overwriting the estimate.

## Upgrade policy

Submodule pins change only after adapter contract, offline tests and relevant smoke tests pass. Upstream changes must not silently alter the LEONES result schema.
