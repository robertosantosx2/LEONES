# TensorFold Integration Proposal for ODS

**Experimental track:** `ods-evolution`  
**Project:** LEONES  
**Date:** 2026-09-30  
**Status:** Architecture and integration study — no production integration

## 1. Executive summary

TensorFold is an OpenAI-compatible inference server targeting Apple Silicon and NVIDIA GPUs. Its distinguishing feature is a family-specific kernel/runtime approach combined with speculative decoding and **exact verification against serial decoding on the same engine, weights and settings**.

This makes TensorFold technically interesting for ODS, but very different from a general-purpose llama.cpp backend.

The recommended role is:

> **optional experimental high-performance backend for specific model families and checkpoint formats.**

It should not replace `llama-server`.

Architecture:

```text
                         ODS
                          |
                  Runtime capability
                          |
          +---------------+----------------+
          |               |                |
     llama-server      TensorFold        AirLLM
       GGUF            MLX/CUDA       HF/SafeTensors
          |               |                |
          +---------------+----------------+
                          |
                   OpenAI-compatible
                          |
                    LiteLLM / WebUI
```

## 2. TensorFold's core contribution

TensorFold currently serves supported model families through MLX on Apple Silicon and CUDA on NVIDIA.

The current README documents:

- OpenAI-compatible chat/completions/Responses APIs;
- MLX and CUDA backends;
- family-specific kernels;
- speculative decoding;
- exact draft verification;
- model-family-specific quantized checkpoints;
- optional MTP/DFlash-style draft models;
- vision support for selected Qwen families;
- context and KV-cache controls;
- multi-rank CUDA support for selected families.

This is a specialized engine, not a generic model loader.

## 3. Why it is interesting for ODS

ODS already uses llama.cpp as the broad compatibility backend.

TensorFold could add a second path for models where its specialized kernels and speculative decoding provide a useful performance/quality combination.

The conceptual difference is:

```text
llama.cpp
  = broad local inference engine

TensorFold
  = specialized optimized execution engine
```

This is analogous to having multiple database engines or multiple compilers selected for different workloads.

## 4. OpenAI API compatibility

This is the strongest integration advantage.

TensorFold exposes:

```text
/v1/models
/v1/chat/completions
/v1/completions
/v1/responses
```

Therefore ODS consumers can potentially use it without changing their application-level API.

The integration boundary can be:

```text
ODS consumer
     |
LiteLLM
     |
TensorFold
     |
model-specific kernels
```

## 5. Model format is the main constraint

TensorFold is not a drop-in replacement for arbitrary GGUF models.

The current model table is built around specific checkpoint conversions and supported families.

Examples documented by the project include Qwen3.8, Qwen3.8 Flash Next, Nemotron, GLM, Gemma and DeepSeek families, with backend and quantization restrictions varying by model.

Therefore an ODS model registry would need runtime compatibility metadata:

```yaml
runtime:
  tensorfold:
    supported: true
    backend: cuda
    checkpoint_format: nvfp4
    drafting: mtp
```

A model should not be marked TensorFold-compatible merely because its architecture name looks similar.

## 6. Exact decoding

TensorFold's most interesting technical property is its exact speculative decoding claim.

The runtime verifies drafted tokens against serial execution under the same engine, weights and settings.

This matters because speculative decoding normally introduces a question:

```text
Does accelerated decoding preserve
the reference engine's result?
```

TensorFold makes exactness part of its engine design.

However, exactness is scoped:

- same engine;
- same weights;
- same runtime;
- same settings.

It does not mean MLX and CUDA necessarily produce identical output, nor that different quantizations are identical.

ODS should preserve that distinction in benchmark reports.

## 7. User hardware constraint

The development machine is an RTX 3050 Laptop GPU with 4 GB VRAM and approximately 14 GB RAM.

The TensorFold experiments performed during this project did not produce a practical test path on that hardware for the modern model configurations investigated.

Therefore LEONES should record:

```text
TensorFold:
  architecture relevance = interesting
  local testability on current machine = insufficient
  MEASURED performance = unavailable
```

This is an evidence result, not a claim that TensorFold cannot run on every 4 GB NVIDIA configuration.

The correct future approach is to test it on hardware/model combinations explicitly supported by TensorFold.

## 8. ODS integration design

Add an optional service:

```text
extensions/services/tensorfold/
├── manifest.yaml
├── compose.yaml
├── Dockerfile
└── README.md
```

The service should expose TensorFold's native OpenAI API directly.

ODS should provide:

- health checking;
- model discovery;
- hardware compatibility;
- model/runtime metadata;
- optional LiteLLM routing;
- explicit opt-in installation.

## 9. Runtime capabilities

TensorFold could advertise:

```yaml
capabilities:
  openai_api: true
  speculative_decoding: true
  exact_same_engine_verification: true
  model_family_specialization: true
  cuda: true
  mlx: true
  gguf: false
```

The exact metadata should be generated from the actual installed TensorFold version.

## 10. Role in LEONES

TensorFold should be treated as a runtime candidate.

```text
Model
  |
  +-- llama.cpp
  |
  +-- TensorFold
  |
  +-- AirLLM
  |
  +-- vLLM
  |
  v
FIT / ESTIMATED
  |
human selection
  |
physical benchmark
  |
MEASURED
```

TensorFold's README-supported model matrix can produce ESTIMATED compatibility.

Only an actual run produces MEASURED throughput and latency.

## 11. What not to do

Do not:

- replace llama.cpp;
- treat TensorFold as a generic GGUF engine;
- claim speculative decoding is automatically faster on every model/GPU;
- infer support for a new checkpoint from architecture name alone;
- label the current RTX 3050 test as a performance measurement when no practical supported run was obtained.

## 12. Implementation phases

### Phase 1
Standalone TensorFold container with one known-supported model.

### Phase 2
ODS manifest and health check.

### Phase 3
LiteLLM model target.

### Phase 4
Model registry capability metadata.

### Phase 5
LEONES benchmark adapter.

### Phase 6
Compare TensorFold vs llama.cpp on the same model where both support the same checkpoint.

## 13. Benchmark design

A fair comparison should record:

- model/checkpoint;
- quantization;
- backend;
- GPU;
- VRAM;
- context;
- prompt;
- TTFT;
- prompt processing;
- generation tok/s;
- peak VRAM;
- peak RAM;
- speculative decoding enabled/disabled;
- exact output comparison where applicable.

The same request must be used for the competing runtimes.

## 14. Conclusion

TensorFold is a **specialized accelerator backend**, not an ODS foundation replacement.

Its strongest reasons for experimentation are:

1. OpenAI-compatible API;
2. specialized kernels;
3. speculative decoding;
4. exact verification within the same engine;
5. modern quantized model support;
6. MLX + CUDA coverage.

Its main limitation for ODS is the narrow model/checkpoint matrix and the fact that the current LEONES development machine did not provide a practical test target for the configurations investigated.

**Verdict:** technically interesting as an optional experimental runtime; do not make it the default ODS engine.

## References

- https://github.com/ashhart/TensorFold
