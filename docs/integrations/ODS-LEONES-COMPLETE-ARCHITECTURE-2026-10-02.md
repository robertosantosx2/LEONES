# Arquitectura completa LEONES + ODS
## Estado actual + evolución propuesta

> Documento de arquitectura de referencia para la evolución conjunta de LEONES y ODS.
> Todo diagrama de este documento está expresado en ASCII para que siga siendo legible desde
> terminales, GitHub, TUI, SSH y herramientas sin renderizado gráfico.

Fecha de referencia: 2026-10-02

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
        | discover             |     | install              |
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

# 1. LEONES — arquitectura completa

## 1.1 Capas actuales

```text
+==============================================================================+
|                                  LEONES                                      |
|                    Local Ecosystem of Open Neural Expert Systems             |
+==============================================================================+
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                         USER / HUMAN AUTHORITY                         |  |
|  |                                                                        |  |
|  |  idioma                                                               |  |
|  |  propósito(s)                                                         |  |
|  |  modelo elegido                                                       |  |
|  |  stack elegido                                                        |  |
|  |  consentimiento                                                       |  |
|  |  instalación / desinstalación                                         |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                           MACHINE DISCOVERY                            |  |
|  |                                                                        |  |
|  |  CPU · RAM · GPU · VRAM · disco · OS · drivers · Docker               |  |
|  |  CUDA · ROCm · Metal · NPU · Vulkan · runtimes existentes             |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                     |
|                                      v                                     |
|  +------------------------------------------------------------------------+  |
|  |                           INVENTORY / STATE                            |  |
|  |                                                                        |  |
|  |  FitLLM/LLMFit · ODS · Magnitude · LLMs · agents · harnesses           |  |
|  |  versiones · instalación · disponibilidad · procedencia               |  |
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

# 2. LEONES — flujo RC4 actual

```text
                              +-----------+
                              |  IDIOMA   |
                              +-----+-----+
                                    |
                                    v
                         +----------------------+
                         | ESTADO DE MÁQUINA   |
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

# 3. LEONES — componentes futuros

La evolución no consiste en añadir herramientas sin límite. Consiste en añadir capacidades alrededor de un contrato de decisión y evidencia.

```text
+============================================================================+
|                           LEONES FUTURO                                    |
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

# 4. ODS — arquitectura actual completa

La arquitectura actual de ODS V3 se organiza alrededor de servicios Docker, overlays por plataforma/GPU, un registro de servicios y un CLI que ensambla y opera el stack. La documentación oficial describe servicios de inferencia, UI, gateway, voz, búsqueda, agentes, RAG, generación multimedia, privacidad/observabilidad y desarrollo. citeturn0search0turn0search1

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
|   +--> feature discovery                                               |
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

# 8. ODS — la arquitectura futura que resulta de toda la investigación

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

# 12. Post-Training — arquitectura completa

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
LEONES       = discovery / decision / evidence
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

Free-provider fallback puede ser una opción, pero no debe tratarse como equivalente automático a un runtime local: hay que registrar términos, privacidad, límites, disponibilidad y dependencia del proveedor.

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

# 19. Evidencia: regla transversal

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

Nunca:

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

Sí:

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

# 20. Seguridad y consentimiento

La arquitectura completa necesita un segundo eje además del rendimiento:

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

# 21. Modelo futuro de proveedor

El contrato conceptual común debería parecerse a esto:

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

Para inference:

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

Para post-training:

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

# 22. Arquitectura física final propuesta

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

# 23. Evolución por fases

```text
PHASE 0
=======

LEONES
  |
  +--> discover
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

# 24. Arquitectura objetivo: LEONES como intelligence layer + ODS como execution fabric

```text
                              HUMAN
                                |
                                v
                 +----------------------------+
                 |           LEONES            |
                 |----------------------------|
                 | discovery                   |
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

# 25. Principio arquitectónico final

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

La arquitectura objetivo no es:

```text
ODS = colección de motores
```

sino:

```text
ODS = EXECUTION FABRIC

        capaz de combinar

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

        para producir

             reproducible execution
```

Y LEONES queda por encima y alrededor de esa fabric:

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

## Fuentes de arquitectura de ODS

La arquitectura actual de ODS, sus servicios, capas de Compose, CLI, registro de extensiones y flujos de inferencia se contrastan con la documentación oficial del proyecto. citeturn0search0turn0search3turn0search4

ODS también documenta explícitamente los modos `local`, `cloud` y `hybrid`, así como la extensión mediante servicios y el uso de LiteLLM como gateway. citeturn0search6

Este documento añade sobre esa arquitectura actual la **capa evolutiva propuesta por la investigación LEONES**: Capability Registry, Runtime Selector/Optimizer, Execution Strategy/Composition, Inference Fabric y Post-Training Fabric.


---

# 26. Inference Profile: del ajuste del modelo a la capacidad real

La evidencia externa experimental de Bonsai 2 añade un requisito metodológico concreto a la arquitectura.

LEONES + ODS no debe preguntar solamente:

> ¿Qué modelo cabe en mi GPU?

La pregunta objetivo es:

> **¿Qué configuración de inferencia produce la mejor capacidad real en mi GPU, para este workload y esta política?**

La unidad de decisión pasa a ser un **Inference Profile**:

    hardware
    + modelo
    + representación / cuantización
    + runtime / versión
    + kernel / versión
    + GPU layers
    + contexto
    + KV cache
    + MTP / speculative decoding
    + visión
    + slots paralelos
    + reasoning effort
    + flags reproducibles
    + evidencia

Esto transforma la arquitectura de un selector de ajuste de modelos en un selector de capacidad.

    hardware + workload
            |
            v
    modelos candidatos
            |
            v
    perfiles de inferencia candidatos
            |
            v
    capacidad estimada
            |
            v
    benchmark físico
            |
            v
    capacidad medida
            |
            v
    mejor configuración real

## 26.1 Contrato de evidencia externa

La investigación de sudoingX sobre Bonsai 2 se incorpora como fuente externa de evidencia experimental, no como dependencia estructural.

Sus resultados publicados se registran como:

    EXTERNAL
    COMMUNITY
    MEASURED
    NOT_REPRODUCED_BY_LEONES

Pueden orientar la generación de candidatos y el diseño experimental, pero no pueden convertirse en evidencia MEASURED de LEONES hasta ser reproducidos sobre el equipo objetivo.

## 26.2 Por qué importa para ODS

El mismo modelo y la misma GPU pueden cambiar de capacidad mediante:

    runtime
    kernel
    cuantización
    contexto
    KV cache
    MTP
    visión
    flags

Por tanto, Capability Registry y Runtime Selector deben representar explícitamente estas dimensiones.

El objetivo de ODS pasa a ser:

    modelo + hardware + workload + capacidades + evidencia
        |
        v
    perfil de ejecución
        |
        v
    runtime / provider
        |
        v
    ejecución física

## 26.3 Relación con FATE + Edge0 + HOBBIT + HybriMoE

Bonsai 2 refuerza el mismo principio arquitectónico desde otra capa:

    FATE       -> predicción
    Edge0      -> prefetch / streaming
    HOBBIT     -> cache / adaptación de precisión
    HybriMoE   -> scheduling CPU/GPU/RAM-NVMe
    runtime    -> ejecución
    benchmark  -> capacidad medida

No son simplemente backends independientes. Son piezas potencialmente componibles de una estrategia de ejecución cuya eficacia debe medirse.

## 26.4 Bucle de evidencia LEONES

    evidencia externa
          |
          v
    perfil candidato
          |
          v
    experimento controlado
          |
          v
    benchmark
          |
          v
    evidencia medida
          |
          v
    MANADA / conocimiento futuro del selector

Se conserva la regla existente:

    ESTIMATED != REPORTED != OBSERVED != MEASURED != REPRODUCED

La arquitectura evoluciona así de la selección de modelos hacia la **selección de capacidad real**.
