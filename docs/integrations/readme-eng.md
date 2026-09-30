# ODS Inference Runtime Integrations

These integrations and research efforts turn external tools into **measurable, documented profiles** without making them structural LEONES dependencies.

## Strategic Introduction: Towards ODS as an Adaptive Execution Framework

Research into runtimes, MoE, expert streaming, CPU/GPU collaboration, predictive caching, and model/hardware profiling points toward an important evolution for ODS.

The goal should not be for ODS to be simply a catalog of backends:

```text
ODS
 ├── llama-server
 ├── MoE-Infinity
 ├── ramvamp
 ├── Edge0
 └── otros runtimes
```

That design makes ODS primarily an **engine selector**. A more powerful architecture is to turn ODS into an **execution abstraction and composition layer**, capable of selecting the best combination of model, strategy, capabilities, and runtime for the user's specific hardware and needs.

### Overview

```text
                         ODS AI EXECUTION FRAMEWORK
                         ==========================

┌───────────────────────────────────────────────────────────────────────┐
│                         USER / USE-CASE                               │
│                                                                       │
│ latency · quality · privacy · context · modality · throughput         │
│ power · storage · RAM · VRAM · budget · offline requirements         │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    MODEL / WORKLOAD PROFILE                           │
│                                                                       │
│ Dense / MoE · active parameters · quantization · context              │
│ multimodal · expert count · routing pattern · KV-cache requirements   │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     HARDWARE / STORAGE PROFILE                        │
│                                                                       │
│ CPU · RAM · GPU · VRAM · CUDA · ROCm · Metal · NPU                   │
│ PCIe · NVMe · bandwidth · memory pressure · available storage         │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     ODS CAPABILITY REGISTRY                           │
│                                                                       │
│ model · hardware · runtime · storage · API · memory · MoE capabilities│
│ constraints · compatibility · measured evidence                       │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                 EXECUTION STRATEGY / COMPOSITION                      │
│                                                                       │
│ expert prediction → prefetch → cache → offload → precision fallback   │
│                                                                       │
│       FATE          Edge0          HOBBIT          HybriMoE            │
│        │              │               │                │              │
│        └──────────────┴───────────────┴────────────────┘              │
│                                                                       │
│ These should be treated as composable capabilities, not simply as     │
│ four independent backends.                                            │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    RUNTIME SELECTOR / OPTIMIZER                        │
│                                                                       │
│             hardware + model + user requirements + evidence           │
│                              │                                        │
│                              ▼                                        │
│                   select / compose execution strategy                 │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       low-VRAM strategy     CPU/NVMe strategy     large-CUDA strategy
              │                     │                     │
              ▼                     ▼                     ▼
       llama.cpp /            ramvamp /             MoE-Infinity /
       llama-server           streaming             vLLM / SGLang / WARP
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         UNIFIED ODS API                                │
│                  OpenAI-compatible service layer                       │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼

```

### 1. User / use-case layer

ODS should start from the **execution objective**, not from the available backend. Latency, quality, privacy, context, modality, throughput, power consumption, storage, and budget can all change the optimal strategy.

For example, an interactive assistant with a small GPU needs a different strategy from a batch workload on a high-capacity GPU. Selection should follow from requirements and detected capabilities.

### 2. Model / workload profile

The model profile must go beyond the model name and total parameter count. For MoE, the following are particularly important:

```text
total parameters
active parameters
number of experts
experts/token
quantization
context
multimodality
routing characteristics
KV-cache requirements
```

This makes it possible to distinguish, for example, a large dense model from an MoE with many total parameters but relatively few active parameters.

### 3. Hardware / storage profile

Hardware should be described as a set of resources and capabilities:

```text
CPU · RAM · GPU · VRAM
CUDA · ROCm · Metal · NPU
PCIe · NVMe · bandwidth
memory pressure · available storage
```

This allows ODS to reason about a concrete system, for example:

```text
RTX 3050 4 GB
+ 16 GB RAM
+ NVMe
+ CUDA
+ limited VRAM
```

rather than simply assuming that "NVIDIA = llama-server".

### 4. Capability Registry

The **Capability Registry** would be the abstraction connecting models, hardware, storage, and runtimes.

A runtime could declare capabilities such as:

```text
MoE-Infinity
 ├── CUDA
 ├── expert offload
 ├── RAM
 ├── SSD
 ├── MoE
 └── OpenAI-compatible serving

ramvamp
 ├── CPU
 ├── RAM
 ├── NVMe
 ├── MoE
 ├── expert streaming
 └── OpenAI-compatible serving
```

The registry should also include constraints, compatibility, and evidence. This allows ODS to ask:

> What combinations can execute this model with the available resources?

instead of merely asking:

> What runtimes are installed?

### 5. Execution Strategy / Composition

This is the most important strategic layer.

The findings around **Edge0 + FATE + HOBBIT + HybriMoE** suggest that they should not simply become four more entries in the backend catalog.

The most interesting direction is to turn their ideas into **composable capabilities**:

```text
                    ODS MoE Execution Layer

          FATE
           │
           ▼
    expert prediction
           │
           ▼
       Edge0
           │
           ▼
        prefetch
           │
           ▼
      HOBBIT
           │
           ├──── cache
           │
           └──── precision adaptation
           │
           ▼
      HybriMoE
           │
           ├──── GPU
           ├──── CPU
           └──── RAM/NVMe
           │
           ▼
    selected runtime
```

The strategic direction for ODS is therefore:

```text
expert prediction
        ↓
     prefetch
        ↓
      cache
        ↓
     offload
        ↓
precision fallback
```

according to the hardware, model, memory pressure, and user objectives.

#### Edge0

Edge0 is particularly relevant because of its combination of expert streaming, routing prediction, prefetch, and SSD support. Its architectural value can be expressed as an **expert prefetch/streaming** capability, rather than requiring the entire system to run inside Edge0.

#### FATE

FATE primarily fits into **expert prediction** and anticipating which experts will be needed. That information can feed a prefetcher or cache system independently of the final backend.

#### HOBBIT

HOBBIT contributes **adaptive prefetch, multidimensional expert caching, and mixed precision**. This allows ODS to consider both which experts to keep hot and which representation to use, based on available memory.

#### HybriMoE

HybriMoE contributes a **CPU/GPU scheduling and collaboration** perspective, allowing work and memory to be distributed across heterogeneous resources rather than assuming everything must remain on the GPU.

### 6. Runtime Selector / Optimizer

Once the following are known:

```text
USER NEEDS
     +
MODEL
     +
HARDWARE
     +
STORAGE
     +
CAPABILITIES
     +
EVIDENCE
```

ODS can select or compose an execution strategy.

For example, for a machine with a small GPU:

```text
RTX 3050 4 GB + RAM + NVMe + MoE
                    │
                    ▼
       expert paging / streaming
                    +
           predictive prefetch
                    +
             small VRAM cache
                    +
               RAM cache
                    +
              NVMe backing
                    +
            precision fallback
```

The concrete runtime could be llama.cpp/llama-server if it provides the required capabilities, or one of the specialized runtimes. The final choice must be validated by measurement rather than assumed from theory.

For CPU + large RAM + NVMe, a CPU/NVMe strategy may make ramvamp a natural candidate. For large NVIDIA GPUs, vLLM, SGLang, MoE-Infinity, WARP, or other runtimes may enter the candidate set depending on the model and available capabilities.

### 7. Runtimes Are No Longer Necessarily Competitors

In this architecture, the researched projects become **execution providers** with different capabilities:

```text
                         ODS EXECUTION FABRIC

       llama.cpp          vLLM             SGLang
       llama-server       WARP             MoE-Infinity
       ramvamp            Edge0            SSD MoE
       BigMoeLLM          FrankenMoE       others
            │                │                 │
            └────────────────┼─────────────────┘
                             │
                      Capability Registry
```

WARP, for example, can be viewed as a specialized strategy for large MoE models and NVMe, while llama-server may be the simpler option for normal GGUF models and hardware with sufficient VRAM. The selector should be able to distinguish them according to the use case.



### Architectural Objective

The final vision is for ODS not to simply ask:

> **"Which backend should I use?"**

sino:

> **"What combination of model, capabilities, execution strategy, and runtime is appropriate for this model, this hardware, and this objective?"**

This would progressively turn ODS from a platform that distributes multiple inference engines into a potential **adaptive local inference orchestration framework**.

## Main Integrations

- **LLMFit — preselector hardware-aware**.
- **ODS — Servidor de Stacks IA**.
- **Magnitude — asistente personal IA**.
- **WARP — runtime experimental para MoE grandes mediante paging desde NVMe**.

## ODS Runtime Research

### P1 — high priority

| Project | Profile | Report |
|---|---|---|
| MoE-Infinity | MoE CUDA + RAM/SSD offload + serving | [MoE-Infinity](moe-infinity/README.md) |
| ramvamp | CPU/NVMe MoE streaming | [ramvamp](ramvamp/README.md) |
| Edge0 | SSD streaming + routing prediction | [Edge0](edge0/README.md) |
| FATE | expert prediction + async prefetch | [FATE](fate/README.md) |
| MoE-Lens | hardware/performance modeling | [MoE-Lens](moe-lens/README.md) |
| HybriMoE | CPU/GPU scheduling + cache | [HybriMoE](hybrimoe/README.md) |
| BigMoeLLM | MoE > VRAM, mmap/paging | [BigMoeLLM](bigmoellm/README.md) |
| FrankenMoE-CUDA | NVMe→RAM→VRAM expert tiers | [FrankenMoE-CUDA](frankenmoe-cuda/README.md) |
| llama.cpp expert paging PoC | possible upstream evolution | [llama.cpp expert paging](llama-cpp-expert-paging/README.md) |
| LocalAI | multi-backend architecture | [LocalAI](localai/README.md) |
| llama-cpp-studio | multi-runtime control plane | [llama-cpp-studio](llama-cpp-studio/README.md) |
| WARP | MoE NVMe paging | [WARP](WARP/README.md) |

### P2 — candidates / research

| Project | Profile | Report |
|---|---|---|
| SSD MoE | SSD streaming | [ssdmoe](ssdmoe/README.md) |
| ExpertFlow | predictive expert caching | [ExpertFlow](expertflow/README.md) |
| moe-hotcache | hot-expert cache on llama.cpp | [moe-hotcache](moe-hotcache/README.md) |
| vllm-moe | CPU offload + GPU prefetch | [vllm-moe](vllm-moe/README.md) |
| vLLM RFC | MoE CPU offload design | [RFC](vllm-cpu-offload-rfc/README.md) |
| DynaExQ | dynamic precision/residency | [DynaExQ](dynaexq/README.md) |
| MoE CPU/GPU Collaborative Inference | CPU/GPU caching | [CPU/GPU](moe-cpu-gpu-collaborative-inference/README.md) |
| local-llm-npu | Intel NPU/OpenVINO | [NPU](local-llm-npu/README.md) |
| Atomic-Chat | local multi-engine | [Atomic-Chat](atomic-chat/README.md) |
| llama.cpp.35B.moe | MoE CUDA optimizations | [fork](llama-cpp-35b-moe/README.md) |
| moe-ssd-streaming-windows | Windows/NVIDIA SSD streaming | [Windows](moe-ssd-streaming-windows/README.md) |
| expert-streaming-engine | expert streaming | [engine](expert-streaming-engine/README.md) |
| ds4-ssd | SSD/weight streaming | [ds4-ssd](ds4-ssd/README.md) |
| moe-edge-inference | MoE edge | [edge](moe-edge-inference/README.md) |
| moe-stream | MoE streaming | [stream](moe-stream/README.md) |
| HOBBIT | mixed-precision expert cache | [HOBBIT](hobbit/README.md) |
| MoE-Gen | single-GPU MoE throughput | [MoE-Gen](moe-gen/README.md) |
| Fiddler | CPU/GPU collaborative inference | [Fiddler](fiddler/README.md) |

### P3 — radar

| Project | Profile | Report |
|---|---|---|
| oBeaver | local/platform-aware toolkit | [oBeaver](obeaver/README.md) |
| Forge | general Rust/CUDA runtime | [Forge](forge/README.md) |
| BaseRT | Apple/NVIDIA-specific runtime | [BaseRT](basert/README.md) |
| ES-MoE | training offload | [ES-MoE](es-moe/README.md) |
| weight-streaming | weight streaming | [weight-streaming](weight-streaming/README.md) |

## Boundary Rule

External tools remain responsible for their installation, runtime, and internal behavior. LEONES handles preflight, consent, reproducible installation where applicable, configuration capture, independent validation, benchmarking, and separation of `estimated` / `reported` / `observed` / `measured` evidence.

**Important:** figures published by projects are not LEONES measurements until they are reproduced.

## Common Workflow

```text
PREFLIGHT → CONSENT → CONTROLLED INSTALLATION
→ HEALTH/STATUS → CONFIGURATION → BENCHMARK
→ ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
→ EVIDENCE
```
