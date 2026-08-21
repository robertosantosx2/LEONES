# LLMFit → recommendation candidates → runtime → benchmark → evidence

This is the executable first stage of LEONES model selection.

```text
hardware
   ↓
llmfit recommend --json
   ↓
llmfit adapter
   ↓
leones.recommendation-candidates.v1
   ↓
select candidate
   ↓
installed + available runtime
   ↓
physical runtime execution
   ↓
leones.runtime-benchmark.v1
   ↓
evidence promotion
   ↓
Atlas / Router / LOTB
```

## Evidence boundary

LLMFit is a **preselector**, not a source of measured truth. `score`, `fit_level`,
`estimated_tps`, memory figures and runtime choice remain `estimated` until LEONES
executes a matching physical generation.

The evidence promoter in `automation/evidence/runtime_benchmark.py` preserves the
LLMFit estimate as provenance and only emits `measured` when the benchmark result
itself reports a real generation with tokens, elapsed generation time and runtime/model
identity. `not_run` and `no_matching_result` remain `unknown`; execution failure is
recorded as `failed`.

## Canonical benchmark evidence

The schema is `schemas/runtime-benchmark-evidence-v1.json` and uses the canonical
`leones.runtime-benchmark.v1` envelope. A measured result records at least:

- model;
- runtime;
- observation time;
- generated tokens;
- generation seconds;
- tokens/second;
- measurement scope;
- hardware fingerprint;
- quantization where available;
- provenance back to the LLMFit estimate.

## Runtime paths

The bridge currently supports the LLMFit local runtime identifiers and an optional
AirLLM runner. AirLLM is capability-gated by actual `airllm` and `torch` imports and
is measured through a real `AutoModel` generation. It is not selected merely because
another backend cannot run a model.

## Execution

```bash
python3 automation/discovery/llmfit_adapter.py --use-case coding --select
python3 scripts/leones_runtime_benchmark.py --use-case coding --output artifacts/runtime-benchmark.json
python3 automation/evidence/runtime_benchmark.py \
  artifacts/runtime-benchmark.json \
  --output artifacts/runtime-benchmark-evidence.json
```

The final artifact can therefore enter the evidence/Atlas pipeline without losing
the distinction between estimation and measurement.

## Reproducibility

Preserve LLMFit version, hardware envelope/fingerprint, model identifier,
quantization, selected runtime, context, estimate basis, benchmark provider/result,
timestamps and failure state. A failed benchmark is evidence of an execution failure,
not evidence that the model is intrinsically good or bad.
