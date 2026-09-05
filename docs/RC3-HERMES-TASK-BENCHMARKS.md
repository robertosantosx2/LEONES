# LEONES RC3 — Hermes selection + task benchmark loop

**Decision:** 5 September 2026

## Canonical flow

```text
hardware_profile.py
      ↓
hardware-profile.v1
      ↓
LEONES candidate-set.v1
      ↓
HERMES selects exactly one candidate
      ↓
user selects Magnitude / ODS / BOTH
      ↓
trusted handoff plan(s)
      ↓
selected stack prepares the model
      ↓
LEONES verifies the real endpoint
      ↓
10 canonical LEONES tasks
      ↓
MEASURED result per task
      ↓
comparison / recommendation
```

### What changed

- **LLMFit/FitLLM is removed from the RC3 implementation tree.** It is not a dependency and is not called by the selector.
- **Hermes is the model-selection agent.** LEONES gives Hermes only the already-normalized candidate set. Hermes cannot introduce a model outside that set.
- Hermes returns `selected_model_id`, rationale and confidence. LEONES validates the returned id and keeps execution/measurement authorization false.
- The user can choose **Magnitude**, **ODS**, or **both**. When both are selected, LEONES creates two independent declarative handoff plans for the same selected model.
- Neither handoff adapter downloads, starts, or benchmarks anything by itself. Physical execution remains behind the existing consent/execution gate.

## Hermes installation

LEONES does not vendor Hermes. `scripts/install_hermes.sh` calls the upstream installer only when the operator explicitly sets `LEONES_ALLOW_NETWORK_INSTALL=1`.

Upstream documents Linux installation with:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Then:

```bash
hermes --version
hermes doctor
```

Hermes exposes `hermes model` for provider/model setup and `hermes -z` for a clean one-shot programmatic response. RC3 uses the latter so the selector can capture structured JSON without parsing the interactive TUI.

## Stack handoff

The handoff layer is declarative:

```python
from runtime_selection.handoff import build_handoffs

plans = build_handoffs(selection)
```

The selected stack(s) are represented as `magnitude.v1.1` and/or `ods.v1.1` plans. The existing adapters remain the only place where a plan can become an execution specification.

Magnitude is used for its native profiling/tuning/inference path. ODS is used for its local-stack/llama-server path. LEONES does not replace either project's native model-management machinery.

## Benchmark by task

The canonical task catalogue is `benchmarks/agentic/tasks.yaml` and currently contains ten tasks: tool use, multi-step execution, artifacts, recovery, long-horizon state, research/evidence reconciliation, coding, local operations, safety, and cost/latency budget.

`scripts/leones_task_benchmark.py` runs the same task suite against an OpenAI-compatible endpoint and produces one result row per task with:

- task id and family;
- successful runs;
- mean latency;
- measured output tokens/s when the endpoint reports completion-token usage;
- evidence type.

The output is `artifacts/task-benchmark-latest.json` by default. This is the measurement layer; provider/catalog speed estimates are never copied into `measured` fields.

## Repeat with another Hermes-selected model

A repeat is intentionally a new selection + measurement cycle. Run:

```bash
python scripts/leones_task_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --decision-json path/to/decision.json \
  --select-with-hermes
```

The command asks Hermes for a fresh candidate choice and then executes the complete ten-task suite against the selected endpoint.

To benchmark a known candidate without reselection:

```bash
python scripts/leones_task_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --model <candidate-id>
```

This makes model A vs model B comparisons reproducible while preserving the distinction between **Hermes selection**, **user stack choice**, and **LEONES measurement**.

## Result presentation

The CLI prints a compact table by task and stores the complete JSON. A future web surface can consume the same `leones-task-benchmark.v1` artifact without inventing a second benchmark format.

The final recommendation is computed only after task-level measurements exist. Until then, model quality, fit and external benchmarks remain decision evidence rather than LEONES measurements.
