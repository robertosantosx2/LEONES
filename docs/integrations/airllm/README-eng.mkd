# AirLLM Integration Proposal for ODS

**Experimental track:** `ods-evolution`  
**Project:** LEONES  
**Date:** 2026-09-30  
**Status:** Architecture and integration study — no production integration yet

## 1. Executive summary

AirLLM is a strong candidate for an **optional memory-constrained inference runtime** in ODS.

The important point is that AirLLM should **not replace ODS's current `llama-server`/llama.cpp path**. It solves a different problem:

- ODS/llama.cpp is the normal, high-performance path for supported GGUF models.
- AirLLM can stream model weights layer-by-layer, and for supported sparse MoE models can stream individual experts, allowing models that would not fit entirely in GPU memory to execute on much smaller GPUs.
- AirLLM is primarily a Python/Hugging Face/SafeTensors runtime, so ODS needs an adapter service if it is to participate in the same OpenAI-compatible service topology.

The proposed direction is therefore:

```text
                         ODS
                          |
                    Runtime Router
                          |
          +---------------+---------------+
          |               |               |
          v               v               v
     llama-server       AirLLM           vLLM
       llama.cpp       HF/SafeTensors     HF
         GGUF          layer/expert      HF
                       streaming
          |               |               |
          +---------------+---------------+
                          |
                   OpenAI-compatible API
                          |
          +---------------+---------------+
          |               |               |
       Open WebUI       Hermes          Agents
```

The experimental ODS evolution should therefore treat AirLLM as a **specialized runtime**, not as a second copy of the normal ODS inference stack.

---

## 2. Current ODS architecture

ODS currently uses `llama-server` as its main local inference foundation. The project architecture documents a layered Docker Compose system, hardware-specific inference paths, and a manifest-based extension mechanism. LiteLLM provides a standardized OpenAI-compatible gateway for consumers. citeturn0search0turn0search2

The current architecture is approximately:

```text
Browser
   |
Open WebUI / Dashboard / Agents
   |
LiteLLM or direct OpenAI-compatible endpoint
   |
llama-server
   |
llama.cpp
   |
GGUF model
   |
CPU / GPU
```

ODS already has the architectural mechanisms needed for an additional service:

- service manifests;
- Docker Compose extension fragments;
- health checks;
- GPU/backend metadata;
- service discovery on the ODS network;
- configurable inference backend selection;
- OpenAI-compatible API consumers.

ODS explicitly documents extensions as services under `extensions/services/<id>/`, with `manifest.yaml` and `compose.yaml` as the core contract. citeturn0search8

This makes an AirLLM integration feasible without redesigning the whole platform.

---

## 3. What AirLLM contributes

AirLLM is fundamentally different from llama.cpp.

Its main technique is **layer streaming**:

1. Keep the model structure resident.
2. Load the weights needed for one layer.
3. Move the layer to the accelerator.
4. Execute it.
5. Release/offload it.
6. Prefetch the next layer where possible.
7. Continue through the model.

The current AirLLM implementation also contains **per-expert streaming** for supported sparse MoE layouts. Instead of materialising all experts in an MoE layer, only the experts selected by routing are loaded. citeturn0search4

AirLLM v3.0.0 also documents support for current Hugging Face model families, FP8 checkpoints, and large MoE models. Its release notes describe the runtime as capable of streaming very large models on small GPUs, but these are AirLLM project claims and must not be treated as LEONES measurements until reproduced on the target machine. citeturn0search7

### Relevant capabilities

| Capability | AirLLM | ODS/llama.cpp |
|---|---:|---:|
| GGUF | Not the primary format | Yes |
| Hugging Face/SafeTensors | Yes | Not primary |
| Layer streaming | Yes | Different memory/offload model |
| MoE expert streaming | Yes, for supported layouts | Has MoE CPU offload, but different mechanism |
| GPU inference | Yes | Yes |
| CPU involvement | Yes | Yes |
| OpenAI-compatible API | Adapter required for ODS | Native server path |
| Very large models on small VRAM | Core use case | Limited by model/offload configuration |
| Production maturity inside ODS | Not integrated | Current default |
| Fast normal inference | Not its primary differentiator | Core strength |

---

## 4. Why AirLLM is interesting for LEONES

LEONES is explicitly designed to separate:

```text
FIT / ESTIMATED
        from
MEASURED / EVIDENCE
```

That distinction is especially important here.

A model can be technically loadable by AirLLM but still be impractical because of:

- model storage size;
- disk throughput;
- CPU preprocessing;
- PCIe transfer overhead;
- RAM requirements;
- VRAM requirements;
- first-token latency;
- tokens/second;
- thermal throttling;
- context length.

Therefore AirLLM should extend the **candidate runtime space**, not automatically make a model a recommendation.

A future LEONES decision could look like:

```text
Model
  |
  +-- llama.cpp / GGUF
  |       |
  |       +-- fits
  |       +-- benchmark
  |
  +-- AirLLM / HF
          |
          +-- fits through streaming
          +-- benchmark
          +-- compare actual performance
```

This preserves the LEONES evidence contract.

---

## 5. Proposed ODS architecture

### 5.1 Runtime contract

Instead of hard-coding an engine name into higher-level logic, ODS should evolve toward a runtime capability description.

Example:

```yaml
runtime:
  engine: llama-server
  protocol: openai
  model_format: gguf
  capabilities:
    gpu_offload: true
    layer_streaming: false
    moe_expert_streaming: false
```

AirLLM:

```yaml
runtime:
  engine: airllm
  protocol: openai
  model_format: safetensors
  capabilities:
    gpu_offload: true
    layer_streaming: true
    moe_expert_streaming: true
    prefetch: true
```

This abstraction is more useful than simply adding:

```text
LLM_BACKEND=airllm
```

because LEONES and ODS can reason about **what a runtime can do**, rather than only its name.

### 5.2 Proposed service

Create:

```text
extensions/services/airllm/
├── manifest.yaml
├── compose.yaml
├── Dockerfile
├── README.md
└── server/
    ├── main.py
    ├── openai_api.py
    ├── model_manager.py
    └── health.py
```

The service could be named:

```text
ods-airllm
```

It would expose an OpenAI-compatible API.

Minimum contract:

```text
GET  /health
GET  /v1/models
POST /v1/chat/completions
POST /v1/completions
```

Optional:

```text
GET /metrics
GET /v1/models/{model}
```

The adapter would translate API requests into AirLLM model loading and `generate()` calls.

---

## 6. Docker and ODS integration

The first implementation should be an **optional extension**, not part of the mandatory ODS installation.

Conceptually:

```yaml
services:
  airllm:
    build:
      context: .
    container_name: ods-airllm
    restart: unless-stopped
    ports:
      - "${AIRLLM_PORT:-8095}:8080"
    environment:
      - HF_HOME=/data/huggingface
      - HF_TOKEN=${HF_TOKEN:-}
    volumes:
      - ./data/models:/data/models
      - ./data/huggingface:/data/huggingface
      - ./data/airllm-cache:/data/airllm-cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - ods-network
```

This is illustrative, not a ready-to-merge Compose file.

The exact GPU configuration should follow the ODS NVIDIA extension conventions rather than introducing an independent Docker GPU mechanism.

---

## 7. Model storage

This is one of the largest architectural differences.

The current ODS normal path is centred on GGUF model files in the ODS model storage. AirLLM is oriented around Hugging Face model repositories and SafeTensors/checkpoint shards.

Therefore the integration should not try to force both runtimes into one physical model format.

Instead:

```text
ODS model registry
        |
        +--------------------+
        |                    |
        v                    v
      GGUF                HF/SafeTensors
        |                    |
        v                    v
   llama-server           AirLLM
```

The model registry should eventually record:

- repository;
- revision;
- format;
- shard count;
- total size;
- dtype;
- quantization;
- architecture;
- context limits;
- VRAM estimate;
- RAM estimate;
- disk estimate;
- supported runtimes.

---

## 8. Runtime selection

A future ODS/LEONES runtime selector could use a decision tree such as:

```text
                 Candidate model
                       |
                What format?
                 /          \
              GGUF       HF/SafeTensors
                |              |
           llama.cpp        Can normal HF
                |            loading fit?
             fits?           /       \
             /  \          yes        no
           yes   no          |          |
            |    |        vLLM/HF     AirLLM
            |    |                     |
            |    |              layer/expert stream
            |    |                     |
            +----+---------------------+
                       |
                    benchmark
                       |
                    MEASURED
```

This is intentionally a **selection mechanism**, not a recommendation engine by itself.

---

## 9. Interaction with LiteLLM

LiteLLM is already used by ODS as an OpenAI-compatible gateway. citeturn0search0turn0search3

That gives two possible integration strategies.

### Strategy A — direct runtime endpoint

```text
Open WebUI
    |
    v
AirLLM :8095
```

Useful for early experiments.

### Strategy B — AirLLM behind LiteLLM

```text
Open WebUI / Hermes / other consumers
              |
              v
          LiteLLM
          /     \
         /       \
llama-server   AirLLM
```

This is preferable for a mature integration because consumers continue to use one API gateway while the runtime can change underneath.

It also allows:

- model aliases;
- runtime routing;
- authentication;
- fallback;
- logging;
- usage accounting.

---

## 10. Runtime router proposal

The longer-term architecture should move toward:

```text
                    ODS Runtime Router
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
   llama.cpp            AirLLM              vLLM
      GGUF           HF/SafeTensors      HF/SafeTensors
        |                  |                  |
        +------------------+------------------+
                           |
                       LiteLLM
                           |
             +-------------+-------------+
             |             |             |
          WebUI          Hermes        Agents
```

The router should select a runtime based on:

- model format;
- architecture;
- model size;
- quantization;
- GPU VRAM;
- system RAM;
- disk capacity;
- GPU backend;
- runtime capabilities;
- user-selected latency/performance objective;
- measured historical results.

The last item is important for LEONES: **measured results should be able to override generic estimates.**

---

## 11. User hardware relevance

The target development machine has approximately:

- NVIDIA RTX 3050 Laptop GPU;
- 4 GB VRAM;
- Intel 12th Gen i7-12650H;
- approximately 14 GB usable system RAM.

AirLLM is particularly interesting on this class of machine because its purpose is to reduce the requirement that the complete model fit in GPU memory.

However, this does **not** mean that every large model becomes practically usable.

The limiting resource can simply move from:

```text
VRAM
```

to:

```text
VRAM + RAM + NVMe bandwidth + PCIe transfer + compute
```

For this machine, a meaningful experiment should therefore measure at least:

- model load time;
- first-token latency;
- prompt processing speed;
- generation tok/s;
- peak VRAM;
- peak RAM;
- disk footprint;
- sustained disk read rate;
- context length;
- stability;
- output correctness.

---

## 12. Performance expectations

AirLLM should not be sold internally as a free way of making huge models fast.

Its primary value is **memory feasibility**.

A useful conceptual distinction is:

```text
Traditional inference:

       model weights
            |
         VRAM/RAM
            |
         compute
            |
         tokens


AirLLM:

       model weights
            |
      disk / host RAM
            |
       layer/expert
            |
          VRAM
            |
         compute
            |
       unload/prefetch
            |
       next layer/expert
```

This introduces additional movement of weights.

Consequently:

- smaller models may be faster with llama.cpp;
- models that comfortably fit VRAM should normally remain on llama.cpp;
- AirLLM becomes interesting when memory constraints are the dominant problem;
- large MoE models are especially interesting because expert streaming can avoid materialising inactive experts.

The correct LEONES result must come from physical benchmarking.

---

## 13. MoE opportunity

AirLLM's expert streaming is particularly relevant to ODS evolution.

A sparse MoE model may contain a very large total parameter count while each token activates only a subset of experts.

AirLLM can exploit this by loading selected experts on demand for supported checkpoint layouts. citeturn0search4

This suggests a future ODS capability field:

```yaml
capabilities:
  moe:
    supported: true
    expert_streaming: true
```

Then LEONES could distinguish:

```text
Total parameters
        !=
Active parameters per token
        !=
Resident parameters
        !=
Streamed parameters
```

This distinction is important for hardware-aware model selection.

---

## 14. AirLLM should not replace llama.cpp

The integration should explicitly preserve the current ODS path.

### llama.cpp remains appropriate for

- GGUF models;
- models that fit comfortably in available memory;
- low-latency local inference;
- standard ODS deployments;
- predictable GPU offload;
- users who do not need layer streaming.

### AirLLM is appropriate to investigate for

- models too large for normal VRAM loading;
- Hugging Face/SafeTensors checkpoints;
- very large models;
- sparse MoE models;
- experimental memory-constrained inference;
- models where layer/expert streaming can make execution possible.

The two runtimes are complementary.

---

## 15. Proposed ODS configuration

A future configuration could look like:

```dotenv
LLM_BACKEND=auto
LLM_RUNTIME_POLICY=fit
AIRLLM_ENABLED=false
AIRLLM_PORT=8095
AIRLLM_MODEL=
AIRLLM_MODEL_REVISION=
AIRLLM_CACHE_DIR=/data/airllm-cache
```

Possible runtime policies:

```text
auto
llama
airllm
vllm
external
```

Possible selection policies:

```text
fit
performance
memory
measured
manual
```

The exact names should be decided during implementation; these are architectural proposals only.

---

## 16. Security and isolation

AirLLM should run as an ODS-local service.

Recommended constraints:

- bind externally only to localhost;
- join the existing ODS network;
- avoid unnecessary host mounts;
- use a dedicated model/cache directory;
- propagate `HF_TOKEN` only when explicitly configured;
- do not expose Hugging Face credentials to unrelated services;
- keep model downloads controlled by the ODS model lifecycle;
- retain ODS authentication/gateway controls where appropriate.

A model-loading service should not automatically become an unrestricted host execution service.

---

## 17. Failure handling

AirLLM introduces new failure classes:

### Model incompatibility

The checkpoint may be available on Hugging Face but unsupported by the current AirLLM version.

### Insufficient system RAM

GPU streaming does not eliminate host-memory requirements.

### Insufficient disk

Large checkpoints and caches can require substantial local storage.

### Excessive I/O

The model may technically fit but be unusably slow.

### Unsupported MoE layout

Expert streaming depends on checkpoint/module structure.

### Runtime regression

A newer Transformers/AirLLM version may change model loading behaviour.

Therefore the service health endpoint should distinguish:

```text
healthy
starting
model-loading
model-ready
model-incompatible
insufficient-memory
insufficient-disk
runtime-error
```

---

## 18. LEONES evidence model

The integration should preserve the existing LEONES principle:

> Providers can propose. FitLLM can recommend. The user chooses. Only a controlled execution on the real machine can produce a LEONES measurement.

For AirLLM:

### ESTIMATED

Derived from:

- model metadata;
- checkpoint size;
- dtype;
- architecture;
- declared runtime capabilities;
- hardware inventory.

### MEASURED

Only after actual execution:

- load time;
- TTFT;
- prompt tok/s;
- generation tok/s;
- peak VRAM;
- peak RAM;
- disk I/O;
- context tested;
- errors.

A model should never be marked `MEASURED` merely because AirLLM's README says it can run on a particular GPU size.

---

## 19. Suggested benchmark A02

The existing A01 measurement chain can remain the general runtime benchmark.

An AirLLM-specific experiment could be:

```text
A02-AIRLLM

1. Discover hardware
2. Record model provenance
3. Verify checkpoint
4. Install/prepare AirLLM
5. Start ods-airllm
6. Wait for /health
7. Query /v1/models
8. Send deterministic prompt
9. Record TTFT
10. Record prompt processing
11. Record generation tok/s
12. Record VRAM
13. Record RAM
14. Record disk I/O
15. Repeat
16. Store raw evidence
17. Produce summary
```

This allows AirLLM to become another measured runtime without changing the core LEONES philosophy.

---

## 20. Proposed implementation phases

### Phase 0 — Documentation

This document.

No ODS production changes.

### Phase 1 — Standalone adapter

Create a small Python service around AirLLM.

Requirements:

- FastAPI;
- OpenAI-compatible endpoints;
- health endpoint;
- one model at a time;
- explicit model configuration;
- no automatic model recommendation.

### Phase 2 — ODS extension

Add:

```text
extensions/services/airllm/
```

with:

- manifest;
- Compose;
- Dockerfile;
- health check;
- README;
- NVIDIA configuration.

### Phase 3 — LiteLLM integration

Expose AirLLM as another backend/model target.

### Phase 4 — Model registry

Teach ODS about:

- HF repository;
- SafeTensors;
- checkpoint shards;
- AirLLM compatibility;
- storage requirements.

### Phase 5 — Runtime selection

Introduce capability-aware selection.

### Phase 6 — LEONES integration

LEONES consumes the runtime metadata and produces ESTIMATED candidates.

After user consent, the selected runtime is executed and produces MEASURED evidence.

---

## 21. What should NOT be done initially

Do not:

- replace `llama-server`;
- make AirLLM mandatory;
- automatically download hundreds of GB of checkpoints;
- treat README hardware claims as benchmark evidence;
- mix AirLLM estimates with measured ODS results;
- hide the runtime choice from the user;
- make AirLLM the default for small models;
- redesign the entire ODS model registry before proving the runtime adapter.

The first experiment should be deliberately small.

---

## 22. Initial proof of concept

The recommended first POC is:

```text
LEONES
   |
user selects model
   |
runtime = AirLLM
   |
ods-airllm
   |
OpenAI-compatible endpoint
   |
LiteLLM
   |
Open WebUI
```

The success criterion is not "run the biggest possible model".

The first success criterion is:

> A model that AirLLM can execute on the target NVIDIA machine can be exposed through the same OpenAI-compatible interface used by the rest of ODS and produce reproducible LEONES measurements.

---

## 23. Architectural conclusion

AirLLM is a good candidate for an **experimental ODS evolution path** because it extends ODS in a direction that llama.cpp does not target in the same way: memory-constrained inference through layer and, for supported models, expert streaming.

The recommended architecture is:

```text
                         ODS
                          |
                  Capability-aware
                   runtime selection
                          |
             +------------+------------+
             |                         |
             v                         v
       llama-server                ods-airllm
        llama.cpp                   AirLLM
          GGUF                  HF/SafeTensors
             |                         |
             +------------+------------+
                          |
                       LiteLLM
                          |
             Open WebUI / Hermes / Agents
                          |
                        LEONES
                          |
                 ESTIMATED -> MEASURED
```

The key architectural principle is:

> **AirLLM should be an additional runtime capability, not a replacement inference engine.**

This approach preserves the stability and performance characteristics of the current ODS path while opening an experimental path for models that are otherwise constrained by GPU memory.

---

## 24. References

- AirLLM repository: https://github.com/lyogavin/airllm
- AirLLM layer/expert streaming implementation: https://github.com/lyogavin/airllm/blob/main/air_llm/airllm/airllm_base.py
- AirLLM releases: https://github.com/lyogavin/airllm/releases
- ODS repository: https://github.com/Osmantic/ODS
- ODS architecture: https://github.com/Osmantic/ODS/blob/main/ARCHITECTURE.md
- ODS extension system: https://github.com/Osmantic/ODS/blob/main/ods/docs/EXTENSIONS.md
- ODS server architecture: https://github.com/Osmantic/ODS/blob/main/ods/docs/HOW-ODS-SERVER-WORKS.md

**Evidence note:** claims about AirLLM's ability to run very large models on small GPUs are attributed to the AirLLM project. They are not treated here as LEONES measurements. Actual feasibility and performance must be established by controlled execution on the target hardware.
