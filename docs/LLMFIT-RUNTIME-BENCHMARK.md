# LLMFit → recommendation candidates → runtime → benchmark

This is the executable first stage of LEONES model selection.

## Contract

```text
hardware
   ↓
llmfit recommend --json
   ↓
automation/discovery/llmfit_adapter.py
   ↓
leones.recommendation-candidates.v1
   ↓
select candidate
   ↓
installed + available runtime
   ↓
llmfit bench --json --provider …
   ↓
leones.runtime-benchmark.v1
   ↓
Router / evidence / LOTB
```

LLMFit is explicitly a **preselector**, not a source of truth. Its `score`,
`fit_level`, `estimated_tps`, memory figures and runtime choice remain
`estimated` until LEONES executes a real measurement. This follows the project
architecture: LLMFit reduces the candidate space, then LEONES applies identity,
evidence, task suitability and measured performance.

## Why this adapter is the boundary

Current LLMFit exposes machine-readable recommendation JSON with fields such as
`score`, score components, fit level, run mode, best quantization, estimated TPS,
memory requirements, runtime, installed state, usable context and an estimate
basis. Its REST/CLI documentation also defines `fit_level`, `run_mode` and
`runtime` as stable machine codes. The adapter accepts both those current fields
and the older shapes already present in LEONES.

The canonical normalized object is:

- `schema_version = leones.recommendation-candidates.v1`;
- `source = llmfit`;
- `evidence_status = estimated`;
- `model_id`;
- `fit_level`;
- `best_quant`;
- `estimated_tps`;
- memory/context fields;
- `runtime` and `runtime_available`;
- `installed`;
- `ollama_name` / `verify_command` when supplied by LLMFit;
- original `raw` candidate for provenance.

Unknown LLMFit fields are retained rather than silently discarded.

## Selection gate

The executable selector defaults to:

1. reject `too_tight`;
2. require at least `good` fit;
3. optionally require the model to be installed;
4. optionally require a locally available runtime;
5. prefer candidates whose estimated TPS meets the LEONES 10 tok/s usability
   reference;
6. break ties with fit level, composite score and estimated TPS.

This is deliberately conservative. A high score does not override an inability
to execute the model.

## First automatic benchmark

Run locally on the target machine:

```bash
python3 -m unittest tests/test_llmfit_adapter.py
python3 automation/discovery/llmfit_adapter.py --use-case coding --select
python3 scripts/leones_runtime_benchmark.py --use-case coding --output artifacts/runtime-benchmark.json
```

The benchmark runner only selects a candidate that is both installed and backed
by an available runtime. It then delegates to LLMFit's provider-aware benchmark
command. If no matching measured result is returned, the output remains
`unknown`; it is never promoted to `measured`.

## Runtime boundary

The adapter currently recognizes the runtime identifiers used by LLMFit for
local inference (`llamacpp`, `mlx`, and the API's `vllm` override). Availability
is checked locally before selection. This is intentionally a capability check,
not an assertion that the runtime has successfully loaded the model.

The successful benchmark is the next evidence boundary. The runtime/model/
quantization/hardware tuple must be preserved with the benchmark result before
it can feed the Router or LOTB.

## Reproducibility

For every candidate LEONES should preserve:

- LLMFit version;
- hardware envelope;
- model identifier;
- quantization;
- selected runtime;
- context used for estimation;
- estimate basis;
- benchmark provider and result;
- timestamps;
- failure state when execution fails.

A failed benchmark is evidence of failure, not evidence that the model is good
or bad in general.
