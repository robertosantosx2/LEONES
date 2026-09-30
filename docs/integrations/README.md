# Integraciones LEONES: LLMFit, ODS, Magnitude y runtimes de inferencia

Estas integraciones y prospecciones convierten herramientas externas en **perfiles medibles y documentados** sin convertirlas en dependencias estructurales de LEONES.

## Introducción estratégica: hacia ODS como framework de ejecución adaptativa

La investigación de runtimes, MoE, expert streaming, CPU/GPU collaboration, predictive caching y model/hardware profiling apunta a una evolución importante para ODS.

El objetivo no debería ser que ODS sea simplemente un catálogo de backends:

```text
ODS
 ├── llama-server
 ├── MoE-Infinity
 ├── ramvamp
 ├── Edge0
 └── otros runtimes
```

Ese diseño convierte ODS principalmente en un **selector de motores**. Una arquitectura más potente es convertir ODS en una **capa de abstracción y composición de ejecución**, capaz de seleccionar la mejor combinación de modelo, estrategia, capacidades y runtime para el hardware y las necesidades concretas del usuario.

### Visión general

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
┌───────────────────────────────────────────────────────────────────────┐
│                         LEONES VALIDATION                              │
│                                                                       │
│ preflight → install → health → benchmark → measure → evidence        │
│                                                                       │
│ estimated ≠ reported ≠ observed ≠ measured                             │
└───────────────────────────────────────────────────────────────────────┘
```

### 1. User / use-case layer

ODS debería empezar por el **objetivo de ejecución**, no por el backend disponible. Latencia, calidad, privacidad, contexto, modalidad, throughput, consumo, almacenamiento y presupuesto pueden cambiar la estrategia óptima.

Por ejemplo, un asistente interactivo con una GPU pequeña necesita una estrategia distinta de una ejecución batch con una GPU de gran capacidad. La selección debe ser consecuencia de los requisitos y de las capacidades detectadas.

### 2. Model / workload profile

El perfil del modelo debe ir más allá del nombre y del número total de parámetros. Para MoE son especialmente importantes:

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

Esto permite distinguir, por ejemplo, un modelo dense grande de un MoE con muchos parámetros totales pero pocos parámetros activos.

### 3. Hardware / storage profile

El hardware debe describirse como un conjunto de recursos y capacidades:

```text
CPU · RAM · GPU · VRAM
CUDA · ROCm · Metal · NPU
PCIe · NVMe · bandwidth
memory pressure · available storage
```

Así ODS puede razonar sobre un sistema concreto, por ejemplo:

```text
RTX 3050 4 GB
+ 16 GB RAM
+ NVMe
+ CUDA
+ limited VRAM
```

en lugar de asumir simplemente que "NVIDIA = llama-server".

### 4. Capability Registry

El **Capability Registry** sería la abstracción que conecta modelos, hardware, almacenamiento y runtimes.

Un runtime podría declarar capacidades como:

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

El registro debe incorporar también restricciones, compatibilidad y evidencia. De esta manera ODS puede preguntar:

> ¿Qué combinaciones pueden ejecutar este modelo con los recursos disponibles?

en lugar de limitarse a:

> ¿Qué runtimes están instalados?

### 5. Execution Strategy / Composition

Esta es la capa estratégica más importante.

Los hallazgos de **Edge0 + FATE + HOBBIT + HybriMoE** sugieren que no deberían convertirse simplemente en cuatro entradas más del catálogo de backends.

La dirección más interesante es convertir sus ideas en **capacidades componibles**:

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

La línea estratégica para ODS es, por tanto:

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

según el hardware, el modelo, la presión de memoria y los objetivos del usuario.

#### Edge0

Edge0 resulta especialmente relevante por la combinación de expert streaming, routing prediction, prefetch y SSD. Su valor arquitectónico puede expresarse como una capacidad de **expert prefetch/streaming**, no necesariamente como una obligación de ejecutar todo el sistema dentro de Edge0.

#### FATE

FATE encaja principalmente en **expert prediction** y en la anticipación de los expertos que serán necesarios. Esa información puede alimentar un prefetcher o un sistema de caché independientemente del backend final.

#### HOBBIT

HOBBIT aporta **adaptive prefetch, multidimensional expert caching y mixed precision**. Esto permite que ODS considere simultáneamente qué expertos mantener calientes y con qué representación, según la memoria disponible.

#### HybriMoE

HybriMoE aporta una perspectiva de **CPU/GPU scheduling y colaboración**, permitiendo distribuir trabajo y memoria entre recursos heterogéneos en lugar de asumir que todo debe permanecer en GPU.

### 6. Runtime Selector / Optimizer

Una vez conocidos:

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

ODS puede seleccionar o componer una estrategia.

Por ejemplo, para una máquina con GPU pequeña:

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

El runtime concreto podría ser llama.cpp/llama-server si ofrece las capacidades necesarias, o uno de los runtimes especializados. La elección final debe validarse mediante medición, no asumirse por teoría.

Para CPU + mucha RAM + NVMe, una estrategia CPU/NVMe puede hacer que ramvamp sea candidato natural. Para GPUs NVIDIA grandes, pueden entrar en la búsqueda vLLM, SGLang, MoE-Infinity, WARP u otros runtimes dependiendo del modelo y de las capacidades disponibles.

### 7. Los runtimes dejan de ser necesariamente competidores

En esta arquitectura, los proyectos investigados pasan a ser **execution providers** con diferentes capacidades:

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

WARP, por ejemplo, puede verse como una estrategia especializada para grandes MoE y NVMe, mientras que llama-server puede ser la opción más sencilla para modelos GGUF normales y hardware con suficiente VRAM. El selector debe poder diferenciarlos según el caso.

### 8. LEONES como bucle de evidencia

LEONES proporciona la capa de validación independiente:

```text
hardware
   +
model
   +
runtime
   +
strategy
   +
configuration
   │
   ▼
benchmark
   │
   ▼
measurement
   │
   ▼
evidence
```

Esto permite que ODS evolucione de una selección basada únicamente en capacidades declaradas a una selección basada en **capacidades + evidencia**.

Las categorías deben mantenerse separadas:

```text
estimated ≠ reported ≠ observed ≠ measured
```

Por tanto, una cifra publicada por un proyecto no debe convertirse en una medición ODS/LEONES hasta que pueda reproducirse y registrarse como evidencia propia.

### Objetivo arquitectónico

La visión final es que ODS no pregunte simplemente:

> **"¿Qué backend debo usar?"**

sino:

> **"¿Qué combinación de modelo, capacidades, estrategia de ejecución y runtime es apropiada para este modelo, este hardware y este objetivo?"**

Eso convertiría progresivamente ODS de una plataforma que distribuye varios motores de inferencia en un posible **framework de orquestación de inferencia local adaptativa**.

## Integraciones principales

- **LLMFit — preselector hardware-aware**.
- **ODS — Servidor de Stacks IA**.
- **Magnitude — asistente personal IA**.
- **WARP — runtime experimental para MoE grandes mediante paging desde NVMe**.

## Prospección de runtimes para ODS

### P1 — prioridad alta

| Proyecto | Perfil | Informe |
|---|---|---|
| MoE-Infinity | MoE CUDA + RAM/SSD offload + serving | [MoE-Infinity](moe-infinity/README.md) |
| ramvamp | CPU/NVMe MoE streaming | [ramvamp](ramvamp/README.md) |
| Edge0 | SSD streaming + routing prediction | [Edge0](edge0/README.md) |
| FATE | expert prediction + async prefetch | [FATE](fate/README.md) |
| MoE-Lens | hardware/performance modeling | [MoE-Lens](moe-lens/README.md) |
| HybriMoE | CPU/GPU scheduling + cache | [HybriMoE](hybrimoe/README.md) |
| BigMoeLLM | MoE > VRAM, mmap/paging | [BigMoeLLM](bigmoellm/README.md) |
| FrankenMoE-CUDA | NVMe→RAM→VRAM expert tiers | [FrankenMoE-CUDA](frankenmoe-cuda/README.md) |
| llama.cpp expert paging PoC | posible evolución upstream | [llama.cpp expert paging](llama-cpp-expert-paging/README.md) |
| LocalAI | arquitectura multi-backend | [LocalAI](localai/README.md) |
| llama-cpp-studio | control plane multi-runtime | [llama-cpp-studio](llama-cpp-studio/README.md) |
| WARP | MoE NVMe paging | [WARP](WARP/README.md) |

### P2 — candidatos / investigación

| Proyecto | Perfil | Informe |
|---|---|---|
| SSD MoE | SSD streaming | [ssdmoe](ssdmoe/README.md) |
| ExpertFlow | predictive expert caching | [ExpertFlow](expertflow/README.md) |
| moe-hotcache | hot-expert cache sobre llama.cpp | [moe-hotcache](moe-hotcache/README.md) |
| vllm-moe | CPU offload + GPU prefetch | [vllm-moe](vllm-moe/README.md) |
| vLLM RFC | diseño de MoE CPU offload | [RFC](vllm-cpu-offload-rfc/README.md) |
| DynaExQ | precisión/residencia dinámica | [DynaExQ](dynaexq/README.md) |
| MoE CPU/GPU Collaborative Inference | caching CPU/GPU | [CPU/GPU](moe-cpu-gpu-collaborative-inference/README.md) |
| local-llm-npu | Intel NPU/OpenVINO | [NPU](local-llm-npu/README.md) |
| Atomic-Chat | multi-engine local | [Atomic-Chat](atomic-chat/README.md) |
| llama.cpp.35B.moe | optimizaciones MoE CUDA | [fork](llama-cpp-35b-moe/README.md) |
| moe-ssd-streaming-windows | SSD streaming Windows/NVIDIA | [Windows](moe-ssd-streaming-windows/README.md) |
| expert-streaming-engine | expert streaming | [engine](expert-streaming-engine/README.md) |
| ds4-ssd | SSD/weight streaming | [ds4-ssd](ds4-ssd/README.md) |
| moe-edge-inference | MoE edge | [edge](moe-edge-inference/README.md) |
| moe-stream | MoE streaming | [stream](moe-stream/README.md) |
| HOBBIT | mixed-precision expert cache | [HOBBIT](hobbit/README.md) |
| MoE-Gen | single-GPU MoE throughput | [MoE-Gen](moe-gen/README.md) |
| Fiddler | CPU/GPU collaborative inference | [Fiddler](fiddler/README.md) |

### P3 — radar

| Proyecto | Perfil | Informe |
|---|---|---|
| oBeaver | toolkit local/platform-aware | [oBeaver](obeaver/README.md) |
| Forge | runtime Rust/CUDA general | [Forge](forge/README.md) |
| BaseRT | runtime Apple/NVIDIA específico | [BaseRT](basert/README.md) |
| ES-MoE | offload para entrenamiento | [ES-MoE](es-moe/README.md) |
| weight-streaming | streaming de pesos | [weight-streaming](weight-streaming/README.md) |

## Regla de frontera

Las herramientas externas siguen siendo responsables de su instalación, runtime y comportamiento interno. LEONES se ocupa de preflight, consentimiento, instalación reproducible cuando corresponda, captura de configuración, validación independiente, benchmark y separación `estimated` / `reported` / `observed` / `measured`.

**Importante:** las cifras publicadas por los proyectos no son mediciones LEONES hasta reproducirlas.

## Flujo común

```text
PREFLIGHT → CONSENTIMIENTO → INSTALACIÓN CONTROLADA
→ HEALTH/STATUS → CONFIGURACIÓN → BENCHMARK
→ ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
→ EVIDENCIA
```
