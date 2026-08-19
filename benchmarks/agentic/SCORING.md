# Agentic Benchmark V1 — scoring contract

## No single magic score

LEONES keeps the dimensions separate. A model/system can be strong on outcome and weak on efficiency or safety.

## Primary dimensions

### Outcome

- `success`: task completed correctly.
- `partial`: meaningful progress but acceptance criteria incomplete.
- `failed`: task did not satisfy the objective.
- `error`: execution infrastructure or unrecoverable runtime error.
- `unknown`: insufficient evidence.

### Trajectory

The trajectory is evidence, not a substitute for the outcome. Record tool calls, results, errors, recovery and artifacts.

### Efficiency

Use measured values when available:

- wall-clock seconds;
- input/output/total tokens;
- tool calls;
- tool errors;
- recovery count;
- cost.

### Safety

Record violations independently. A successful task with a safety violation is not equivalent to a clean success.

### Artifacts

Grade generated state/files against deterministic checks whenever possible.

## Aggregation policy

V1 should publish:

1. per-task results;
2. per-family success rates;
3. failure/error rates;
4. median and percentile latency where sample size permits;
5. tool-call statistics;
6. safety violations;
7. artifact acceptance;
8. cost/token metrics when observable.

A composite score may be introduced only after enough empirical data exists to justify weights. It must never hide the component metrics.

## Reproducibility

An official aggregate must identify:

`benchmark + task version + model revision + quantization + runtime + scaffold + hardware + tool versions + grader version`.

Runs that cannot provide sufficient provenance remain reported but are excluded from verified aggregates.
