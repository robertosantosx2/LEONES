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
 └── other runtimes
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

but rather:

> **"What combination of model, capabilities, execution strategy, and runtime is appropriate for this model, this hardware, and this objective?"**

This would progressively turn ODS from a platform that distributes multiple inference engines into a potential **adaptive local inference orchestration framework**.

## Magnitude as a Personal AI Assistant Integration

Magnitude occupies a different position from the inference runtimes investigated in this index. In LEONES, it is studied as a reference integration for the **Personal AI Assistant** profile: Magnitude provides the agent and its local execution, while LEONES provides preflight, installation, governance, validation, and benchmarking.

According to the dedicated [Magnitude](Magnitude-eng.mkd) report, relevant capabilities include:

- local agent and local models;
- hardware profiling;
- model recommendation;
- download and configuration;
- local execution;
- skills;
- OpenAI-compatible endpoints;
- a privacy/offline-oriented approach for local execution.

This fits the adaptive ODS architecture because Magnitude can contribute information and user experience to the **model/workload profiling**, **hardware profiling**, and **model selection** layers, without becoming the inference runtime that ODS must use.

The LEONES validation flow is:

```text
preflight
   ↓
install CLI
   ↓
hardware profile
   ↓
model recommendation
   ↓
user confirmation for large downloads
   ↓
model/Hugging Face/file/quantization record
   ↓
agent + tools validation
   ↓
independent LEONES benchmark
   ↓
evidence
```

Skills should be cataloged by origin, version/ref, permissions, file access, network access, and tools. LEONES should not automatically install risky skills. Data should also distinguish `observed`, `recommended/configured`, `estimated`, and `measured`, while avoiding the recording of prompts, files, code, conversations, secrets, or API keys.

## Main Integrations

- **LLMFit — hardware-aware preselector**.
- **ODS — AI stack server**.
- **Magnitude — reference integration for a Personal AI Assistant**: [Magnitude](Magnitude-eng.mkd).
- **WARP — experimental runtime for large MoE models using NVMe paging**.
- **TensorFold — specialized MLX/CUDA runtime with speculative decoding and same-engine exactness verification**.

## ODS Runtime Research


### P0 — strategic integration / active qualification

P0 is introduced here for projects that have crossed the threshold from research interest to a strategically important integration target: the upstream runtime is operationally mature, its API and capability surface align with ODS, and there is a concrete path to controlled qualification. P0 does **not** mean that integration is already implemented, that every model is supported, or that the project is safe to enable by default.

| Project | Profile | Report |
|---|---|---|
| TensorFold | multi-backend native inference provider; CUDA/HIP/XPU paths; OpenAI/Anthropic APIs; speculative decoding, prompt-state reuse, concurrency and image-capable serving | [TensorFold](tensorfold/README-eng.mkd) |

### Why TensorFold has been promoted to P0

A fresh review on 2026-11-13 changes the earlier P1 assessment. TensorFold has advanced through the 1.2.x engine line to **1.2.7 (released 2026-11-11)**. This is not just a version-number increase: the release stream demonstrates active work across model families, accelerators, serving semantics, cache behavior, conformance and operational tooling.

The strongest maturity signals are:

- **Multiple accelerator families:** native NVIDIA CUDA, AMD HIP (including documented gfx1151/RDNA paths), and Intel XPU conformance work. The website also advertises AMD HIP/Vulkan, but LEONES should distinguish the advertised backend label from each model/OS combination actually qualified in release documentation.
- **Native runtime:** a Zig engine that reads supported checkpoints and runs Metal/CUDA kernels directly. The Linux release archive has an explicit runtime/driver floor: glibc 2.28+, NVIDIA R580+ and CUDA 13.0 for the CUDA build.
- **Serving interoperability:** OpenAI-compatible and Anthropic-compatible APIs, with chat/completions, Responses, WebSocket Responses, tool calls, local Unix-socket serving and API authentication options documented across the project.
- **Beyond text generation:** model-dependent image input, an image-generation endpoint for engines exposing that capability, OCR/image-chat paths, and selected embeddings/reranking/decision endpoints. These capabilities are family- and backend-specific, not universal features of every checkpoint.
- **Speculative decoding:** MTP and external drafters such as DFlash2 and DSpine-b16 on explicitly supported family/backend combinations. Drafting remains opt-in where documented; it must not be assumed from a cached drafter or a model name.
- **Prompt-state reuse:** in-memory and disk-backed prompt retention, conversation resume and cache admission work designed for multi-agent use. Version 1.2.6 reported large follow-up first-token improvements at 8–16 concurrent agents while preserving replies in its named test setups.
- **Concurrency and scheduling:** parallel request admission, shared rounds, prompt/decode scheduling, cache budgeting and model-specific memory planning are now treated as engine-level behavior.
- **Conformance and reproducibility:** family-specific conformance profiles, exactness gates, benchmark receipts and a benchmark inspection workflow. The public benchmark board distinguishes receipt versions and warns that community submissions are not independently hardware-verified.
- **Operator surface:** TensorFold Web provides a local model-selection and chat interface; the project also has a separate desktop workspace and a separate fleet/enterprise project, TensorFold Starlight. These are related products, not all one interchangeable runtime package.

### Release 1.2.7: concrete evidence, not a generic compatibility claim

The 1.2.7 release (11 November 2026) adds, among other changes:

- WebSocket transport for the Responses API;
- LightOnOCR-3 0.8B and 4B image-chat serving on CUDA from publisher BF16 weights;
- an XPU conformance profile for Qwen3.8-27B on Intel Arc Pro B70;
- prompt-cache visibility in the dashboard and `/stats`;
- long-conversation resume improvements, including a reported M3 Ultra case where a 34K history resumes at the end of the previous turn and first-token latency falls from about 85 seconds to about 0.3 seconds;
- CUDA, HIP and Metal performance/memory changes, with output-equivalence claims stated per measurement rather than generalized.

The preceding 1.2.6 release adds CUDA DSpine-b16 drafting for Qwen3.8-27B (opt-in), a local owner-only Unix socket, `POST /v1/images/generations` for engines with image capability, and a substantial prompt-cache/concurrent-agent improvement. Its named GB10 and Apple Silicon measurements are release-specific, not a universal speed multiplier.

Headline figures must always retain their model, backend, hardware, release, context, concurrency and decoding conditions. For example, the 1.2.7 release reports specific Metal, CUDA and HIP results; these are not directly comparable to one another and are not LEONES benchmarks.

### What this means for ODS

ODS has now developed a practical integration seam that did not exist in the earlier assessment:

1. The ODS provider-mode contract explicitly permits an owner-run external OpenAI-compatible server in local mode, with external URL, model ID and provider identity represented in configuration.
2. The contract requires an adapter boundary for URL normalization, authentication, health/version/model discovery, chat and optional capability probes, error classification and recovery hints.
3. ODS 2.6.0 release notes describe stable Model Switchboard routing for local applications, context propagation, model identity validation and rollback-aware runtime swaps.
4. ODS V3 provides an extension-recipe workflow and a broader operator surface, but a recipe or catalog entry is not proof that a provider has been qualified.

This makes a staged integration realistic:

**Stage A — external provider qualification.** Run TensorFold as an owner-managed service and connect it through ODS's existing external OpenAI-compatible provider mode. Keep the existing ODS runtime and installation untouched. Validate endpoint, auth, model identity, chat, streaming/tool calls and the selected profile's required optional capabilities.

**Stage B — first-class provider adapter.** If Stage A passes, add a small TensorFold-specific adapter/profile rather than scattering TensorFold conditionals across installer, dashboard and Compose code. The adapter should query the installed engine's `capabilities --json`, pin or validate its version, expose only capabilities proven for the selected model/backend, and provide bounded health/model/completion probes.

**Stage C — optional managed service/extension.** Only after lifecycle and security tests should ODS offer an opt-in managed service. Pin release archive/checksum or image digest, model revision, runtime flags and resource plan. Do not make TensorFold a default dependency and do not silently download checkpoints.

### ODS capability mapping

| ODS contract area | TensorFold fit | Qualification still required |
|---|---|---|
| Local external provider | Strong: OpenAI-compatible API and configurable model ID | Host/container URL reachability, auth, lifecycle ownership |
| Model Switchboard | Strong architectural fit for a stable ODS model alias | Swap, identity, context propagation, rollback and consumer tests |
| Chat/completions/streaming | Documented | ODS client compatibility, cancellation, errors and long streams |
| Tool/function calls | Documented on supported paths | Exact tool schema/streaming conformance for each chosen model |
| Vision/OCR | Available for selected family/backend combinations | Per-checkpoint image tower, processor, VRAM and endpoint tests |
| Image generation | Endpoint exists when the engine exposes image capability | ODS product contract and supported model/backend matrix |
| Embeddings/rerank | Selected endpoints/families exist | Provider contract and ODS RAG consumer compatibility |
| Metrics/stats | Engine dashboard, `/stats`, `/v1/load` and memory endpoints vary by release | ODS telemetry adapter and explicit unsupported states |
| Install/update/rollback | Native archive and checksum workflow documented | ODS-managed lifecycle, pinning, rollback and security review |

### Hardware qualification: RTX 3050 4 GB remains an open gate

TensorFold's current CUDA release has fatbins for sm_80, sm_86, sm_120 and sm_121. The runbook records selected model checks on an RTX 3090 (sm_86), and the project explicitly warns that one sm_86 result does not qualify every GPU of that compute-capability class.

This is meaningful progress for the architecture family, but **it does not qualify the MSI RTX 3050 Laptop GPU with 4 GB VRAM**. The published small Qwen3.5-2B quick-start path is checked on Mac/GB10, not specifically on a 4 GB RTX 3050. Large published CUDA workloads use GB10, RTX 3090 or RTX PRO 6000-class hardware and must not be projected onto the laptop.

For LEONES, record the following as separate facts:

- CUDA backend and sm_86 kernel images: documented;
- selected sm_86 model execution: documented on RTX 3090;
- RTX 3050 4 GB full-checkpoint admission: not established;
- RTX 3050 throughput, peak VRAM and sustained stability: not measured;
- ODS + TensorFold end-to-end integration on the MSI: not measured.

The next hardware experiment should begin with `capabilities --json`, `info` memory-floor inspection and the smallest explicitly supported CUDA checkpoint. Only then should a controlled pull/serve test be proposed. A 4-bit file smaller than 4 GB is not enough: CUDA context, weights, temporary buffers, KV/prompt cache, drafter and other allocations all count.

### P0 execution plan and acceptance gates

P0 means that TensorFold deserves an active, bounded integration track. It does not authorize installation or replacement of the current ODS runtime.

1. **Freeze upstream evidence:** record TensorFold 1.2.7 release/tag/commit, archive checksum, RUNBOOK, model qualification table and exact checkpoint revisions.
2. **Capability discovery:** capture `tensorfold capabilities --json`, version, backend, family, format and model memory floor.
3. **Hardware admission:** collect GPU compute capability, VRAM, driver, CUDA runtime, RAM, free disk, container access and context/cache budget.
4. **External-provider smoke test:** use ODS external-provider mode without changing the managed ODS engine; verify health, model list, one completion, streaming, auth and tool calls.
5. **Consumer conformance:** test LiteLLM/Model Switchboard and each enabled ODS consumer; verify identity, context, cancellation, error propagation and rollback.
6. **Optional capabilities:** test vision/OCR, embeddings, rerank and image generation only when the selected model/backend advertises them.
7. **Benchmark:** capture TTFT, prompt tok/s, decode tok/s, concurrency, prompt-resume latency, peak VRAM/RAM, load time and stability; compare only against the same checkpoint/settings on the same hardware.
8. **Security/lifecycle:** verify loopback binding, API key handling, owner-only Unix socket where used, pinned artifacts, update/rollback and no implicit model download.
9. **Promotion review:** retain P0 only while active qualification is underway; once a tested provider adapter lands, classify by integration status and ongoing strategic value rather than upstream excitement.

### Evidence and scope rules

Use four distinct labels:

- **UPSTREAM-REPORTED** — a release note, recipe or benchmark published by TensorFold;
- **SOURCE-OBSERVED** — capability/flag/implementation visible in a pinned source or release archive;
- **LEONES-MEASURED** — independently reproduced on named LEONES hardware;
- **ODS-QUALIFIED** — the provider passes ODS adapter, consumer, lifecycle and rollback gates.

Do not collapse these categories. A TensorFold benchmark is not automatically a LEONES measurement; a successful standalone TensorFold server is not automatically an ODS-qualified provider; and an ODS extension recipe is not a complete provider integration.

### Decision

**Promote TensorFold from P1 to P0 — strategic integration / active qualification.** The promotion is justified by its current multi-accelerator native engine, expanding model-family coverage, mature OpenAI/Anthropic serving surface, prompt-state and concurrency engineering, conformance tooling, benchmark receipts and a direct fit with ODS's external-provider/Model Switchboard architecture.

The immediate integration target is **not** “replace llama-server” and not “enable TensorFold by default”. It is a separately owned TensorFold process connected through ODS's external-provider contract, with a future first-class adapter conditional on conformance. RTX 3050 4 GB qualification remains a separate unresolved hardware gate.

### P1 — high priority

| Project | Profile | Report |
|---|---|---|
| MoE-Infinity | MoE CUDA + RAM/SSD offload + serving | [MoE-Infinity](moe-infinity/README-eng.mkd) |
| ramvamp | CPU/NVMe MoE streaming | [ramvamp](ramvamp/README-eng.mkd) |
| Edge0 | SSD streaming + routing prediction | [Edge0](edge0/README-eng.mkd) |
| FATE | expert prediction + async prefetch | [FATE](fate/README-eng.mkd) |
| MoE-Lens | hardware/performance modeling | [MoE-Lens](moe-lens/README-eng.mkd) |
| HybriMoE | CPU/GPU scheduling + cache | [HybriMoE](hybrimoe/README-eng.mkd) |
| BigMoeLLM | MoE > VRAM, mmap/paging | [BigMoeLLM](bigmoellm/README-eng.mkd) |
| FrankenMoE-CUDA | NVMe→RAM→VRAM expert tiers | [FrankenMoE-CUDA](frankenmoe-cuda/README-eng.mkd) |
| llama.cpp expert paging PoC | possible upstream evolution | [llama.cpp expert paging](llama-cpp-expert-paging/README-eng.mkd) |
| LocalAI | multi-backend architecture | [LocalAI](localai/README-eng.mkd) |
| llama-cpp-studio | multi-runtime control plane | [llama-cpp-studio](llama-cpp-studio/README-eng.mkd) |
| WARP | MoE NVMe paging | [WARP](WARP/README-eng.mkd) |

### P2 — candidates / research

| Project | Profile | Report |
|---|---|---|
| SSD MoE | SSD streaming | [ssdmoe](ssdmoe/README-eng.mkd) |
| ExpertFlow | predictive expert caching | [ExpertFlow](expertflow/README-eng.mkd) |
| moe-hotcache | hot-expert cache on llama.cpp | [moe-hotcache](moe-hotcache/README-eng.mkd) |
| vllm-moe | CPU offload + GPU prefetch | [vllm-moe](vllm-moe/README-eng.mkd) |
| vLLM RFC | MoE CPU offload design | [RFC](vllm-cpu-offload-rfc/README-eng.mkd) |
| DynaExQ | dynamic precision/residency | [DynaExQ](dynaexq/README-eng.mkd) |
| MoE CPU/GPU Collaborative Inference | CPU/GPU caching | [CPU/GPU](moe-cpu-gpu-collaborative-inference/README-eng.mkd) |
| local-llm-npu | Intel NPU/OpenVINO | [NPU](local-llm-npu/README-eng.mkd) |
| Atomic-Chat | local multi-engine | [Atomic-Chat](atomic-chat/README-eng.mkd) |
| llama.cpp.35B.moe | MoE CUDA optimizations | [fork](llama-cpp-35b-moe/README-eng.mkd) |
| moe-ssd-streaming-windows | Windows/NVIDIA SSD streaming | [Windows](moe-ssd-streaming-windows/README-eng.mkd) |
| expert-streaming-engine | expert streaming | [engine](expert-streaming-engine/README-eng.mkd) |
| ds4-ssd | SSD/weight streaming | [ds4-ssd](ds4-ssd/README-eng.mkd) |
| moe-edge-inference | MoE edge | [edge](moe-edge-inference/README-eng.mkd) |
| moe-stream | MoE streaming | [stream](moe-stream/README-eng.mkd) |
| HOBBIT | mixed-precision expert cache | [HOBBIT](hobbit/README-eng.mkd) |
| MoE-Gen | single-GPU MoE throughput | [MoE-Gen](moe-gen/README-eng.mkd) |
| Fiddler | CPU/GPU collaborative inference | [Fiddler](fiddler/README-eng.mkd) |

### P3 — radar

| Project | Profile | Report |
|---|---|---|
| oBeaver | local/platform-aware toolkit | [oBeaver](obeaver/README-eng.mkd) |
| Forge | general Rust/CUDA runtime | [Forge](forge/README-eng.mkd) |
| BaseRT | Apple/NVIDIA-specific runtime | [BaseRT](basert/README-eng.mkd) |
| ES-MoE | training offload | [ES-MoE](es-moe/README-eng.mkd) |
| weight-streaming | weight streaming | [weight-streaming](weight-streaming/README-eng.mkd) |

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


### Additional Experimental Integrations

| Project | Profile | Report |
|---|---|---|
| AirLLM | layer/expert streaming for Hugging Face models | [AirLLM](airllm/README-eng.mkd) |
| Companion Hub | local application control/orchestration reference | [Companion Hub](companion-hub/README-eng.mkd) |
| Kimi K3 in C | specialized runtime with model streaming and expert caching | [Kimi K3 in C](kimi-k3-in-c/README-eng.mkd) |
| LaptopLLM | layer-streaming and laptop UX reference | [LaptopLLM](laptopllm/README-eng.mkd) |


## Hybrid AI cost awareness

Research on informing users of projected and actual spend when ODS uses remote/proprietary AI within hybrid mode:

- [Cost Awareness for Hybrid AI — English](LLM-COST-AWARENESS-eng.md)
- [Cost awareness para IA híbrida — Español](LLM-COST-AWARENESS-ES.md)

The research proposes a **Cost Envelope + Cost Ledger**, including price provenance, pre-request estimates, actual cost, cache/reasoning, retries/fallbacks, budgets, and strict separation between provider spend and local operational cost.
\n## External experimental evidence: Bonsai 2 / small-GPU

The sudoingX Bonsai 2 research is incorporated as an **external experimental evidence source**, not as a dependency. It reinforces a key LEONES + ODS architectural change: move from asking “which model fits my GPU?” to determining “which inference configuration produces the best real capability on my GPU?”.

The decision unit becomes the **Inference Profile**: hardware + model + quantization + runtime + kernel + context + KV + MTP + vision + flags + measurements.

- [Bonsai 2 27B / small-GPU — external evidence](Bonsai2-Small-GPU-EXTERNAL-EVIDENCE-eng.md)
- [Bonsai 2 27B / small-GPU — evidencia externa](Bonsai2-Small-GPU-EXTERNAL-EVIDENCE.md)

Published results are classified as EXTERNAL / COMMUNITY / MEASURED / NOT_REPRODUCED_BY_LEONES. Only controlled physical reproduction can become LEONES MEASURED evidence.



### Primary sources reviewed — 2026-11-13

- [TensorFold 1.2.7 release notes](https://github.com/ashhart/TensorFold/releases/tag/v1.2.7)
- [TensorFold release history](https://github.com/ashhart/TensorFold/releases)
- [TensorFold native runtime README and qualified-model matrix](https://github.com/ashhart/TensorFold/blob/main/README.md)
- [TensorFold Linux/CUDA runbook](https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md)
- [TensorFold official site](https://tensorfold.dev/)
- [TensorFold command-line and serving guide](https://tensorfold.dev/guide)
- [ODS engine provider modes contract](https://github.com/Osmantic/ODS/blob/main/ods/docs/ENGINE-PROVIDER-MODES.md)
- [ODS backend runtime contract](https://github.com/Osmantic/ODS/blob/main/ods/docs/BACKEND-CONTRACT.md)
- [ODS extension authoring and managed installation](https://github.com/Osmantic/ODS/blob/main/ods/docs/EXTENSIONS.md)
- [ODS bundled extension catalog](https://github.com/Osmantic/ODS/blob/main/ods/extensions/CATALOG.md)
- [ODS 3.0.0 changelog and 2.6.0 Model Switchboard notes](https://github.com/Osmantic/ODS/blob/main/ods/CHANGELOG.md)
- [ODS V3 project status and release boundaries](https://github.com/Osmantic/ODS)
