# A01 + final model/runtime selection

The selector now exposes a frozen execution envelope: `leones.runtime-selection.v1`.

The executor/grader boundary must consume this envelope instead of independently choosing a model or runtime.

```text
A01 task
  ↓
LLMFit candidates
  ↓
final_selector.select()
  ↓
selection_envelope.build_selection_envelope()
  ↓
leones.runtime-selection.v1
  ↓
executor
  ↓
grader
  ↓
benchmark/evidence
```

## Invariant

The envelope records both `estimated_tps` and `measured_tps`. The selection reason is explicit:

- `measured-runtime-evidence`: a physical measurement influenced selection;
- `llmfit-estimate-fallback`: no measured runtime evidence was available.

An executor must not silently re-rank or replace the selected model/runtime. If execution cannot use the selected runtime, it should return a structured failure so the Router can learn from the failure rather than silently switching models.

## Current repository boundary

The model/runtime selector and its contracts are present on `feat/llmfit-runtime-benchmark`. A repository-wide search did not expose an A01 executor/grader implementation under the expected names, so this change deliberately stops at the contract boundary rather than inventing an integration point that has not been located.

The next integration step is therefore to identify the actual A01 executor entry point and make it consume `leones.runtime-selection.v1`.
