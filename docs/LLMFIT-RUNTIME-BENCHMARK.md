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
provider-specific benchmark
   ├─ llmfit bench --json
   └─ AirLLM local runner
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
basis. The adapter accepts both those current fields and older shapes already
present in LEONES.

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

## Runtime boundary

The adapter recognizes `llamacpp`, `mlx`, `vllm` and the optional `airllm`
runtime. AirLLM is capability-gated by actual imports of both `airllm` and
`torch`; merely having a model that Transformers can describe does not make
AirLLM available.

AirLLM is intentionally a runtime fallback/experimental path rather than a
new source of model recommendations. Its benchmark uses
`AutoModel.from_pretrained(...)`, tokenization and generation, and records a
physical local generation. The first run may download and create layer-wise
shards, so disk and I/O are part of the measured runtime cost.

See `docs/RUNTIME-AIRLLM.md` for the runtime-specific boundary and limitations.

## First automatic benchmark

Run locally on the target machine:

```bash
python3 -m unittest tests/test_llmfit_adapter.py
python3 automation/discovery/llmfit_adapter.py --use-case coding --select
python3 scripts/leones_runtime_benchmark.py --use-case coding --output artifacts/runtime-benchmark.json
```

For a direct AirLLM physical smoke benchmark:

```bash
python3 scripts/leones_airllm_benchmark.py <huggingface-model-id>
```

The normal benchmark runner only selects a candidate that is both installed
and backed by an available runtime. A successful AirLLM run is marked `measured`
only after the selected model actually generates tokens. A failed load or
missing dependency remains an execution failure and is never promoted.

## Evidence boundary

The successful benchmark must preserve the runtime/model/quantization/hardware
tuple before it can feed the Router or LOTB. A single-generation AirLLM run is
**performance evidence**, not a model-quality benchmark; quality promotion
still requires the normal LEONES evidence gates.

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
