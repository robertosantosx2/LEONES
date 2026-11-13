# Integraciones runtimes de inferencia en ODS

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



### Objetivo arquitectónico

La visión final es que ODS no pregunte simplemente:

> **"¿Qué backend debo usar?"**

sino:

> **"¿Qué combinación de modelo, capacidades, estrategia de ejecución y runtime es apropiada para este modelo, este hardware y este objetivo?"**

Eso convertiría progresivamente ODS de una plataforma que distribuye varios motores de inferencia en un posible **framework de orquestación de inferencia local adaptativa**.

## Magnitude como integración de perfil de asistente personal

Magnitude ocupa una posición diferente de los runtimes de inferencia investigados en este índice. En LEONES se estudia como una integración de referencia para el perfil **Personal AI Assistant**: proporciona el agente y su ejecución local, mientras que LEONES aporta preflight, instalación, gobernanza, validación y benchmark.

Según el informe específico [Magnitude](Magnitude.md), las capacidades relevantes incluyen:

- agente local y modelos locales;
- perfilado de hardware;
- recomendación de modelos;
- descarga y configuración;
- ejecución local;
- skills;
- endpoints compatibles con OpenAI;
- enfoque de privacidad/offline para la ejecución local.

Esto encaja con la arquitectura adaptativa de ODS porque Magnitude puede aportar información y experiencia de usuario en las capas de **model/workload profiling**, **hardware profiling** y **model selection**, sin convertirse por ello en el runtime de inferencia que ODS deba utilizar.

El flujo de validación propuesto por LEONES es:

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

Las skills deben catalogarse por origen, versión/ref, permisos, acceso a archivos, red y herramientas. LEONES no debería instalar automáticamente skills de riesgo. Asimismo, los datos deben separar `observed`, `recommended/configured`, `estimated` y `measured`, evitando registrar prompts, archivos, código, conversaciones, secretos o API keys.

## Integraciones principales

- **LLMFit — preselector hardware-aware**.
- **ODS — servidor de stacks IA**.
- **Magnitude — integración de referencia para asistente personal IA**: [Magnitude](Magnitude.md).
- **WARP — runtime experimental para MoE grandes mediante paging desde NVMe**.
- **TensorFold — runtime especializado MLX/CUDA con speculative decoding y verificación exacta dentro del mismo motor**.

## Prospección de runtimes para ODS


### P0 — integración estratégica / cualificación activa

Se introduce P0 para proyectos que han superado el umbral entre interés de investigación y objetivo de integración estratégicamente importante: el runtime upstream tiene madurez operativa, su API y sus capacidades encajan con ODS y existe una ruta concreta para cualificarlo de forma controlada. P0 **no** significa que la integración ya esté implementada, que todos los modelos estén soportados ni que el proyecto pueda activarse por defecto con seguridad.

| Proyecto | Perfil | Informe |
|---|---|---|
| TensorFold | proveedor nativo multi-backend; rutas CUDA/HIP/XPU; APIs OpenAI/Anthropic; speculative decoding, reutilización de estado de prompt, concurrencia y serving con capacidades de imagen | [TensorFold](tensorfold/README.md) |

### Por qué TensorFold asciende a P0

Una nueva revisión a 13/11/2026 cambia la evaluación P1 anterior. TensorFold ha avanzado por la serie de motores 1.2.x hasta **1.2.7 (publicada el 11/11/2026)**. No es solo un incremento de versión: la secuencia de releases demuestra trabajo activo en familias de modelos, aceleradores, semántica de serving, caché, conformance y herramientas operativas.

Las señales de madurez más importantes son:

- **Varias familias de aceleradores:** NVIDIA CUDA nativo, AMD HIP (incluidas rutas RDNA/gfx1151 documentadas) e iniciativas de conformance Intel XPU. La web también anuncia AMD HIP/Vulkan, pero LEONES debe distinguir la etiqueta anunciada para el backend de cada combinación modelo/SO realmente cualificada en las releases.
- **Runtime nativo:** motor Zig que lee checkpoints soportados y ejecuta directamente kernels Metal/CUDA. El archivo Linux tiene requisitos explícitos: glibc 2.28+, NVIDIA R580+ y CUDA 13.0 para la build CUDA.
- **Interoperabilidad de serving:** APIs compatibles con OpenAI y Anthropic; chat/completions, Responses, Responses por WebSocket, tool calls, serving mediante Unix socket local y opciones de autenticación documentadas.
- **Más allá de generación de texto:** entrada de imágenes según modelo, endpoint de generación de imágenes cuando el engine expone esa capacidad, rutas OCR/image-chat y endpoints de embeddings/reranking/decisiones en determinadas familias. No son capacidades universales de todos los checkpoints.
- **Speculative decoding:** MTP y drafters externos como DFlash2 y DSpine-b16 en combinaciones concretas de familia/backend. El drafting sigue siendo opt-in cuando así lo indica la documentación; no debe suponerse por tener el drafter en caché o por el nombre del modelo.
- **Reutilización de estado de prompt:** retención en memoria y en disco, reanudación de conversaciones y admisión de caché preparada para múltiples agentes. La versión 1.2.6 publicó grandes mejoras de first-token en seguimientos con 8–16 agentes concurrentes, manteniendo las respuestas en sus configuraciones de prueba.
- **Concurrencia y scheduling:** admisión de peticiones paralelas, rondas compartidas, planificación prompt/decode, presupuesto de caché y planificación de memoria específica por modelo ya forman parte del comportamiento del motor.
- **Conformance y reproducibilidad:** perfiles de conformance por familia, gates de exactitud, recibos de benchmark y flujo para inspeccionarlos. El benchmark público distingue versiones de recibos y advierte que los resultados comunitarios no verifican independientemente el hardware.
- **Superficie operativa:** TensorFold Web ofrece selección de modelos y chat en local; también existe una aplicación de escritorio separada y un proyecto de flota/empresa, TensorFold Starlight. Son productos relacionados, no paquetes intercambiables de un único runtime.

### Release 1.2.7: evidencia concreta, no una afirmación genérica de compatibilidad

La release 1.2.7 (11/11/2026) incorpora, entre otros cambios:

- transporte WebSocket para Responses API;
- serving image-chat de LightOnOCR-3 0.8B y 4B en CUDA desde pesos BF16 del publicador;
- perfil de conformance XPU para Qwen3.8-27B en Intel Arc Pro B70;
- visibilidad de la prompt cache en el dashboard y `/stats`;
- mejoras al reanudar conversaciones largas; un caso publicado en M3 Ultra reanuda al final del turno anterior una historia de 34K y reduce el first-token de unos 85 segundos a unos 0,3 segundos;
- cambios de rendimiento/memoria en Metal, CUDA e HIP, con afirmaciones de equivalencia de salida especificadas para cada medición, no generalizadas.

La release 1.2.6 anterior añade drafting CUDA con DSpine-b16 para Qwen3.8-27B (opt-in), Unix socket local restringido al propietario, `POST /v1/images/generations` para engines con capacidad de imagen y mejoras importantes de prompt cache/agentes concurrentes. Sus mediciones concretas en GB10 y Apple Silicon pertenecen a esas releases y condiciones; no son un multiplicador universal de velocidad.

Las cifras destacadas deben conservar siempre modelo, backend, hardware, release, contexto, concurrencia y condiciones de decoding. Los resultados 1.2.7 en Metal, CUDA e HIP no son comparables directamente entre sí y no son benchmarks de LEONES.

### Qué significa esto para ODS

ODS ha desarrollado una vía de integración práctica que no existía en la evaluación anterior:

1. El contrato de provider modes de ODS permite explícitamente un servidor externo OpenAI-compatible gestionado por el propietario en modo local, con URL, ID exacto del modelo e identidad del proveedor en la configuración.
2. El contrato exige una frontera de adapter para normalizar URLs, autenticación, health/version/model discovery, probes de chat y capacidades opcionales, clasificación de errores y recuperación.
3. Las notas de ODS 2.6.0 describen Model Switchboard con routing estable para aplicaciones locales, propagación de contexto, validación de identidad de modelo y swaps con rollback.
4. ODS V3 ofrece un flujo de recetas de extensiones y una superficie operativa más amplia, pero una receta o entrada de catálogo no demuestra que el proveedor esté cualificado.

Esto permite una integración por etapas:

**Etapa A — cualificación como proveedor externo.** Ejecutar TensorFold como servicio gestionado por el propietario y conectarlo mediante el modo externo OpenAI-compatible existente en ODS. Mantener intactos el runtime y la instalación actuales de ODS. Validar endpoint, auth, identidad del modelo, chat, streaming/tool calls y las capacidades opcionales requeridas por el perfil.

**Etapa B — adapter de proveedor de primera clase.** Si A supera las pruebas, añadir un adapter/perfil específico TensorFold, en lugar de dispersar condicionales por instalador, dashboard y Compose. El adapter debe consultar `capabilities --json`, fijar o validar la versión, exponer solo capacidades probadas para el modelo/backend seleccionado y ofrecer probes acotados de health/model/completion.

**Etapa C — servicio/extensión gestionada opcional.** Solo después de superar las pruebas de lifecycle y seguridad, ODS debería ofrecer un servicio gestionado opt-in. Fijar archivo/checksum o digest de imagen, revisión del modelo, flags y plan de recursos. TensorFold no debe convertirse en dependencia por defecto ni descargar checkpoints silenciosamente.

### Correspondencia de capacidades ODS

| Área del contrato ODS | Encaje de TensorFold | Cualificación pendiente |
|---|---|---|
| Proveedor externo local | Alto: API OpenAI-compatible e ID configurable | Alcance host/container, auth y ownership del lifecycle |
| Model Switchboard | Encaje arquitectónico alto con alias estable ODS | Pruebas de swap, identidad, contexto, rollback y consumidores |
| Chat/completions/streaming | Documentado | Compatibilidad de clientes ODS, cancelación, errores y streams largos |
| Tool/function calls | Documentado en rutas soportadas | Conformance exacta de schema/streaming para cada modelo elegido |
| Visión/OCR | Disponible en combinaciones concretas de familia/backend | Pruebas de image tower, processor, VRAM y endpoints por checkpoint |
| Generación de imagen | Existe endpoint cuando el engine expone esa capacidad | Contrato de producto ODS y matriz modelo/backend |
| Embeddings/rerank | Existen endpoints/familias seleccionadas | Contrato de proveedor y compatibilidad con consumidores RAG de ODS |
| Métricas/stats | Dashboard, `/stats`, `/v1/load` y endpoints de memoria varían por release | Adapter de telemetría ODS y estados explícitos de no soportado |
| Instalación/update/rollback | Archivo nativo y flujo checksum documentados | Lifecycle gestionado por ODS, pinning, rollback y revisión de seguridad |

### Cualificación de hardware: RTX 3050 4 GB sigue pendiente

La release CUDA de TensorFold incluye fatbins para sm_80, sm_86, sm_120 y sm_121. El runbook registra pruebas de determinados modelos en RTX 3090 (sm_86) y advierte expresamente de que un resultado en una GPU sm_86 no cualifica todas las GPU de esa clase.

Es un avance relevante para la familia de arquitectura, pero **no cualifica la RTX 3050 Laptop GPU de 4 GB**. La ruta pequeña Qwen3.5-2B del quick start está comprobada en Mac/GB10, no específicamente en una RTX 3050 de 4 GB. Las cargas CUDA publicadas utilizan GB10, RTX 3090 o hardware de clase RTX PRO 6000; no deben extrapolarse al portátil.

Para LEONES hay que registrar por separado:

- backend CUDA e imágenes de kernel sm_86: documentados;
- ejecución de determinados modelos sm_86: documentada en RTX 3090;
- admisión del checkpoint completo en RTX 3050 4 GB: no establecida;
- throughput, VRAM máxima y estabilidad sostenida en RTX 3050: no medidos;
- integración ODS + TensorFold de extremo a extremo en el MSI: no medida.

El siguiente experimento de hardware debe empezar por `capabilities --json`, inspección del memory floor con `info` y selección del checkpoint CUDA soportado más pequeño. Solo después se debe proponer una prueba controlada de pull/serve. Que un fichero 4-bit mida menos de 4 GB no basta: también cuentan contexto CUDA, pesos, buffers temporales, KV/prompt cache, drafter y demás asignaciones.

### Plan P0 y gates de aceptación

P0 significa que TensorFold merece una línea activa y acotada de integración. No autoriza instalarlo ni reemplazar el runtime ODS actual.

1. **Fijar evidencia upstream:** registrar release/tag/commit 1.2.7, checksum del archivo, RUNBOOK, tabla de modelos cualificados y revisiones exactas de checkpoints.
2. **Descubrimiento de capacidades:** capturar `tensorfold capabilities --json`, versión, backend, familia, formato y memory floor del modelo.
3. **Admisión de hardware:** recoger compute capability, VRAM, driver, CUDA runtime, RAM, disco libre, acceso al contenedor y presupuesto de contexto/cache.
4. **Smoke test de proveedor externo:** usar el modo external-provider de ODS sin cambiar el engine gestionado; verificar health, lista de modelos, completion, streaming, auth y tool calls.
5. **Conformance de consumidores:** probar LiteLLM/Model Switchboard y cada consumidor ODS habilitado; verificar identidad, contexto, cancelación, propagación de errores y rollback.
6. **Capacidades opcionales:** probar visión/OCR, embeddings, rerank y generación de imagen solo cuando el modelo/backend elegido las anuncie.
7. **Benchmark:** capturar TTFT, tok/s de prompt, tok/s de decode, concurrencia, latencia de resume, VRAM/RAM máximas, tiempo de carga y estabilidad; comparar solo con el mismo checkpoint/configuración en el mismo hardware.
8. **Seguridad/lifecycle:** verificar bind a loopback, API keys, Unix socket owner-only cuando se utilice, artefactos fijados, update/rollback y ausencia de descargas implícitas.
9. **Revisión de promoción:** mantener P0 mientras haya cualificación activa; una vez que exista un adapter probado, reclasificar según el estado real de integración y el valor estratégico, no por entusiasmo con releases upstream.

### Reglas de evidencia y alcance

Utilizar cuatro etiquetas distintas:

- **UPSTREAM-REPORTED** — release note, receta o benchmark publicado por TensorFold;
- **SOURCE-OBSERVED** — capacidad/flag/implementación visible en source o archivo de release fijado;
- **LEONES-MEASURED** — reproducido independientemente en hardware LEONES identificado;
- **ODS-QUALIFIED** — el proveedor supera los gates de adapter, consumidores, lifecycle y rollback de ODS.

No deben fusionarse estas categorías. Un benchmark TensorFold no es automáticamente una medición LEONES; un servidor TensorFold standalone funcionando no es automáticamente un proveedor ODS cualificado; y una receta de extensión ODS no constituye una integración completa.

### Decisión

**Promover TensorFold de P1 a P0 — integración estratégica / cualificación activa.** La promoción se justifica por su motor nativo multiacelerador actual, cobertura creciente de familias, superficie madura de serving OpenAI/Anthropic, ingeniería de prompt-state y concurrencia, herramientas de conformance, recibos de benchmark y encaje directo con la arquitectura external-provider/Model Switchboard de ODS.

El objetivo inmediato **no** es «reemplazar llama-server» ni «activar TensorFold por defecto». Es un proceso TensorFold independiente conectado mediante el contrato external-provider de ODS, con un futuro adapter de primera clase condicionado a conformance. La cualificación de la RTX 3050 de 4 GB sigue siendo una puerta de hardware separada y pendiente.

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


### Integraciones experimentales adicionales

| Proyecto | Perfil | Informe |
|---|---|---|
| AirLLM | streaming de capas/expertos para modelos Hugging Face | [AirLLM](airllm/README.md) |
| Companion Hub | referencia de control/orquestación de aplicaciones locales | [Companion Hub](companion-hub/README.md) |
| Kimi K3 in C | runtime especializado con streaming de modelo y caché de expertos | [Kimi K3 in C](kimi-k3-in-c/README.md) |
| LaptopLLM | referencia de streaming de capas y UX para portátiles | [LaptopLLM](laptopllm/README.md) |


## Post-training / Pos-entrenamiento

Research on post-training as part of **LEONES Evolution**, using hybrid compute while keeping **ODS as the AI execution platform**:

- [TangleML — Post-training / hybrid compute — English](post-training/TANGLEML.md)
- [TangleML — Post-training / computación híbrida — Español](post-training/TANGLEML-ES.md)
- [Gerbil SDK / Tune — specialist tuning, adapters and edge runtime — English](post-training/GERBIL.md)
- [Gerbil SDK / Tune — especialización, adapters y runtime edge — Español](post-training/GERBIL-ES.md)

## Multi-provider hybrid inference

Research on evolving ODS into a multi-provider hybrid inference layer, with free-provider fallback and explicit routing policies:

- [Multi-provider hybrid inference / Free-provider fallback — English](MULTI-PROVIDER-HYBRID-INFERENCE.md)
- [Inferencia híbrida multi-proveedor / fallback de proveedores gratuitos — Español](MULTI-PROVIDER-HYBRID-INFERENCE-ES.md)


## Post-training / Pos-entrenamiento

- [LLaMA-Factory — ODS Post-Training Service Provider — English](post-training/LLAMA-FACTORY.md)
- [LLaMA-Factory — provider del servicio Post-Training de ODS — Español](post-training/LLAMA-FACTORY-ES.md)

- [Axolotl — ODS Post-Training Service Provider — English](post-training/AXOLOTL.md)
- [Axolotl — proveedor del servicio Post-Training de ODS — Español](post-training/AXOLOTL-ES.md)

- [Unsloth — ODS Post-Training Service Provider — English](post-training/UNSLOTH.md)
- [Unsloth — proveedor del servicio Post-Training de ODS — Español](post-training/UNSLOTH-ES.md)

## Evidencia experimental externa: Bonsai 2 / small-GPU

La investigación de sudoingX sobre Bonsai 2 se incorpora como **fuente externa de evidencia experimental**, no como dependencia. Refuerza un cambio arquitectónico de LEONES + ODS: pasar de preguntar «qué modelo cabe en mi GPU» a determinar «qué configuración de inferencia produce la mejor capacidad real en mi GPU».

La unidad de decisión pasa a ser el **Inference Profile**: hardware + modelo + cuantización + runtime + kernel + contexto + KV + MTP + visión + flags + mediciones.

- [Bonsai 2 27B / small-GPU — evidencia externa](Bonsai2-Small-GPU-EXTERNAL-EVIDENCE.md)
- [Bonsai 2 27B / small-GPU — external evidence (English)](Bonsai2-Small-GPU-EXTERNAL-EVIDENCE-eng.md)

Los resultados publicados se clasifican como EXTERNAL / COMMUNITY / MEASURED / NOT_REPRODUCED_BY_LEONES. Solo una reproducción física controlada puede convertirse en MEASURED de LEONES.

## Arquitectura completa LEONES + ODS

- [Arquitectura completa LEONES + ODS — estado actual y evolución propuesta](ODS-LEONES-COMPLETE-ARCHITECTURE.md)

- [ODS + LEONES — arquitectura completa (2026-10-02)](ODS-LEONES-COMPLETE-ARCHITECTURE-2026-10-02.md)

- [ODS + LEONES — complete architecture (2026-10-02, English)](ODS-LEONES-COMPLETE-ARCHITECTURE-2026-10-02-eng.md)


## Cost awareness / Costes de IA híbrida

Investigación sobre cómo informar al usuario del gasto previsto y real cuando ODS utiliza IA remota/propietaria dentro del modo híbrido:

- [Cost awareness para IA híbrida — Español](LLM-COST-AWARENESS-ES.md)
- [Cost Awareness for Hybrid AI — English](LLM-COST-AWARENESS-eng.md)

La investigación propone un **Cost Envelope + Cost Ledger**, con procedencia de precios, estimación previa, coste real, caché/reasoning, retries/fallbacks, presupuestos y separación estricta entre provider cost y coste operativo local.


## Inference Configuration Discovery (ICD) — LEONES + ODS

La evolución de ODS como framework adaptativo incorpora **Inference Configuration Discovery** como unidad de decisión: no solo qué modelo o runtime encaja, sino qué combinación de modelo, cuantización, engine, colocación de memoria, caché, offload, contexto y decoding produce la mejor capacidad real.

- [ICD / Strata — Español](ODS/INFERENCE-CONFIGURATION-DISCOVERY-2026-10-06.md)
- [ICD / Strata — English](ODS/INFERENCE-CONFIGURATION-DISCOVERY-2026-10-06-eng.md)

Strata aporta evidencia experimental externa sobre MoE heterogéneo; sus cifras publicadas siguen separadas de las mediciones LEONES hasta su reproducción física controlada.
