# Complete LEONES + ODS Architecture
## Current State + Proposed Evolution

> Reference architecture document for the joint evolution of LEONES and ODS.
> All diagrams in this document are expressed in ASCII so they remain readable from
> terminals, GitHub, TUI, SSH, and tools without graphical rendering.

Reference date: 2026-10-02

---

## 0. Idea central

```text
                         LEONES + ODS
                         ============

                 LEONES DECIDE Y DEMUESTRA
                 ODS EJECUTA Y OPERA

        +----------------------+     +----------------------+
        |        LEONES        |     |         ODS          |
        |----------------------|     |----------------------|
        | storagever             |     | install              |
        | profile              |     | configure            |
        | candidates           |     | serve                |
        | recommendation       |     | route                |
        | human choice         | --> | execute              |
        | consent              |     | orchestrate          |
        | install/prepare      |     | observe              |
        | benchmark            | <-- | benchmark hooks      |
        | evidence             |     | artifacts            |
        +----------------------+     +----------------------+
                    |                         |
                    +-----------+-------------+
                                |
                                v
                         MEASURED EVIDENCE
```

LEONES no debe convertirse en el runtime de inferencia.

ODS no debe convertirse en el sistema que decide por el usuario qué debe elegir.

La separación propuesta es:

```text
 LEONES
   |
   | profile + candidates + evidence
   v
 ODS
   |
   | execution strategy
   v
 providers / runtimes / services
   |
   | physical execution
   v
 benchmark
   |
   v
 LEONES
```

---

# 1. LEONES — complete architecture

## 1.1 Current layers

```text
+==============================================================================+
|                                  LEONES                                      |
|                    Local Ecosystem of Open Neural Expert Systems             |
+==============================================================================+
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                         USER / HUMAN AUTHORITY                         |  |
|  |                                                                        |  |
|  |  language                                                               |  |
|  |  purpose(s)                                                         |  |
|  |  selected model                                                       |  |
|  |  selected stack                                                        |  |
|  |  consent                                                       |  |
|  |  installation / uninstallation                                         |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                           MACHINE DISCOVERY                            |  |
|  |                                                                        |  |
|  |  CPU · RAM · GPU · VRAM · storage · OS · drivers · Docker               |  |
|  |  CUDA · ROCm · Metal · NPU · Vulkan · runtimes existentes             |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                           INVENTORY / STATE                            |  |
|  |                                                                        |  |
|  |  FitLLM/LLMFit · ODS · Magnitude · LLMs · agents · harnesses           |  |
|  |  versions · installation · availability · provenance               |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                        PURPOSE / WORKLOAD PROFILE                      |  |
|  |                                                                        |  |
|  |  chat · coding · agent · RAG · multimodal · batch · training          |  |
|  |  latency · quality · context · privacy · cost · offline · throughput   |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                        MODEL DISCOVERY                                 |  |
|  |                                                                        |  |
|  |  Hugging Face · Artificial Analysis · model metadata                   |  |
|  |  architecture · parameters · active params · quantization              |  |
|  |  context · modality · MoE experts · routing                             |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                         FITLLM / LLMFIT                                |  |
|  |                                                                        |  |
|  |  hardware-aware preselection                                           |  |
|  |  up to 3 candidates                                                     |  |
|  |  ESTIMATED only                                                        |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                          HUMAN SELECTION                                |  |
|  |                                                                        |  |
|  |  LEONES may recommend.                                                 |  |
|  |  USER chooses.                                                         |  |
|  |  No recommendation is a measured result.                               |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                         STACK MANAGEMENT                                |  |
|  |                                                                        |  |
|  |  install selected model / ODS / Magnitude / other components            |  |
|  |  uninstall independently                                               |  |
|  |  explicit consent for large downloads                                  |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                         RUNTIME / EXECUTION                             |  |
|  |                                                                        |  |
|  |  ODS · Magnitude · direct runtime · external provider                  |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                           A01 BENCHMARK                                |  |
|  |                                                                        |  |
|  |  physical execution · timing · throughput · resources · result         |  |
|  +-----------------------------------+------------------------------------+ |
|                                      |                                      |
|                                      v                                      |
|  +------------------------------------------------------------------------+ |
|  |                             EVIDENCE                                    | |
|  |                                                                        | |
|  |  ESTIMATED != REPORTED != OBSERVED != MEASURED                         | |
|  +------------------------------------------------------------------------+ |
+==============================================================================+
```

---

# 2. LEONES — current RC4 flow

```text
                              +-----------+
                              |  LANGUAGE   |
                              +-----+-----+
                                    |
                                    v
                         +----------------------+
                         | MACHINE STATE   |
                         +----------+-----------+
                                    |
                    +---------------+----------------+
                    |               |                |
                    v               v                v
                  CPU/RAM        GPU/VRAM        SOFTWARE
                    |               |                |
                    +---------------+----------------+
                                    |
                                    v
                         +----------------------+
                         | COMPONENT INVENTORY  |
                         +----------+-----------+
                                    |
            +-----------------------+-------------------------+
            |                       |                         |
            v                       v                         v
         FitLLM                    ODS                    Magnitude
            |                       |                         |
            +-----------------------+-------------------------+
                                    |
                                    v
                         +----------------------+
                         | PURPOSE(S)           |
                         | multi-select         |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | HF + Artificial      |
                         | Analysis             |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | FITLLM PRESELECTION  |
                         | <= 3 candidates      |
                         | ESTIMATED            |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | HUMAN SELECTION      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | STACK MANAGEMENT     |
                         +----------+-----------+
                                    |
                   +----------------+----------------+
                   |                |                |
                   v                v                v
                MODEL             ODS            MAGNITUDE
                   |                |                |
                   +----------------+----------------+
                                    |
                                    v
                         +----------------------+
                         | RUNTIME              |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | A01 BENCHMARK        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | MEASURED EVIDENCE    |
                         +----------------------+
```

---

# 3. LEONES — future components

Evolution is not about adding tools without limit. It is about adding capabilities around a decision-and-evidence contract.

```text
+============================================================================+
|                           FUTURE LEONES                                    |
+============================================================================+
|                                                                            |
|  DISCOVERY                                                                |
|  +---------------------------------------------------------------------+   |
|  | hardware · OS · drivers · accelerators · storage · network          |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  MODEL INTELLIGENCE                                                       |
|  +---------------------------------------------------------------------+   |
|  | architecture · size · active params · MoE · quantization            |   |
|  | context · modality · KV cache · routing · license                    |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  PROVIDER INTELLIGENCE                                                    |
|  +---------------------------------------------------------------------+   |
|  | inference runtimes · post-training · orchestration · agents          |   |
|  | local · remote · cloud · hybrid · API compatibility                  |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  CAPABILITY MATCHING                                                       |
|  +---------------------------------------------------------------------+   |
|  | model <-> hardware <-> runtime <-> workload <-> policy               |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  CONSENT / GOVERNANCE                                                      |
|  +---------------------------------------------------------------------+   |
|  | downloads · network · credentials · data · skills · remote execution  |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  EXPERIMENT RUNNER                                                         |
|  +---------------------------------------------------------------------+   |
|  | install -> configure -> execute -> benchmark -> collect              |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  EVIDENCE ENGINE                                                           |
|  +---------------------------------------------------------------------+   |
|  | estimated / reported / observed / measured / reproduced              |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  MANADA                                                                    |
|  +---------------------------------------------------------------------+   |
|  | aggregate evidence across machines / models / providers              |   |
|  | without pretending measurements are interchangeable                   |   |
|  +---------------------------------------------------------------------+   |
+============================================================================+
```

---

# 4. ODS — architecture actual completa

La architecture actual de ODS V3 se organiza alrededor de servicios Docker, overlays por plataforma/GPU, un registro de servicios y un CLI que ensambla y opera el stack. The official documentation describes inference, UI, gateway, voice, search, agents, RAG, media generation, privacy/observability, and development services. citeturn0search0turn0search1

```text
+==============================================================================+
|                                    ODS                                       |
|                         OSMANTIC DEPLOYMENT SYSTEM                          |
+==============================================================================+
|                                                                              |
|                           USER / CLIENTS                                    |
|                                                                              |
|   Browser       OpenAI clients       API clients       Agents                |
|      |                 |                  |               |                  |
|      +-----------------+------------------+---------------+                  |
|                                |                                             |
|                                v                                             |
|                        +---------------+                                     |
|                        | ODS PROXY     |                                     |
|                        | / ingress     |                                     |
|                        +-------+-------+                                     |
|                                |                                             |
|              +-----------------+------------------+                           |
|              |                                    |                           |
|              v                                    v                           |
|      +---------------+                    +---------------+                   |
|      | Open WebUI    |                    | Dashboard     |                   |
|      | :3000         |                    | :3001         |                   |
|      +-------+-------+                    +-------+-------+                   |
|              |                                    |                           |
|              |                              +-----v------+                    |
|              |                              | Dashboard  |                    |
|              |                              | API :3002  |                    |
|              |                              +------------+                    |
|              |                                                                |
|              v                                                                |
|      +-----------------------+                                                |
|      | LiteLLM :4000         |                                                |
|      | OpenAI-compatible     |                                                |
|      | local/cloud/hybrid    |                                                |
|      +----------+------------+                                                |
|                 |                                                             |
|        +--------+-----------------------+                                     |
|        |                                |                                     |
|        v                                v                                     |
| +-------------+                  +-------------+                              |
| | LOCAL LLM   |                  | CLOUD /     |                              |
| | llama-server|                  | REMOTE APIs |                              |
| | :8080       |                  | optional    |                              |
| +------+------+                  +-------------+                              |
|        |                                                                       |
|        v                                                                       |
|   GGUF MODEL                                                                  |
|                                                                              |
+==============================================================================+
```

---

# 5. ODS — servicios actuales por dominio

## 5.1 Inferencia y API

```text
+-----------------------------------------------------------------------+
| INFERENCE / API                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  llama-server                                                        |
|      |                                                                |
|      +--> LLM inference                                               |
|      +--> OpenAI-compatible API                                       |
|      +--> GGUF                                                        |
|      +--> GPU/CPU backend                                             |
|                                                                       |
|  LiteLLM                                                              |
|      |                                                                |
|      +--> OpenAI-compatible gateway                                   |
|      +--> local mode                                                  |
|      +--> cloud mode                                                  |
|      +--> hybrid mode                                                 |
|      +--> provider routing                                            |
|                                                                       |
+-----------------------------------------------------------------------+
```

ODS V3 documenta llama-server como motor base y LiteLLM como gateway que permite local, cloud y hybrid. citeturn0search0turn0search6

---

## 5.2 Chat y control

```text
+-----------------------------------------------------------------------+
| USER EXPERIENCE                                                       |
+-----------------------------------------------------------------------+
|                                                                       |
| Open WebUI :3000                                                      |
|   |                                                                   |
|   +--> chat                                                           |
|   +--> history                                                        |
|   +--> document upload                                                |
|   +--> web search                                                     |
|   +--> voice integration                                              |
|   +--> image generation integration                                   |
|                                                                       |
| Dashboard :3001                                                       |
|   |                                                                   |
|   +--> setup                                                          |
|   +--> service health                                                 |
|   +--> GPU status                                                     |
|   +--> model management                                                |
|   +--> feature storagevery                                               |
|   +--> extensions                                                      |
|                                                                       |
| Dashboard API :3002                                                   |
|   |                                                                   |
|   +--> setup                                                           |
|   +--> features                                                        |
|   +--> agents                                                          |
|   +--> privacy                                                         |
|   +--> workflows                                                       |
|   +--> updates                                                         |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

## 5.3 Voz

```text
+-----------------------------------------------------------------------+
| VOICE                                                                 |
+-----------------------------------------------------------------------+
|                                                                       |
| microphone                                                            |
|     |                                                                 |
|     v                                                                 |
|  Whisper :9000                                                        |
|     |                                                                 |
|     | speech -> text                                                  |
|     v                                                                 |
|  LLM / Agent                                                          |
|     |                                                                 |
|     | text                                                            |
|     v                                                                 |
|  Kokoro / TTS :8880                                                   |
|     |                                                                 |
|     v                                                                 |
|  audio                                                                 |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

## 5.4 RAG y búsqueda

```text
+-----------------------------------------------------------------------+
| SEARCH / RAG                                                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  Documents                                                            |
|      |                                                                |
|      v                                                                |
|  embeddings / TEI :8090                                               |
|      |                                                                |
|      v                                                                |
|  Qdrant :6333                                                         |
|      |                                                                |
|      | vector retrieval                                                |
|      v                                                                |
|  context                                                              |
|      |                                                                |
|      +----------------------------+                                   |
|                                   |                                   |
|                                   v                                   |
|                              LLM / Agent                              |
|                                                                       |
|  SearXNG :8888                                                        |
|      |                                                                |
|      +--> privacy-respecting metasearch                               |
|      |                                                                |
|      v                                                                |
|  Perplexica :3004                                                     |
|      |                                                                |
|      +--> deep research                                                |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

## 5.5 Agentes y automatización

```text
+-----------------------------------------------------------------------+
| AGENTS / AUTOMATION                                                   |
+-----------------------------------------------------------------------+
|                                                                       |
|                           USER                                        |
|                             |                                         |
|                             v                                         |
|                    +------------------+                                |
|                    | Hermes Proxy     |                                |
|                    | :9120            |                                |
|                    +--------+---------+                                |
|                             |                                          |
|                             v                                          |
|                    +------------------+                                 |
|                    | Hermes           |                                 |
|                    | :9119 internal   |                                 |
|                    +--------+---------+                                 |
|                             |                                          |
|             +---------------+---------------+                          |
|             |               |               |                          |
|             v               v               v                          |
|          search           tools          LLM                           |
|                                                                       |
|  APE :7890                                                            |
|      +--> agent policy                                                |
|      +--> allow/deny                                                  |
|      +--> audit                                                       |
|                                                                       |
|  n8n :5678                                                            |
|      +--> visual workflows                                             |
|      +--> automation                                                  |
|                                                                       |
|  OpenClaw :7860                                                      |
|      +--> legacy/deprecated optional agent                            |
|                                                                       |
+-----------------------------------------------------------------------+
```

La documentación actual identifica Hermes como agente general por defecto, APE como capa de políticas/auditoría, n8n para workflows y OpenClaw como agente legado/deprecado. citeturn0search0turn0search4

---

## 5.6 Generación multimedia

```text
+-----------------------------------------------------------------------+
| MEDIA                                                                 |
+-----------------------------------------------------------------------+
|                                                                       |
| prompt                                                                |
|   |                                                                   |
|   v                                                                   |
| ComfyUI :8188                                                         |
|   |                                                                   |
|   +--> SDXL Lightning                                                 |
|   +--> image generation                                               |
|   |                                                                   |
|   v                                                                   |
| image                                                                 |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

## 5.7 Privacidad, observabilidad y operaciones

```text
+-----------------------------------------------------------------------+
| PRIVACY / OBSERVABILITY                                               |
+-----------------------------------------------------------------------+
|                                                                       |
| privacy-shield :8085                                                  |
|   +--> PII detection                                                  |
|   +--> scrubbing                                                      |
|                                                                       |
| token-spy :3005                                                       |
|   +--> token usage                                                    |
|   +--> cost tracking                                                  |
|                                                                       |
| Langfuse :3006                                                        |
|   +--> tracing                                                        |
|   +--> observability                                                  |
|                                                                       |
| Docker / health checks                                                |
|   +--> service health                                                 |
|   +--> dependencies                                                   |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

## 5.8 Desarrollo

```text
+-----------------------------------------------------------------------+
| DEVELOPMENT                                                           |
+-----------------------------------------------------------------------+
|                                                                       |
| OpenCode :3003                                                        |
|   +--> browser-based AI coding IDE                                    |
|                                                                       |
| ODS CLI                                                               |
|   +--> status                                                         |
|   +--> list                                                           |
|   +--> logs                                                           |
|   +--> start / stop                                                   |
|   +--> restart                                                        |
|   +--> mode local/cloud/hybrid                                        |
|   +--> model swap                                                     |
|   +--> enable / disable extension                                     |
|   +--> config                                                         |
|   +--> presets                                                        |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

# 6. ODS — instalador y sistema de extensiones

```text
+==============================================================================+
|                         ODS INSTALL / BOOTSTRAP                              |
+==============================================================================+
|                                                                              |
|  01 PRE-FLIGHT                                                              |
|       |                                                                      |
|       v                                                                      |
|  02 DETECTION                                                               |
|       |                                                                      |
|       v                                                                      |
|  03 FEATURES                                                                |
|       |                                                                      |
|       v                                                                      |
|  04 REQUIREMENTS                                                            |
|       |                                                                      |
|       v                                                                      |
|  05 DOCKER                                                                  |
|       |                                                                      |
|       v                                                                      |
|  06 DIRECTORIES / ENV                                                       |
|       |                                                                      |
|       v                                                                      |
|  07 DEVTOOLS                                                                |
|       |                                                                      |
|       v                                                                      |
|  08 IMAGES                                                                  |
|       |                                                                      |
|       v                                                                      |
|  09 OFFLINE                                                                 |
|       |                                                                      |
|       v                                                                      |
|  10 PLATFORM TUNING                                                         |
|       |                                                                      |
|       v                                                                      |
|  11 SERVICES                                                                |
|       |                                                                      |
|       v                                                                      |
|  12 HEALTH                                                                  |
|       |                                                                      |
|       v                                                                      |
|  13 SUMMARY                                                                 |
|                                                                              |
+==============================================================================+
```

ODS utiliza un registro de servicios y manifests. Una extensión puede aportar metadatos, health checks, puertos, features y composición Docker; el sistema puede descubrirlas desde el dashboard, CLI y stack de Compose. citeturn0search3turn0search0

```text
extensions/services/<service>/
        |
        +-- manifest.yaml
        |      |
        |      +-- id
        |      +-- port
        |      +-- health
        |      +-- category
        |      +-- GPU backends
        |      +-- dependencies
        |      +-- features
        |
        +-- compose.yaml
        |
        +-- compose.nvidia.yaml
        |
        +-- compose.amd.yaml
        |
        +-- Dockerfile
        |
        v
 service registry
        |
        +-------------------+
        |                   |
        v                   v
      CLI              Dashboard
        |                   |
        +---------+---------+
                  |
                  v
           Compose resolver
                  |
                  v
              Docker
```

---

# 7. ODS — matriz de ejecución por plataforma

```text
+============================================================================+
|                         ODS PLATFORM BACKENDS                             |
+============================================================================+
|                                                                            |
| NVIDIA                                                                     |
|   GPU --> CUDA --> llama-server                                            |
|                                                                            |
| AMD                                                                        |
|   GPU/APU --> ROCm/Vulkan/NPU --> Lemonade / selected backend              |
|                                                                            |
| Apple Silicon                                                              |
|   host --> Metal --> native llama-server                                   |
|                                                                            |
| Intel Arc                                                                  |
|   GPU --> SYCL --> experimental backend                                    |
|                                                                            |
| CPU                                                                        |
|   CPU --> llama.cpp --> llama-server                                       |
|                                                                            |
| Cloud / Hybrid                                                             |
|   ODS --> LiteLLM --> remote provider                                      |
|                                                                            |
+============================================================================+
```

---

# 8. ODS — la architecture futura que resulta de toda la investigación

La investigación de runtimes cambia el centro de gravedad.

Actualmente:

```text
             USER
               |
               v
             ODS
               |
               v
         llama-server
               |
               v
             MODEL
```

Evolución propuesta:

```text
                         USER / WORKLOAD
                                |
                                v
                    +-----------------------+
                    | WORKLOAD PROFILE      |
                    +-----------+-----------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
        MODEL PROFILE                     HARDWARE PROFILE
               |                                 |
               +----------------+----------------+
                                |
                                v
                    +-----------------------+
                    | CAPABILITY REGISTRY   |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | STRATEGY OPTIMIZER    |
                    +-----------+-----------+
                                |
                +---------------+---------------+
                |               |               |
                v               v               v
             local           remote          hybrid
                |               |               |
                +---------------+---------------+
                                |
                                v
                    +-----------------------+
                    | EXECUTION FABRIC      |
                    +-----------+-----------+
                                |
          +---------------------+----------------------+
          |                     |                      |
          v                     v                      v
       runtime              capability             provider
          |                     |                      |
          v                     v                      v
      llama.cpp             prefetch              remote API
      vLLM                  caching               cloud LLM
      SGLang               paging
      MoE-Infinity         offload
      ramvamp              precision
      WARP
          |                     |                      |
          +---------------------+----------------------+
                                |
                                v
                    +-----------------------+
                    | UNIFIED ODS API       |
                    +-----------+-----------+
                                |
                                v
                    applications / agents / RAG
```

---

# 9. Motores de inferencia investigados

## 9.1 Runtimes generales

```text
+------------------------------------------------------------------------+
| GENERAL INFERENCE                                                      |
+------------------------------------------------------------------------+
|                                                                        |
| llama.cpp / llama-server                                               |
|   +-- general GGUF inference                                           |
|   +-- ODS current core                                                 |
|                                                                        |
| vLLM                                                                    |
|   +-- high-throughput serving                                          |
|   +-- strong CUDA ecosystem                                            |
|                                                                        |
| SGLang                                                                  |
|   +-- serving / scheduling / optimized inference                       |
|                                                                        |
| LocalAI                                                                  |
|   +-- multi-backend abstraction                                        |
|   +-- useful architectural reference                                   |
|                                                                        |
| llama-cpp-studio                                                        |
|   +-- multi-runtime control-plane reference                            |
|                                                                        |
+------------------------------------------------------------------------+
```

## 9.2 MoE / memory / streaming

```text
+------------------------------------------------------------------------+
| MoE / MEMORY / STREAMING                                               |
+------------------------------------------------------------------------+
|                                                                        |
| MoE-Infinity                                                            |
|   CUDA + RAM/SSD offload + serving                                     |
|                                                                        |
| ramvamp                                                                 |
|   CPU + RAM + NVMe + MoE streaming                                     |
|                                                                        |
| WARP                                                                    |
|   MoE NVMe paging                                                      |
|                                                                        |
| Edge0                                                                   |
|   SSD streaming + routing prediction                                   |
|                                                                        |
| FATE                                                                    |
|   expert prediction + async prefetch                                   |
|                                                                        |
| HOBBIT                                                                  |
|   adaptive prefetch + multidimensional expert cache + mixed precision  |
|                                                                        |
| HybriMoE                                                                |
|   CPU/GPU scheduling + collaboration                                   |
|                                                                        |
| BigMoeLLM                                                              |
|   MoE larger than VRAM + mmap/paging                                   |
|                                                                        |
| FrankenMoE-CUDA                                                         |
|   NVMe -> RAM -> VRAM expert tiers                                     |
|                                                                        |
+------------------------------------------------------------------------+
```

## 9.3 Segunda línea / radar

```text
+------------------------------------------------------------------------+
| P2 / P3 / EXPERIMENTAL                                                 |
+------------------------------------------------------------------------+
|                                                                        |
| SSD MoE              ExpertFlow             moe-hotcache                |
| vllm-moe             vLLM CPU-offload RFC  DynaExQ                     |
| CPU/GPU collaborative inference                                         |
| local-llm-npu        Atomic-Chat           llama.cpp.35B.moe           |
| moe-ssd-streaming-windows                                               |
| expert-streaming-engine                                                  |
| ds4-ssd             moe-edge-inference    moe-stream                  |
| MoE-Gen             Fiddler               oBeaver                     |
| Forge               BaseRT                ES-MoE                      |
| weight-streaming                                                            |
|                                                                        |
+------------------------------------------------------------------------+
```

## 9.4 Experimental integrations

```text
+------------------------------------------------------------------------+
| EXPERIMENTAL                                                            |
+------------------------------------------------------------------------+
|                                                                        |
| AirLLM        -> layer/expert streaming                                |
| TensorFold    -> specialized CUDA/MLX + speculative decoding           |
| Kimi K3 in C  -> model streaming + expert cache                       |
| LaptopLLM     -> layer streaming + laptop UX                          |
| Companion Hub -> local application control/orchestration reference     |
|                                                                        |
+------------------------------------------------------------------------+
```

---

# 10. La pieza que falta: Capability Registry

La investigación apunta a que ODS necesita una descripción estructurada de capacidades.

```text
+============================================================================+
|                         CAPABILITY REGISTRY                               |
+============================================================================+
|                                                                            |
| MODEL                                                                      |
|  |                                                                         |
|  +-- architecture                                                         |
|  +-- dense / MoE                                                          |
|  +-- parameters                                                           |
|  +-- active parameters                                                    |
|  +-- experts / token                                                      |
|  +-- quantization                                                         |
|  +-- context                                                              |
|  +-- modality                                                             |
|  +-- KV-cache                                                             |
|  +-- routing                                                              |
|                                                                            |
| HARDWARE                                                                   |
|  |                                                                         |
|  +-- CPU                                                                    |
|  +-- RAM                                                                    |
|  +-- GPU                                                                    |
|  +-- VRAM                                                                   |
|  +-- CUDA / ROCm / Metal / NPU / Vulkan                                   |
|  +-- PCIe                                                                   |
|  +-- NVMe                                                                   |
|  +-- bandwidth                                                              |
|                                                                            |
| RUNTIME                                                                    |
|  |                                                                         |
|  +-- supported model formats                                               |
|  +-- accelerator                                                           |
|  +-- quantization                                                          |
|  +-- MoE                                                                    |
|  +-- paging                                                                 |
|  +-- offload                                                                |
|  +-- batching                                                               |
|  +-- streaming                                                              |
|  +-- OpenAI API                                                             |
|                                                                            |
| EVIDENCE                                                                   |
|  |                                                                         |
|  +-- reported                                                               |
|  +-- observed                                                               |
|  +-- reproduced                                                             |
|  +-- measured                                                               |
|  +-- environment                                                            |
|  +-- version                                                                |
|                                                                            |
+============================================================================+
```

Esto permite que ODS deje de razonar únicamente en términos de nombres de software.

---

# 11. Execution Strategy — composición de capacidades

```text
                         MODEL REQUEST
                              |
                              v
                    +-------------------+
                    | MODEL ROUTER      |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | EXPERT PREDICTOR   |
                    | FATE / Edge0      |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | PREFETCHER         |
                    | Edge0 / HOBBIT     |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | CACHE MANAGER      |
                    | HOBBIT / hotcache  |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | MEMORY PLACEMENT   |
                    | VRAM / RAM / NVMe  |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | CPU/GPU SCHEDULER  |
                    | HybriMoE           |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | PRECISION POLICY   |
                    | DynaExQ / fallback |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | INFERENCE RUNTIME  |
                    +-------------------+
```

---

# 12. Post-Training — architecture completa

El post-training debe ser un servicio de ODS, no un proceso residente permanente.

```text
+==============================================================================+
|                         ODS POST-TRAINING SERVICE                           |
+==============================================================================+
|                                                                              |
|                          CONTROL PLANE                                      |
|                                                                              |
|  API                                                                       |
|   |                                                                        |
|   +-- create job                                                            |
|   +-- status                                                                 |
|   +-- cancel                                                                 |
|   +-- logs                                                                   |
|   +-- artifacts                                                              |
|   +-- benchmark                                                              |
|                                                                              |
|  SCHEDULER                                                                   |
|   |                                                                        |
|   +-- local                                                                  |
|   +-- remote                                                                 |
|   +-- hybrid                                                                 |
|                                                                              |
|  POLICY                                                                      |
|   |                                                                        |
|   +-- data access                                                            |
|   +-- credentials                                                            |
|   +-- network                                                                |
|   +-- resources                                                              |
|                                                                              |
|  ARTIFACT REGISTRY                                                           |
|                                                                              |
+--------------------------------------+---------------------------------------+
                                       |
                                       v
                         +---------------------------+
                         | JOB CREATED               |
                         +-------------+-------------+
                                       |
                                       v
                         +---------------------------+
                         | PROVIDER SELECTION        |
                         +-------------+-------------+
                                       |
              +------------------------+-------------------------+
              |                        |                         |
              v                        v                         v
       LLaMA-Factory               Axolotl                   Unsloth
              |                        |                         |
              +------------------------+-------------------------+
                                       |
                                       v
                               JOB-SCOPED WORKLOAD
                                       |
                                       v
                            +-----------------------+
                            | TRAIN / ADAPT         |
                            +-----------+-----------+
                                        |
                                        v
                            +-----------------------+
                            | EXPORT ARTIFACT        |
                            +-----------+-----------+
                                        |
                                        v
                            +-----------------------+
                            | VALIDATE / CONVERT     |
                            +-----------+-----------+
                                        |
                                        v
                            +-----------------------+
                            | ODS MODEL REGISTRY     |
                            +-----------+-----------+
                                        |
                                        v
                            +-----------------------+
                            | BENCHMARK              |
                            +-----------+-----------+
                                        |
                                        v
                                  DEPLOY / SERVE
```

---

# 13. Post-training providers investigados

```text
+==============================================================================+
|                           POST-TRAINING FABRIC                              |
+==============================================================================+
|                                                                              |
|                         ODS SERVICE CONTRACT                                 |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                                                                        |  |
|  |  Provider abstraction                                                  |  |
|  |                                                                        |  |
|  +----------------------+----------------------+--------------------------+  |
|                         |                      |                             |
|                         v                      v                             v
|                 LLaMA-Factory             Axolotl                      Unsloth
|                         |                      |                             |
|                         +----------------------+-----------------------------+
|                                                |
|                                                v
|                                      training / adaptation
|                                                |
|                                                v
|                                         artifact
|                                                |
|                         +----------------------+--------------------+
|                         |                                           |
|                         v                                           v
|                     adapter                                  merged model
|                         |                                           |
|                         +----------------------+--------------------+
|                                                |
|                                                v
|                                         conversion
|                                                |
|                                                v
|                                      ODS Model Registry
|                                                |
|                                                v
|                                          inference
|                                                                              |
+==============================================================================+
```

---

# 14. TangleML — orquestación

TangleML no debería ser confundido con el runtime de inferencia ni con el provider de entrenamiento.

```text
                         ODS POST-TRAINING
                                |
                                v
                         +-------------+
                         | TangleML    |
                         | ORCHESTRATOR|
                         +------+------+ 
                                |
              +-----------------+-----------------+
              |                 |                 |
              v                 v                 v
           dataset           training          evaluation
              |                 |                 |
              +-----------------+-----------------+
                                |
                                v
                         artifacts / logs
                                |
                                v
                           ODS registry
```

Roles:

```text
LEONES       = storagevery / decision / evidence
ODS          = execution platform / service boundary
TangleML     = workflow orchestration
LLaMA-Factory= training provider
Axolotl      = training provider
Unsloth      = training provider
runtime      = inference provider
```

---

# 15. Post-training — ciclo de vida del workload

```text
                         NO PENDING JOB
                              |
                              v
                    provider workload = OFF
                              |
                              |
                         JOB CREATED
                              |
                              v
                    +-------------------+
                    | PREPARE           |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | START PROVIDER     |
                    | isolated workload  |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | TRAIN / ADAPT      |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | EXPORT             |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | VALIDATE           |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | CONVERT            |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | REGISTER           |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | BENCHMARK          |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | STOP / REMOVE      |
                    | provider workload  |
                    +---------+---------+
                              |
                              v
                    resources released
                              |
                              v
                    artifacts persist
```

No pending training job should mean no permanent LLaMA-Factory/Axolotl/Unsloth training daemon.

---

# 16. Multi-provider hybrid inference

ODS ya dispone de la idea de local/cloud/hybrid mediante LiteLLM. La evolución propuesta es convertir esa capacidad en una política de ejecución explícita.

```text
                         REQUEST
                            |
                            v
                   +-------------------+
                   | POLICY / ROUTER   |
                   +---------+---------+
                             |
             +---------------+---------------+
             |               |               |
             v               v               v
           LOCAL           REMOTE          HYBRID
             |               |               |
             v               v               v
       llama-server      cloud API       local first
       MoE runtime       free provider   remote fallback
       specialized       paid provider   capability route
             |               |               |
             +---------------+---------------+
                             |
                             v
                         RESPONSE
```

Futuro:

```text
              +--------------------------------------+
              | MULTI-PROVIDER POLICY                |
              +--------------------------------------+
              |                                      |
              | privacy                              |
              | cost                                 |
              | latency                              |
              | availability                         |
              | context                              |
              | model capability                     |
              | provider independence                |
              | offline requirement                  |
              | user consent                         |
              |                                      |
              +------------------+-------------------+
                                 |
                                 v
                         provider selection
```

Free-provider fallback puede ser una opción, pero no debe tratarse como equivalente automático a un runtime local: hay que registrar términos, privacidad, límites, availability y dependencia del proveedor.

---

# 17. ODS + LEONES + post-training + inference

Este es el mapa de extremo a extremo:

```text
+==============================================================================+
|                              HUMAN / USE CASE                               |
+=======================================+======================================+
                                        |
                                        v
+==============================================================================+
|                                  LEONES                                      |
|                                                                              |
|  DISCOVER -> PROFILE -> CANDIDATES -> HUMAN CHOICE -> CONSENT               |
|       |          |             |                 |             |             |
|       v          v             v                 v             v             |
|   hardware     model       providers          stack        permissions      |
|                                                                              |
|                         +----------------------+                             |
|                         | FitLLM / LLMFit      |                             |
|                         | ESTIMATED            |                             |
|                         +----------+-----------+                             |
|                                    |                                         |
|                                    v                                         |
|                         +----------------------+                             |
|                         | selected workload    |                             |
|                         +----------+-----------+                             |
+------------------------------------+-----------------------------------------+
                                     |
                                     v
+==============================================================================+
|                                    ODS                                       |
|                                                                              |
|  +----------------+   +----------------+   +-----------------------------+ |
|  | Dashboard      |   | ODS CLI        |   | API / OpenAI-compatible     | |
|  +-------+--------+   +-------+--------+   +--------------+--------------+ |
|          |                    |                            |                |
|          +--------------------+----------------------------+                |
|                               |                                             |
|                               v                                             |
|                    +--------------------------+                             |
|                    | Capability / Service     |                             |
|                    | Registry                 |                             |
|                    +------------+-------------+                             |
|                                 |                                           |
|                  +--------------+--------------+                            |
|                  |                             |                            |
|                  v                             v                            |
|          INFERENCE FABRIC               POST-TRAINING                       |
|                  |                             |                            |
|       +----------+----------+        +---------+---------+                   |
|       |          |          |        |         |         |                   |
|       v          v          v        v         v         v                   |
|   llama.cpp    vLLM       MoE     LLaMA-F    Axolotl   Unsloth               |
|   llama-server SGLang     Edge0      |         |         |                   |
|                WARP       FATE       +---------+---------+                   |
|                ramvamp    HOBBIT                |                           |
|                ...        HybriMoE              v                           |
|                                      TangleML orchestration                  |
|                                                |                             |
|                                                v                             |
|                                           ARTIFACT                           |
|                                                |                             |
|                                                v                             |
|                                      ODS MODEL REGISTRY                     |
|                                                |                             |
|                                                v                             |
|                                           INFERENCE                          |
|                                                                              |
+----------------------------------------------+-------------------------------+
                                               |
                                               v
+==============================================================================+
|                         ODS SERVICES / APPLICATIONS                          |
|                                                                              |
| Chat · Agents · RAG · Search · Voice · Image · Workflows · Coding · APIs   |
|                                                                              |
+----------------------------------------------+-------------------------------+
                                               |
                                               v
+==============================================================================+
|                                BENCHMARK                                     |
+----------------------------------------------+-------------------------------+
                                               |
                                               v
+==============================================================================+
|                                  LEONES                                      |
|                                                                              |
| OBSERVED / MEASURED / REPRODUCED / EVIDENCE                                |
|                                                                              |
|                 measured result -> MANADA / knowledge base                  |
+==============================================================================+
```

---

# 18. Separación de responsabilidades

```text
+----------------------+----------------------------+-------------------------+
| CAPA                 | RESPONSABILIDAD           | NO DEBE HACER          |
+----------------------+----------------------------+-------------------------+
| LEONES               | decidir con evidencia     | ejecutar como runtime   |
| FitLLM / LLMFit      | preselección ESTIMATED    | producir MEASURED       |
| ODS                  | operar y ejecutar         | sustituir elección     |
| ODS Registry         | capacidades/artifacts    | inventar compatibilidad |
| ODS Scheduler        | recursos/jobs/routes     | ocultar políticas       |
| Inference Provider   | inferencia física         | gobernar LEONES         |
| PT Provider          | entrenamiento físico     | quedar daemon permanente|
| TangleML             | workflow orchestration   | ser inference runtime  |
| Dashboard            | UX/control                | ser fuente de verdad    |
| Benchmark            | medir ejecución           | copiar cifras externas |
| MANADA               | acumular evidencia       | mezclar entornos        |
+----------------------+----------------------------+-------------------------+
```

---

# 19. Evidence: cross-cutting rule

```text
                           INFORMATION
                               |
               +---------------+---------------+
               |               |               |
               v               v               v
           ESTIMATED        REPORTED        OBSERVED
               |               |               |
         prediction       project says      LEONES sees
               |               |               |
               +---------------+---------------+
                               |
                               v
                         REPRODUCTION
                               |
                               v
                          MEASURED
                               |
                               v
                     LEONES EVIDENCE
```

Never:

```text
GitHub README
     |
     v
"100 tok/s"
     |
     X
     |
     +----> LEONES MEASURED
```

Yes:

```text
GitHub README
     |
     v
REPORTED
     |
     v
LEONES reproduces test
     |
     v
MEASURED
     |
     v
environment + version + config + result
```

---

# 20. Seguridad y consent

La architecture completa necesita un segundo eje además del rendimiento:

```text
+============================================================================+
|                         TRUST / GOVERNANCE                                |
+============================================================================+
|                                                                            |
|  INSTALLATION                                                             |
|      |                                                                     |
|      +--> explicit user consent                                            |
|                                                                            |
|  NETWORK                                                                   |
|      |                                                                     |
|      +--> local / remote / cloud                                           |
|      +--> destination                                                      |
|                                                                            |
|  DATA                                                                      |
|      |                                                                     |
|      +--> documents                                                        |
|      +--> prompts                                                          |
|      +--> production traces                                                |
|      +--> training datasets                                                |
|                                                                            |
|  CREDENTIALS                                                               |
|      |                                                                     |
|      +--> API keys                                                         |
|      +--> secrets                                                          |
|                                                                            |
|  AGENTS                                                                    |
|      |                                                                     |
|      +--> tools                                                            |
|      +--> filesystem                                                        |
|      +--> shell                                                             |
|      +--> browser                                                           |
|                                                                            |
|  POST-TRAINING                                                             |
|      |                                                                     |
|      +--> dataset access                                                   |
|      +--> model access                                                     |
|      +--> artifact destination                                             |
|                                                                            |
+============================================================================+
```

---

# 21. Future provider model

The common conceptual contract should look like this:

```text
                         PROVIDER CONTRACT
                                |
          +---------------------+----------------------+
          |                     |                      |
          v                     v                      v
      DESCRIBE               PREPARE                 RUN
          |                     |                      |
          v                     v                      v
    capabilities          environment              workload
          |                     |                      |
          +---------------------+----------------------+
                                |
                                v
                              STOP
                                |
                                v
                             EXPORT
                                |
                                v
                           ARTIFACT
                                |
                                v
                           EVIDENCE
```

For inference:

```text
Provider
  |
  +-- capabilities()
  +-- can_run(model, hardware)
  +-- prepare()
  +-- serve()
  +-- health()
  +-- metrics()
  +-- stop()
```

For post-training:

```text
Provider
  |
  +-- capabilities()
  +-- validate(job)
  +-- prepare(job)
  +-- run(job)
  +-- status(job)
  +-- cancel(job)
  +-- export(job)
  +-- cleanup(job)
```

---

# 22. Proposed final physical architecture

```text
                                USER
                                 |
                                 v
                         +---------------+
                         |    LEONES     |
                         | decision layer|
                         +-------+-------+
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
          local execution                    remote execution
                |                                 |
                +----------------+----------------+
                                 |
                                 v
+==============================================================================+
|                                    ODS                                       |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  | CONTROL PLANE                                                         |  |
|  |                                                                        |  |
|  | dashboard · API · CLI · registry · scheduler · policy · artifacts     |  |
|  +--------------------------------+---------------------------------------+  |
|                                   |                                          |
|          +------------------------+-------------------------+                |
|          |                        |                         |                |
|          v                        v                         v                |
|    INFERENCE                POST-TRAINING              WORKFLOWS             |
|       FABRIC                    FABRIC                     |                |
|          |                        |                        |                |
|          v                        v                        v                |
|    runtimes/providers       training providers          TangleML            |
|          |                        |                                         |
|          +------------+-----------+                                         |
|                       |                                                     |
|                       v                                                     |
|                ARTIFACT REGISTRY                                            |
|                       |                                                     |
|                       v                                                     |
|                 MODEL REGISTRY                                               |
|                       |                                                     |
|                       v                                                     |
|                 INFERENCE FABRIC                                             |
|                       |                                                     |
|        +--------------+-------------------+                                  |
|        |              |                   |                                  |
|        v              v                   v                                  |
|      local          hybrid              remote                               |
|        |              |                   |                                  |
|        +--------------+-------------------+                                  |
|                       |                                                     |
|                       v                                                     |
|             OpenAI-compatible API                                            |
|                       |                                                     |
|       +---------------+---------------+----------------+                     |
|       |               |               |                |                     |
|       v               v               v                v                     |
|      chat            agent            RAG            workflows              |
|       |               |               |                |                     |
|       +---------------+---------------+----------------+                     |
|                       |                                                     |
|                       v                                                     |
|                  applications                                                |
+==============================================================================+
                                 |
                                 v
                         +---------------+
                         |   BENCHMARK   |
                         +-------+-------+
                                 |
                                 v
                         +---------------+
                         |    LEONES     |
                         |   EVIDENCE    |
                         +-------+-------+
                                 |
                                 v
                              MANADA
```

---

# 23. Evolution by phases

```text
PHASE 0
=======

LEONES
  |
  +--> storagever
  +--> FitLLM/LLMFit
  +--> human choice
  +--> install
  +--> benchmark

ODS
  |
  +--> llama-server
  +--> services
  +--> LiteLLM
```

```text
PHASE 1
=======

ODS
 |
 +--> multi-provider inference
 |
 +--> capability metadata
 |
 +--> local / remote / hybrid
 |
 +--> provider health
 |
 +--> benchmark hooks
```

```text
PHASE 2
=======

ODS
 |
 +--> Capability Registry
 |
 +--> Runtime Selector
 |
 +--> Execution Strategy
 |
 +--> MoE capabilities
 |       |
 |       +--> prefetch
 |       +--> cache
 |       +--> paging
 |       +--> offload
 |       +--> CPU/GPU
 |
 +--> inference providers
```

```text
PHASE 3
=======

ODS
 |
 +--> Post-Training Service
 |       |
 |       +--> LLaMA-Factory
 |       +--> Axolotl
 |       +--> Unsloth
 |       +--> TRL/PEFT
 |       +--> torchtune
 |
 +--> TangleML orchestration
 |
 +--> artifact registry
 |
 +--> model conversion
```

```text
PHASE 4
=======

LEONES <-----------------------------------------> ODS
   |                                                |
   | profile                                       | execute
   | candidate                                     | serve
   | evidence                                      | train
   | benchmark                                     | orchestrate
   |                                                |
   +------------------- capability ----------------+
                         feedback
```

---

# 24. Target architecture: LEONES as intelligence layer + ODS as execution fabric

```text
                              HUMAN
                                |
                                v
                 +----------------------------+
                 |           LEONES            |
                 |----------------------------|
                 | storagevery                   |
                 | profiling                   |
                 | recommendation              |
                 | consent                     |
                 | experiment design           |
                 | benchmark                   |
                 | evidence                    |
                 | MANADA                      |
                 +-------------+--------------+
                               |
                               | decision / policy
                               v
+==============================================================================+
|                                    ODS                                       |
|--------------------------- EXECUTION FABRIC --------------------------------|
|                                                                              |
|   MODEL REGISTRY       CAPABILITY REGISTRY       POLICY REGISTRY             |
|        |                       |                       |                      |
|        +-----------------------+-----------------------+                      |
|                                |                                              |
|                                v                                              |
|                       EXECUTION OPTIMIZER                                    |
|                                |                                              |
|             +------------------+------------------+                           |
|             |                  |                  |                           |
|             v                  v                  v                           |
|         INFERENCE          POST-TRAINING       WORKFLOW                      |
|             |                  |                  |                           |
|             v                  v                  v                           |
|         providers          providers           TangleML                      |
|             |                  |                                               |
|             +------------------+                                               |
|                                |                                               |
|                                v                                               |
|                          ARTIFACTS                                               |
|                                |                                               |
|                                v                                               |
|                           DEPLOYMENT                                              |
|                                |                                               |
|                                v                                               |
|                   chat / agents / RAG / tools                                   |
|                                                                              |
+--------------------------------+---------------------------------------------+
                                 |
                                 v
                            MEASUREMENT
                                 |
                                 v
                              LEONES
                                 |
                                 v
                               MANADA
```

---

# 25. Final architectural principle

```text
                         LEONES
                           |
             "WHAT SHOULD WE RUN?"
                           |
                           v
                    +-------------+
                    | ODS         |
                    |             |
                    | "HOW DO WE  |
                    |  RUN IT?"   |
                    +------+------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
      inference       post-training       workflow
          |                |                |
          v                v                v
      provider          provider         provider
          |                |                |
          +----------------+----------------+
                           |
                           v
                       execution
                           |
                           v
                       benchmark
                           |
                           v
                        evidence
                           |
                           v
                         LEONES
```

La architecture objetivo no es:

```text
ODS = colección de motores
```

but:

```text
ODS = EXECUTION FABRIC

        able to combine

model
  +
hardware
  +
storage
  +
runtime
  +
execution capabilities
  +
provider
  +
policy
  +
evidence

        to produce

             reproducible execution
```

And LEONES sits above and around that fabric:

```text
                 LEONES
                    |
       +------------+------------+
       |            |            |
    DISCOVER      DECIDE      MEASURE
       |            |            |
       +------------+------------+
                    |
                    v
                   ODS
                    |
          +---------+---------+
          |         |         |
       INFERENCE  TRAINING  WORKFLOW
          |         |         |
          +---------+---------+
                    |
                    v
                EXECUTION
                    |
                    v
                EVIDENCE
                    |
                    +----------> LEONES / MANADA
```

---

## Fuentes de architecture de ODS

La architecture actual de ODS, sus servicios, capas de Compose, CLI, registro de extensiones y flujos de inferencia se contrastan con la documentación oficial del proyecto. citeturn0search0turn0search3turn0search4

ODS also explicitly documents `local`, `cloud`, and `hybrid` modes, service-based extensibility, and the use of LiteLLM as a gateway. citeturn0search6

Este documento añade sobre esa architecture actual la **capa evolutiva propuesta por la investigación LEONES**: Capability Registry, Runtime Selector/Optimizer, Execution Strategy/Composition, Inference Fabric y Post-Training Fabric.


---

# 26. Inference Profile: from model fit to real capability

The Bonsai 2 small-GPU external evidence adds a concrete methodological requirement to the architecture.

LEONES + ODS must not ask only:

> Which model fits my GPU?

The target question is:

> **Which inference configuration produces the best real capability on my GPU, for this workload and policy?**

The decision unit is therefore an **Inference Profile**:

    hardware
    + model
    + representation / quantization
    + runtime / version
    + kernel / version
    + GPU layers
    + context
    + KV cache
    + MTP / speculative decoding
    + vision
    + parallel slots
    + reasoning effort
    + reproducible flags
    + evidence

This changes the architecture from a model-fit selector into a capability selector.

    hardware + workload
            |
            v
    candidate models
            |
            v
    candidate inference profiles
            |
            v
    estimated capability
            |
            v
    physical benchmark
            |
            v
    measured capability
            |
            v
    best real configuration

## 26.1 External evidence contract

The sudoingX Bonsai 2 research is incorporated as an external experimental evidence source, not as a structural dependency.

Its published results are stored as:

    EXTERNAL
    COMMUNITY
    MEASURED
    NOT_REPRODUCED_BY_LEONES

They can guide candidate generation and experiment design, but they cannot become LEONES MEASURED evidence until reproduced on the target machine.

## 26.2 Why this matters for ODS

The same model and GPU can change capability through:

    runtime
    kernel
    quantization
    context
    KV cache
    MTP
    vision
    flags

Therefore the Capability Registry and Runtime Selector should represent these dimensions explicitly.

The ODS target becomes:

    model + hardware + workload + capabilities + evidence
        |
        v
    execution profile
        |
        v
    runtime / provider
        |
        v
    physical execution

## 26.3 Relation to FATE + Edge0 + HOBBIT + HybriMoE

Bonsai 2 reinforces the same architectural principle at another layer:

    FATE       -> prediction
    Edge0      -> prefetch / streaming
    HOBBIT     -> cache / precision adaptation
    HybriMoE   -> CPU/GPU/RAM-NVMe scheduling
    runtime    -> execution
    benchmark  -> measured capability

The result is not a collection of independent backends. It is a composable execution strategy whose effectiveness must be measured.

## 26.4 LEONES evidence loop

    external evidence
          |
          v
    candidate profile
          |
          v
    controlled experiment
          |
          v
    benchmark
          |
          v
    measured evidence
          |
          v
    MANADA / future selector knowledge

This preserves the existing rule:

    ESTIMATED != REPORTED != OBSERVED != MEASURED != REPRODUCED

The architecture therefore evolves from model selection toward **real capability selection**.
