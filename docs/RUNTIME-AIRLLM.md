# AirLLM runtime in LEONES

AirLLM is an **optional runtime path**, not a replacement for LLMFit.

## Role

```text
LLMFit estimate
   ↓
recommendation candidate
   ↓
capability gate: python + torch + airllm
   ↓
AirLLM AutoModel.from_pretrained(model_id)
   ↓
real local generation
   ↓
leones.runtime-benchmark.v1
```

The upstream AirLLM API exposes `AutoModel.from_pretrained(...)`, tokenization
and `generate(...)`. The first run may download and split the model into
layer-wise shards, so disk capacity and I/O are part of the runtime cost.

LEONES therefore records AirLLM as available only when both `airllm` and
`torch` can actually be imported. Availability is not treated as evidence of
performance.

## Benchmark

```bash
python3 scripts/leones_airllm_benchmark.py Qwen/Qwen3-8B
```

Or let the normal runtime bridge select an installed AirLLM candidate:

```bash
python3 scripts/leones_runtime_benchmark.py --use-case coding
```

The benchmark reports generation time, generated token count, tokens/second,
model-load time and environment information. It is deliberately labelled as
a **single local generation**, not a model-quality benchmark.

## Constraints

AirLLM must remain opt-in/capability-gated. It should not be selected merely
because a model is too large for another backend. A runtime candidate must
still pass the normal LEONES fit, installation and evidence gates.

CPU-only support must not be inferred from generic Transformers compatibility;
where AirLLM's environment does not provide a supported execution path, the
candidate remains unavailable and another runtime is tried.
