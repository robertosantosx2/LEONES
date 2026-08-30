# JALÓN 4 — Artificial Analysis methodology lock

**Status:** frozen design clarification; no physical execution.

## Purpose

This document locks the part of JALÓN 4 that must be exact before Ubuntu: LEONES may borrow **methodological principles** from Artificial Analysis, but it must not reproduce, rename or imply ownership of Artificial Analysis's private benchmark datasets or headline scores.

The current Artificial Analysis Coding Agent Index evaluates end-to-end software-engineering work and keeps outcome and efficiency views tied to the same task-level benchmark coverage. Its current public suite uses three benchmark families: long-horizon software engineering, terminal use, and repository Q&A. Each task is evaluated with three attempts, task-level pass@1 is calculated before aggregation, and the component benchmarks are equally weighted in the public index. Artificial Analysis also explicitly treats reward hacking as a zero outcome for affected attempts in Terminal-Bench v2.1.

## LEONES adoption rules

### 1. User intent selects the benchmark profile

The benchmark is selected from the user's declared work, not from the hardware tier:

| User intent | Mandatory task families | Optional task families |
|---|---|---|
| `chat` | knowledge, reasoning, transformation | artifact |
| `coding` | coding, terminal, repository Q&A | long-horizon agent |
| `reasoning` | reasoning, knowledge | coding |
| `agent` | terminal, long-horizon agent, artifact | coding, multimodal |
| `server` | knowledge, coding, terminal/tool use | concurrency |
| `multimodal` | multimodal, knowledge, artifact | reasoning |
| `custom` | exactly the user-declared families | user-declared |

No hardware tier is allowed to select a task family.

### 2. Audit repetition

For an audit comparison, the default is **3 independent attempts per task** when the selected harness supports repeatable execution.

A task's reported `pass@1` is the mean of its first-attempt outcomes across the configured attempts, preserving the Artificial Analysis distinction between task-level aggregation and pooled attempts.

If physical cost or time makes three attempts impossible, the plan must explicitly record the reduced attempt count and must not present the result as directly comparable to a three-attempt Artificial Analysis evaluation.

### 3. Equal task weight

Within a benchmark family, each task has equal weight. We do not pool raw attempts and divide by the total number of attempts when task attempt counts differ.

For a family:

```text
family_pass_at_1 = mean(task_pass_at_1 for every task in the family)
```

A LEONES recommendation may report several families separately. If a composite is eventually required, its family weights must be declared before audit and frozen with the benchmark plan.

### 4. Outcome first

A task is successful only when the required final state or artifact satisfies its verifier/rubric.

Generation throughput is not task success. A fast model that does not complete the user's required work is not the preferred system for that intent.

### 5. Efficiency stays paired with outcome

For every audited configuration, retain at least:

- task completion / pass@1;
- end-to-end task time;
- agent wall time when available;
- input/output/reasoning/total tokens when available;
- retries/recoveries;
- errors;
- inference metrics from `runtime-benchmark-evidence.v1.1`.

Missing telemetry is recorded as missing, not zero.

### 6. Reward-hacking / verifier integrity

A passing verifier is not sufficient if the trajectory shows manipulation of the grading mechanism or retrieval of the task's reference answer where that retrieval is prohibited.

LEONES therefore treats the following as invalid for audit scoring when the task rules prohibit them:

- modifying tests or verifier state to force a pass;
- writing the expected answer directly into the grading output;
- copying a bundled reference solution;
- retrieving a graded answer/reference solution externally;
- reporting a result that the agent did not actually compute.

The invalid attempt remains in the evidence set and is scored as a non-success according to the frozen task contract.

## Separation of sources

The following are never merged into one number:

```text
LLMFit estimated fit/speed
ODS native tier/catalog recommendation
Magnitude hardware profile/recommendation
LEONES physical runtime measurement
LEONES task-completion outcome
```

External estimates remain `estimated` or `recommended`. Only the physical LEONES execution can produce `measured` local performance.

## No Artificial Analysis score clone

LEONES must not publish an `Artificial Analysis score` or imply that a local LEONES composite is the Artificial Analysis Index.

The safe formulation is:

> **LEONES task-completion result, using Artificial Analysis-aligned methodology.**

The benchmark definition, task IDs, attempts, verifiers, versions, hardware, runtime and evidence remain LEONES-owned and auditable.

## Closure condition

JALÓN 4 is design-closed when:

1. the user-intent → task-family mapping is frozen;
2. audit repetition is explicit;
3. task-level aggregation is explicit;
4. outcome/efficiency/inference metrics are separated;
5. verifier/reward-hacking rules are explicit;
6. LLMFit/ODS/Magnitude remain source authorities rather than inputs to a new LEONES selector;
7. no physical result is claimed before Ubuntu execution.

**Next physical boundary:** `AHORA NECESITO UBUNTU`.
