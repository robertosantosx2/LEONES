# JALÓN 4 — Task Completion Benchmark Suite

## Scope

This is the execution plan for the **deep benchmark** that follows model/hardware/runtime selection. It is intentionally an outcome benchmark, not another tokens-per-second leaderboard.

The methodology is aligned with the current Artificial Analysis approach to agent/coding evaluation: end-to-end tasks, objective resolution where possible, `pass@1`, and paired efficiency metrics. It is not presented as a reproduction of Artificial Analysis's private benchmark datasets or score.

## Selection-driven profiles

| User selection | Required families | Optional families |
|---|---|---|
| `chat` | knowledge, reasoning, transformation | artifact |
| `coding` | coding, terminal, repository Q&A | long-horizon |
| `reasoning` | reasoning, knowledge | coding |
| `agent` | terminal, long-horizon, artifact | coding, multimodal |
| `server` | knowledge, coding, tool/terminal | concurrency |
| `multimodal` | multimodal, knowledge, artifact | reasoning |
| `custom` | user-declared families | user-declared |

The suite is therefore **selected by the user's intended work**, not by the hardware tier.

## Three execution levels

### Level 1 — Smoke

Purpose: confirm that the selected system can perform the task family.

- 3–5 tasks/family
- 1 attempt/task
- fixed timeout
- objective verifier where possible

### Level 2 — Development

Purpose: compare candidate models/runtimes before freezing the audit suite.

- 10–30 tasks/family
- repeat selected hard cases
- collect performance + outcome telemetry
- may evolve during development

### Level 3 — Audit

Purpose: immutable recommendation evidence.

- frozen task IDs/version
- frozen fixtures
- frozen prompts/scaffolds
- no inspection of hidden labels
- `pass@1` as primary task success measure
- all attempts retained, including failures
- task set is never optimized after seeing audit results

## Task families

### Knowledge

Answer a bounded question from supplied facts or a controlled corpus.

Success should be machine-checkable where possible; otherwise use a fixed rubric and judge version.

### Reasoning

Require a determinate answer or structured result. Prefer problems with an objective verifier over subjective grading.

### Coding

Repository-level change with tests or another deterministic acceptance check. Record the resulting patch/artifact and verifier output.

### Terminal

A real shell task with a known final state. The verifier checks filesystem state, command output, tests, or another objective property.

### Long-horizon agent

Multi-step task requiring planning, tools and recovery. The task ends only when the required artifact/state exists and passes verification.

### Artifact

Create a document, spreadsheet, slide deck, report, data file or other requested artifact. Validate structure and required content programmatically when feasible.

### Multimodal

Only enabled when the selected runtime/model path actually supports the input modality. Store source media hash and task version, not private user media.

## Task result contract

Every task attempt produces:

```text
attempt_id
execution_id
task_id
task_version
model_revision
runtime_version
hardware_fingerprint
started_at
finished_at
status = pass | fail | invalid | blocked
verifier_status
verifier_version
turns
input_tokens (if available)
output_tokens (if available)
reasoning_tokens (if available)
peak_memory_mb (if available)
error_class (if any)
artifact_refs
stdout_ref / stderr_ref (sanitized)
```

No secrets, API keys, private prompts or arbitrary user files are stored in public evidence.

## Primary metrics

### Outcome

`pass@1 = successful first attempt / valid first attempts`

For a single deterministic local run, this is simply pass/fail. Repeats are reported separately and must not be silently collapsed into a higher score.

### Efficiency

- end-to-end task time;
- agent wall time where available;
- input/output/reasoning/total tokens;
- retries/recoveries;
- peak memory;
- errors.

### Inference performance

From the existing runtime benchmark contract:

- TTFT;
- time to first answer token when applicable;
- output tok/s;
- TPOT;
- p50/p95/p99 when sample count supports it;
- context;
- concurrency.

## Recommendation rule

LEONES must not select a winner from a single number.

The recommendation is a **task-conditional result**:

```text
user intent
+ selected model/configuration
+ LLMFit fit state
+ ODS/Magnitude native selection/configuration
+ measured task success
+ measured performance
+ efficiency
+ limitations
```

A model that is faster but fails the user's critical task is not the recommended system for that intent.

## Integrity rules

- Development and audit suites are distinct.
- Audit task definitions are frozen before final measurement.
- Model/runtime/configuration changes create a new execution identity.
- Failed and invalid runs are preserved and explained.
- No benchmark result is copied from ODS, Magnitude, LLMFit, Artificial Analysis or another source and labeled `measured` by LEONES.
- External benchmark scores are contextual evidence only.
- Local measured evidence is tied to an exact hardware/model/runtime/configuration identity.

## Execution gate

The suite is fully designed but deliberately **not executed** in this phase.

Physical execution requires the user's explicit signal:

> **AHORA NECESITO UBUNTU**
