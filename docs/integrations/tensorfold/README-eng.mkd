# TensorFold Integration Proposal for ODS

**Experimental track:** `ods-evolution`  
**Project:** LEONES  
**Date:** 2026-10-01  
**Status:** Architecture and integration study — no production integration

## 1. Executive summary

TensorFold is a specialized local inference runtime built around family-specific execution engines, low-resident-memory model streaming, speculative decoding, and exactness checks against serial decoding on the same engine.

The project has progressed significantly beyond the initial MLX-only/early-CUDA prototype. Its current documentation describes:

- MLX execution on Apple Silicon;
- CUDA execution on supported NVIDIA configurations;
- layer/tensor-aware streaming from standard model shards;
- OpenAI-compatible serving;
- family-specific CUDA engines;
- speculative decoding with MTP and DFlash-style drafters;
- byte-exact verification against serial decoding on the same engine;
- model-specific 4-bit checkpoints and requirements;
- one- and two-rank CUDA execution for selected families.

The appropriate ODS role is still:

> **optional specialized runtime for model families and hardware combinations where TensorFold has a supported execution path.**

It should complement rather than replace `llama-server`.

## 2. Current TensorFold architecture

TensorFold's current design starts with a memory-virtualization layer:

```text
.safetensors shards
       ↓
TensorFold manifest
       ↓
layer / tensor index
       ↓
mmap-backed access
       ↓
memory-budget streaming
       ↓
family-specific inference engine
       ↓
OpenAI-compatible server
```

The project explicitly describes the runtime as an exact-first local inference system intended to reduce resident memory pressure while preserving the model weights and transformer architecture.

This is strategically relevant to ODS because it fits the broader ODS direction of separating:

- model;
- hardware;
- memory/storage strategy;
- execution capabilities;
- concrete runtime.

## 3. Current supported execution paths

The current TensorFold documentation describes two major hardware paths.

### Apple Silicon / MLX

TensorFold can stream supported model checkpoints through MLX, retaining only selected layers and pinned tensors under a resident-weight budget.

### NVIDIA / CUDA

TensorFold now documents a dedicated CUDA path for several model families, including:

- Qwen3.8-27B;
- Qwen3.8 Flash Next;
- GLM-5.3-Flash;
- Nemotron families;
- additional family-specific recipes, including DeepSeek and other supported checkpoints.

Support is **family- and checkpoint-specific**. CUDA support therefore does not mean that an arbitrary Hugging Face, SafeTensors, GGUF, or quantized model can be loaded.

The current NVIDIA runbook uses an NVIDIA PyTorch container and installs TensorFold inside it. Some CUDA families use one rank, while others require two ranks and NCCL-based communication.

## 4. OpenAI-compatible API

TensorFold provides an OpenAI-compatible serving boundary.

The current documentation exposes endpoints including:

```text
/v1/models
/v1/chat/completions
/v1/completions
/v1/responses
```

This is the clearest integration advantage for ODS.

The proposed boundary is:

```text
ODS consumer
     ↓
LiteLLM / ODS API layer
     ↓
TensorFold
     ↓
family-specific execution engine
     ↓
model checkpoint
```

ODS applications should not need to know whether the selected model is being served by llama-server or TensorFold.

## 5. Speculative decoding and exactness

Speculative decoding is now a central part of TensorFold rather than merely a future feature.

The current runtime supports draft/verify execution using mechanisms such as:

- prompt-lookup drafting;
- MTP heads;
- DFlash-style draft models;
- family-specific draft policies.

The important property is the project's **same-engine exactness contract**.

TensorFold verifies drafted tokens against serial decoding on the same engine, weights and runtime settings. Its CUDA recipe documentation reports byte-identical results for the documented verification tests.

This distinction must remain explicit in LEONES:

```text
TensorFold exactness
    =
same engine + same weights + same settings

NOT

TensorFold output
    =
all other runtimes / quantizations / hardware
```

Published TensorFold benchmarks are therefore **reported evidence**, not LEONES measurements.

## 6. Current performance evidence

The current TensorFold CUDA recipe book reports measurements on NVIDIA DGX Spark / GB10 hardware.

For example, the documented CUDA recipes report multi-x comparisons against vLLM for selected Qwen3.8 and GLM-5.3-Flash workloads, while the underlying tests also verify byte-identical drafted decoding against TensorFold's serial reference.

These figures are useful for assessing the runtime's architectural potential, but they must not be transferred to an RTX 3050 or another GPU as expected performance.

LEONES should store them as:

```text
source = TensorFold project
evidence = reported
hardware = documented benchmark hardware
not a LEONES measurement
```

## 7. Current LEONES hardware relevance

The development machine used for this study has:

```text
GPU:    NVIDIA RTX 3050 Laptop GPU
VRAM:   4 GB
RAM:    ~14 GB
CUDA:   available
```

TensorFold now having a documented CUDA backend is an important change: NVIDIA support is no longer merely theoretical.

However, the currently documented CUDA recipes target substantially larger-memory NVIDIA systems and specific model/checkpoint combinations. The available documentation does not establish that the modern CUDA recipes fit a 4 GB RTX 3050 Laptop GPU.

Therefore the current LEONES evidence remains:

```text
architecture relevance       = high
CUDA backend exists          = observed in project documentation
RTX 3050 4 GB compatibility  = not established
RTX 3050 performance         = not measured
LEONES measured throughput   = unavailable
```

This is a compatibility/evidence boundary, not a claim that TensorFold can never run on a 4 GB NVIDIA GPU.

## 8. Model-selection implications for ODS

TensorFold should be represented in the ODS capability registry as a **conditional runtime**.

Example:

```yaml
runtime:
  tensorfold:
    supported: conditional
    backends:
      - mlx
      - cuda
    api:
      openai_compatible: true
    capabilities:
      tensor_streaming: true
      speculative_decoding: true
      exact_same_engine_verification: true
    constraints:
      model_family_specific: true
      checkpoint_specific: true
      gguf: false
```

The registry should additionally record:

- supported family;
- exact checkpoint/revision;
- quantization;
- backend;
- GPU requirements;
- rank requirements;
- draft-model requirements;
- context limits;
- memory budget;
- evidence source and evidence class.

A model must not be marked TensorFold-compatible from its architecture name alone.

## 9. ODS integration design

A future ODS integration could expose TensorFold as an optional service:

```text
extensions/services/tensorfold/
├── manifest.yaml
├── compose.yaml
├── Dockerfile
└── README.md
```

The service should provide:

- health checking;
- `/v1/models` discovery;
- explicit model/checkpoint selection;
- hardware compatibility checks;
- TensorFold version capture;
- model/runtime capability metadata;
- optional LiteLLM routing;
- explicit opt-in installation.

Because TensorFold has family-specific kernels and model requirements, ODS should avoid presenting it as a generic model backend.

## 10. Role in the ODS execution framework

TensorFold fits the adaptive ODS architecture as a specialized execution provider:

```text
USER / WORKLOAD
       ↓
MODEL PROFILE
       ↓
HARDWARE + STORAGE PROFILE
       ↓
ODS CAPABILITY REGISTRY
       ↓
EXECUTION STRATEGY
       ↓
RUNTIME SELECTOR
       ↓
 ┌──────────────┬──────────────┬──────────────┐
 │ llama-server │ TensorFold   │ other runtime│
 │ broad        │ specialized  │ specialized  │
 └──────────────┴──────────────┴──────────────┘
       ↓
UNIFIED ODS API
       ↓
LEONES validation
```

TensorFold therefore strengthens the case for a capability-driven ODS selector rather than a fixed list of interchangeable backends.

## 11. Relationship with other LEONES runtime research

TensorFold occupies a different position from projects such as MoE-Infinity, ramvamp, Edge0 or AirLLM.

```text
llama.cpp / llama-server
    broad compatibility

ramvamp
    CPU + RAM/NVMe streaming

MoE-Infinity / WARP / related runtimes
    large-MoE offload and streaming

AirLLM
    Hugging Face layer streaming

TensorFold
    family-specific optimized execution
    + low-resident streaming
    + speculative decoding
    + exact same-engine verification
```

This makes TensorFold particularly interesting as a **specialized accelerator/runtime option**, rather than as another generic backend.

## 12. What not to do

Do not:

- replace llama.cpp/llama-server;
- assume CUDA support means arbitrary NVIDIA GPUs are supported;
- assume a model architecture is supported without checking the exact TensorFold family and checkpoint recipe;
- treat published DGX Spark measurements as RTX 3050 estimates;
- claim a speedup without measuring the same workload on the target hardware;
- treat TensorFold's same-engine exactness as cross-runtime equivalence;
- classify an untested RTX 3050 configuration as `measured`.

## 13. Proposed implementation phases

### Phase 1 — capability integration

Register TensorFold in ODS with explicit model-family/checkpoint constraints.

### Phase 2 — standalone runtime

Build an optional TensorFold service using a documented supported CUDA model on suitable NVIDIA hardware.

### Phase 3 — API integration

Expose the native OpenAI-compatible endpoint through the ODS API/LiteLLM layer.

### Phase 4 — hardware/model admission

Make ODS reject or downgrade candidates when the detected GPU memory, rank topology, context or checkpoint requirements do not fit.

### Phase 5 — LEONES benchmark adapter

Record:

- exact model/revision;
- checkpoint format and quantization;
- TensorFold version;
- GPU/VRAM;
- context;
- draft configuration;
- TTFT;
- prompt processing;
- generation tok/s;
- peak VRAM;
- peak RAM;
- serial vs speculative output equivalence.

### Phase 6 — comparative validation

Where the same model/checkpoint is supported by both runtimes, compare TensorFold against llama.cpp or another ODS runtime under identical conditions.

## 14. Benchmark and evidence rules

For every TensorFold result, LEONES should distinguish:

```text
REPORTED
  TensorFold's own published result.

OBSERVED
  A capability or behavior verified from the repository/runbook.

ESTIMATED
  A compatibility inference made before execution.

MEASURED
  A result actually produced on the target machine by LEONES.
```

Only the last category should be used for claims about actual RTX 3050 throughput, latency or resource consumption.

## 15. Updated conclusion

TensorFold has become a substantially more relevant ODS integration candidate than the initial study suggested.

The important update is not simply that CUDA exists: TensorFold now documents a growing set of **family-specific CUDA engines, model recipes, speculative-decoding paths and exactness tests**, alongside its MLX streaming architecture.

For ODS, the resulting position is:

> **TensorFold should be tracked as a specialized, capability-driven experimental runtime, with strong interest for supported CUDA model families but strict checkpoint and hardware admission.**

For the current RTX 3050 4 GB LEONES machine:

> **No compatibility or performance claim should be made until a documented supported checkpoint can actually be admitted and measured.**

This keeps the integration aligned with the LEONES principle:

```text
DISCOVERY
   ↓
PROFILE
   ↓
CANDIDATES
   ↓
CONSENT
   ↓
INSTALL
   ↓
PHYSICAL VERIFICATION
   ↓
BENCHMARK
   ↓
MEASUREMENT
   ↓
EVIDENCE
```

**Current integration priority:** P2/P3 experimental runtime research, with the priority increasing if a small supported CUDA checkpoint becomes available for low-VRAM NVIDIA hardware.

## References

- https://github.com/ashhart/TensorFold
- https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/cuda.md
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash.md
