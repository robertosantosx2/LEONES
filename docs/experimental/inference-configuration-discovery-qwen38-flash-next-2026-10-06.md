# Inference Configuration Discovery: Qwen3.8-Flash-Next and LEONES+ODS Evolution

**Date:** 2026-10-06  
**Status:** Experimental / architectural proposal  
**Scope:** LEONES + ODS local and hybrid inference selection

## Executive conclusion

Qwen3.8-Flash-Next provides a concrete example of a broader architectural fact: model capability on user hardware is not determined only by model size, quantization, or whether weights fit. It is also determined by the inference runtime and its configuration.

Reported external results such as approximately **25 → 50+ tok/s** for Qwen3.8-Flash-Next, **40 → 100 tok/s** for Qwen3.6-35B Q8, and **40 → 80 tok/s** for Qwen3.8-27B are retained as external experimental evidence, not universal guarantees.

## Inference Configuration Discovery (ICD)

**Inference Configuration Discovery** is the process of discovering, testing and selecting the best reproducible inference configuration for a given combination of hardware, model artifact and workload.

The search space may include:

- model and immutable artifact;
- quantization;
- inference runtime and revision;
- backend and kernels;
- KV-cache format and policy;
- context length;
- GPU/CPU/RAM/SSD offload;
- speculative decoding;
- MTP / Multi-Token Prediction;
- draft configuration;
- batch and parallelism;
- model-specific acceleration features.

The objective changes from:

> Can this model run?

to:

> **Which reproducible inference configuration extracts the best useful, measured capability from this hardware for this workload?**

## Qwen3.8-Flash-Next as a case study

Qwen3.8-Flash-Next demonstrates why a model entry cannot be reduced to a static VRAM requirement. Candidate execution features include MTP-assisted speculative decoding, KV-cache choices, MoE execution/offload and model-specific memory strategies.

The reported `--spec-draft-n-max 4` is therefore a **candidate configuration**, not a universal ODS default. ODS should be able to compare candidate values and retain the best measured result for the detected hardware/workload.

## Architectural evolution

ODS should evolve from:

```
hardware → model fit → runtime → execution
```

to:

```
hardware profile
      ↓
model candidates
      ↓
runtime capability registry
      ↓
inference configuration candidates
      ↓
Inference Configuration Discovery
      ↓
measured benchmark
      ↓
evidence
      ↓
best real configuration
      ↓
ODS execution
```

The measured unit becomes:

```
model artifact
 + runtime + revision
 + configuration
 + hardware
 + workload
        ↓
measured capability
```

## Runtime-aware model selection

The same model and hardware can produce materially different results depending on runtime and configuration. ODS must therefore avoid interpreting the first successful runtime as the intrinsic capability of the hardware/model.

Candidate runtimes should be evaluated independently, including upstream `llama.cpp`, specialized derivatives such as `cafe-llama.cpp`, TensorFold where applicable, and future runtimes discovered by ODS.

## LEONES evidence rule

ICD does not replace the existing runtime evidence contract. It sits above it.

Discovery generates candidate configurations. The benchmark layer is the authoritative producer of measured performance evidence.

Therefore:

- estimates remain estimates;
- external reports remain external evidence;
- measured local results require reproducible provenance;
- changing runtime, artifact, configuration or hardware creates a distinct experimental condition;
- a reported 2× improvement must never be silently transferred to another configuration.

## Proposed ICD record

A future ICD record should represent at least:

```yaml
model:
  id:
  revision:
  artifact_sha256:
  quantization:

runtime:
  name:
  version:
  commit:
  backend:

configuration:
  context:
  kv_cache:
  gpu_offload:
  cpu_offload:
  ram_offload:
  ssd_offload:
  speculative:
  mtp:
  spec_draft_n_max:
  batch:
  parallel:

hardware:
  cpu:
  ram:
  gpu:
  vram:
  driver:

workload:
  protocol:
  prompt:
  output_tokens:

result:
  tok_s:
  ttft:
  total_time:
  vram:
  ram:
  acceptance_rate:

evidence:
  execution_id:
  timestamp_utc:
  provenance:
```

## Connection with Edge0 + FATE + HOBBIT + HybriMoE

ICD strengthens the intended LEONES+ODS architecture:

```
DISCOVERY
   ↓
PROFILE
   ↓
MODEL / RUNTIME CANDIDATES
   ↓
Inference Configuration Discovery
   ↓
PREFETCH / CACHE
   ↓
BENCHMARK
   ↓
MEASURED EVIDENCE
   ↓
CHOICE
   ↓
CONSENT
   ↓
INSTALL / EXECUTE
```

Runtime optimization becomes part of capability discovery rather than an implementation detail hidden after model selection.

## Architectural principle adopted

> **LEONES must discover the best measured inference configuration, not merely the largest model that fits the hardware.**

This is also relevant to hybrid inference: a newly discovered local configuration can change a workload's optimal local/hybrid/cloud placement.

## Experimental status

The Qwen3.8-Flash-Next speedup reports motivate ICD but are not LEONES benchmark results. The next validation step is controlled reproduction with complete runtime, configuration, hardware, workload and provenance recorded through the existing runtime benchmark evidence contract.

## Implementation targets

1. Extend `runtime-selection.v1.1` with configuration capability descriptors.
2. Add an ICD candidate-generation layer before runtime execution.
3. Keep runtime commands inside trusted adapters.
4. Run candidate configurations through `runtime-benchmark-evidence.v1.1`.
5. Store measured configuration results as distinct evidence records.
6. Let ODS rank model + runtime + configuration combinations.
7. Feed measured results back into selection without treating them as universal guarantees.
