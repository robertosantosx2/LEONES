# Ecosistema de IA abierta identificado por Mozilla — análisis independiente

> **Fuente primaria:** Mozilla, *The State of Open Source AI*, v1.0.1, julio de 2026.
> **Informe:** https://stateofopensource.ai/
> **Artículo de lanzamiento:** https://blog.mozilla.org/en/mozilla/mozilla-state-of-open-source-ai-report/
> **Estado en LEONES:** fuente de conocimiento estratégica, independiente y versionada.

## 1. Propósito

Este documento convierte el ecosistema de IA abierta identificado por Mozilla en una **fuente de conocimiento estructurada para LEONES**.

No reproduce el informe ni convierte sus conclusiones en decisiones automáticas. Su función es:

1. registrar qué capas y proyectos identifica Mozilla;
2. conservar la procedencia de cada observación;
3. traducir el mapa a entidades útiles para LEONES;
4. analizar independientemente qué partes son relevantes para hardware de consumo, IA local y agentes;
5. identificar huecos que LEONES puede medir por sí mismo;
6. mantener separadas **fuente externa, interpretación y medición LEONES**.

### Regla de evidencia

```text
MOZILLA / SLASHDATA
        ↓
OBSERVACIÓN EXTERNA
        ↓
ANÁLISIS LEONES
        ↓
HIPÓTESIS / CANDIDATO
        ↓
MEDICIÓN O VERIFICACIÓN
        ↓
CONOCIMIENTO LEONES
```

Una afirmación de Mozilla no se convierte automáticamente en una medición de LEONES.

---

## 2. Qué aporta Mozilla

La edición v1.0.1 presenta un mapa del stack abierto con **9 capas y 48 componentes**, evaluados mediante diez criterios de madurez. Mozilla utiliza como dimensiones, entre otras, comunidad, adopción, preparación para producción, interoperabilidad, sostenibilidad, rendimiento frente a cerrado, documentación, estandarización y preparación empresarial.

El informe plantea una tesis central: el problema de la IA abierta se desplaza desde disponer de pesos hacia **poder operar un sistema completo**. El modelo es intercambiable; la capa que lo rodea —runtime, herramientas, memoria, ejecución, permisos, evaluación y gobernanza— concentra cada vez más valor y dificultad.

Para LEONES esto es especialmente relevante porque el objetivo del proyecto no es catalogar modelos aislados, sino encontrar combinaciones reproducibles de:

```text
modelo × variante × runtime × hardware × workload × herramientas × restricciones
```

---

## 3. Mapa independiente del ecosistema

Mozilla organiza el stack en nueve grandes capas. LEONES conserva la taxonomía de Mozilla como **fuente externa**, pero añade una clasificación propia de utilidad para IA local.

| Capa Mozilla | Función | Prioridad LEONES |
|---|---|---:|
| 01 Infrastructure | cómputo, distribución e infraestructura | Alta |
| 02 Model Components: Datasets | datos, evaluación y alineamiento | Alta |
| 03 Model Components: Code | entrenamiento, evaluación e inferencia | Muy alta |
| 04 Training | entrenamiento y adaptación | Alta |
| 05 Serving | entrega del modelo | Muy alta |
| 06 Documentation | documentación y resultados | Muy alta |
| 07 Applications | interfaces y aplicaciones | Media |
| 08 Governance / Trust | control, seguridad y responsabilidad | Muy alta |
| 09 Agent Layer | agentes, herramientas, memoria y permisos | Crítica |

> **Nota:** la nomenclatura y el número de capas/componentes corresponden al mapa de Mozilla; la tabla de prioridad es una valoración independiente de LEONES.

---

# 4. Capa 01 — Infrastructure

Mozilla identifica aquí infraestructura de cómputo y comunicación. Entre los proyectos destacados aparecen:

- Ubicloud
- SkyPilot
- GPUStack
- dstack
- Beam
- PyTorch Distributed
- Ray
- DeepSpeed
- gRPC
- Apache Spark

### Lectura LEONES

Esta capa determina si la IA abierta puede pasar de «modelo descargable» a **modelo ejecutable y servible**.

Para LEONES interesan especialmente:

- soporte para hardware heterogéneo;
- ejecución CPU/GPU;
- memoria distribuida o unificada;
- multi-GPU;
- utilización de hardware de consumo;
- reproducibilidad;
- despliegue local/offline;
- coste energético y económico.

### Señal que debemos medir

`infrastructure_portability`

Debe distinguir al menos:

```text
CPU
GPU_NVIDIA
GPU_AMD
GPU_INTEL
APPLE_SILICON
UNIFIED_MEMORY
MULTI_GPU
DISTRIBUTED
OFFLINE
```

---

# 5. Capa 02 — Model Components: Datasets

Mozilla destaca cinco familias:

### Benchmark / Evaluation Data

Ejemplos destacados:

- MT-Bench
- MBPP
- Chatbot Arena
- lm-evaluation-harness
- SWE-bench

### Data Preprocessing

- MinerU
- fastText
- Marker
- Great Expectations
- Microsoft Presidio

### Preference Alignment Data

- awesome-RLHF
- HH-RLHF Red Teaming Attempts
- PKU-SafeRLHF
- ImageReward

### Pretraining Data

- RedPajama-Data-1T
- RedPajama-v2
- Dolma Toolkit
- DCLM / DataComp-LM

### Synthetic Data

- Faker
- nlpaug
- Self-Instruct
- distilabel
- Synthea

### Lectura LEONES

Los datos deben mantenerse separados de los modelos y de las evaluaciones. En particular, el uso de un benchmark no implica que el modelo sea comparable en cualquier workload.

LEONES debe conservar:

```text
benchmark_id
version
dataset_id
split
contamination_status
protocol
model
runtime
hardware
result
source
```

Esto enlaza directamente con la regla existente de separar entrenamiento, validación y test.

---

# 6. Capa 03 — Model Components: Code

Esta es una de las capas más importantes para LEONES.

## Evaluation Code

Mozilla destaca:

- FastChat / LMSYS Chatbot Arena
- MT-Bench
- IFEval
- Promptfoo
- DeepEval

## Finetuning Code

- Unsloth
- DeepSpeed
- LLaMA-Factory
- PEFT
- Alpaca-LoRA

## Inference Code

- Ollama
- vLLM
- llama.cpp
- Ray Serve
- bitnet.cpp

## Telemetry / Observability

- PostHog LLM Observability
- Langfuse
- SigNoz
- MLflow
- promptfoo

## UI / API

- Ollama
- Langflow
- Dify
- ChatGPT-Next-Web / NextChat
- GPT4All

### Lectura LEONES

La inferencia es una dimensión de primera clase del Atlas. Un modelo sin runtime compatible no es equivalente a un modelo que puede ejecutarse en el hardware objetivo.

Por eso LEONES debe conservar separadamente:

```text
model
weights_format
runtime
runtime_version
backend
hardware
quantization
context
workload
latency
throughput
memory
```

La recomendación nunca debe decir simplemente «este modelo funciona». Debe poder decir **en qué combinación funciona y con qué evidencia**.

---

# 7. Documentación y resultados

Mozilla identifica como áreas diferenciadas:

- documentación de datos;
- resultados de evaluación;
- model cards.

Entre los proyectos destacados aparecen OpenMetadata, DataHub, Pachyderm, lakeFS, CKAN, EleutherAI LM Evaluation Harness, BFCL, MTEB y OpenCompass.

### Lectura LEONES

Esta capa valida una decisión arquitectónica ya fijada en el proyecto:

> **La evidencia es parte del producto, no un anexo.**

Cada observación debe poder reconstruirse hasta su fuente y protocolo.

---

# 8. Capa 09 — Agent Layer

Esta es la parte de mayor interés estratégico.

Mozilla descompone el agente en varias superficies.

## 8.1 Runtime Plane

Proyectos destacados:

- MCP servers
- Daytona
- AutoGen
- mem0
- CrewAI

Función: conectar el agente con herramientas, ejecución y contexto.

## 8.2 Control Plane

Proyectos destacados:

- LiteLLM
- Langfuse
- MLflow
- Casbin
- Portkey

Función: gobernar modelos, observabilidad, políticas, rutas y operaciones.

## 8.3 Frameworks

- AutoGPT
- Langflow
- Dify
- LangChain
- Microsoft AutoGen

Función: construir bucles de razonamiento/acción y aplicaciones agentivas.

## 8.4 Open Harnesses

Mozilla destaca:

- Hermes Agent
- AutoGPT
- Gemini CLI
- Codex CLI
- MetaGPT

El **harness** es la capa que convierte un modelo en un sistema capaz de actuar.

## 8.5 Standards Stack

Mozilla identifica como especialmente relevantes:

- Model Context Protocol (MCP)
- OpenAPI Specification
- Agent2Agent Protocol (A2A)
- Open Policy Agent (OPA)
- MCP Official Registry

## 8.6 Permission Model

Mozilla identifica aquí una debilidad importante del ecosistema abierto. Entre los proyectos destacados aparecen:

- Composio Tool Router
- A2A Protocol
- Open Policy Agent
- Microsoft Agent Governance Toolkit
- SPIFFE / SPIRE

### Lectura LEONES

El agente no debe modelarse como:

```text
modelo + prompt
```

sino como:

```text
MODELO
  ↓
ORQUESTACIÓN
  ↓
MEMORIA
  ↓
HERRAMIENTAS
  ↓
EJECUCIÓN / SANDBOX
  ↓
PERMISOS
  ↓
OBSERVABILIDAD
  ↓
EVALUACIÓN
```

---

# 9. El problema de los permisos

Esta es probablemente la observación del informe con mayor valor arquitectónico para LEONES.

Mozilla separa dos clases de operaciones:

### Reads

Operaciones reversibles o de bajo impacto:

- leer documentos;
- consultar bases de datos;
- listar información.

### Writes

Operaciones con efectos secundarios:

- enviar mensajes;
- gastar dinero;
- modificar registros;
- ejecutar transacciones;
- modificar código;
- publicar cambios.

El problema abierto no es principalmente identificar al agente. Es determinar **qué puede hacer sin supervisión**, qué necesita aprobación y qué está prohibido.

### Modelo que LEONES debe adoptar

```text
READ
WRITE
APPROVAL
DENY
REVOCATION
```

Y cada acción debería poder llevar:

```text
actor
resource
action
scope
risk
approval_required
cost_limit
expiry
reason
result
```

Esto debe permanecer independiente de la clasificación de apertura de los modelos.

---

# 10. El meta-harness

Mozilla apunta hacia una evolución desde frameworks individuales hacia una capa superior capaz de gobernar varios harnesses.

La idea puede representarse como:

```text
                  META-HARNESS
                       │
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
   HARNESS A       HARNESS B       HARNESS C
       │               │               │
       └───────────────┼───────────────┘
                       ↓
                 MODELOS / TOOLS
```

Esta arquitectura resulta especialmente compatible con LEONES porque el proyecto ya pretende separar selección de modelo, runtime, hardware y agente.

### Hipótesis LEONES

El futuro recomendador no debería seleccionar solamente un modelo.

Debería poder seleccionar un **stack ejecutable**:

```text
MODELO + QUANT + RUNTIME + HARNESS + TOOLS + MEMORY + POLICY
```

---

# 11. Memoria como activo

Mozilla plantea la memoria como una capa estratégica cuando el modelo se vuelve intercambiable.

Proyectos/líneas relevantes:

- Mem0
- Letta
- Zep
- LangMem

### Análisis LEONES

La memoria tiene características distintas de los pesos:

- es acumulativa;
- pertenece al sistema desplegado;
- puede ser privada;
- puede migrarse entre modelos;
- puede convertirse en ventaja por continuidad;
- necesita políticas de retención y borrado.

Por tanto, LEONES debe tratar `memory_backend` como una dimensión independiente.

---

# 12. Sandboxes y ejecución

Mozilla destaca el ecosistema de:

- E2B
- Daytona
- Modal

Estas herramientas permiten separar la capacidad de razonar de la capacidad de ejecutar.

### Relevancia para hardware de consumo

Un agente local necesita saber:

```text
¿dónde ejecuta código?
¿con qué usuario?
¿qué filesystem puede tocar?
¿tiene red?
¿qué procesos puede lanzar?
¿qué recursos puede consumir?
¿cómo se detiene?
```

Esto introduce una futura dimensión de LEONES:

`execution_sandbox`

con perfiles como:

```text
NONE
CONTAINER
VM
MICROVM
REMOTE_SANDBOX
HOST_RESTRICTED
HOST_FULL
```

---

# 13. Observabilidad

El ecosistema identificado por Mozilla incluye:

- Langfuse
- Phoenix
- LangSmith
- MLflow
- SigNoz
- promptfoo

### Lectura LEONES

La observabilidad debe cubrir como mínimo:

```text
prompt
model
runtime
hardware
latency
tokens
cost
memory
tool_calls
errors
permissions
agent_trace
```

Sin esto no puede existir una evaluación agentiva reproducible.

---

# 14. Interfaces y superficie de usuario

Mozilla identifica una segunda frontera alrededor de:

- AG-UI
- A2UI
- APIs
- metering
- pagos

El principio importante para LEONES es que una interfaz de agente no debe confundirse con el agente mismo.

```text
UI
 ↓
AGENT API
 ↓
HARNESS
 ↓
POLICY
 ↓
MODEL / TOOLS
```

---

# 15. Economía del ecosistema

Mozilla observa una fuerte diferencia entre adopción de modelos abiertos y captura económica.

La consecuencia para LEONES no es crear un único indicador económico, sino conservar dimensiones separadas:

```text
adoption
production
inference_cost
hardware_cost
energy_cost
hosting_cost
licensing_cost
switching_cost
lock_in
```

Esto conecta directamente con los futuros pilares TCO y optimización multiobjetivo.

---

# 16. Soberanía

Mozilla interpreta la apertura también como una cuestión de control tecnológico.

Para LEONES conviene separar:

- origen del modelo;
- control de pesos;
- posibilidad de ejecución local;
- dependencia de API externa;
- dependencia de proveedor;
- licencia;
- capacidad de auditoría;
- portabilidad;
- revocabilidad.

### No crear un «score soberano» prematuro

Primero se deben almacenar las evidencias individuales. Cualquier agregación posterior deberá ser explícita y auditable.

---

# 17. Geografía y concentración

Mozilla señala una fuerte actividad de Asia y China en IA abierta y utiliza adopción, descargas y tokens como indicadores del desplazamiento del centro de gravedad.

LEONES debe registrar:

```text
organization_country
model_origin
primary_development_region
community_region
infrastructure_region
```

Esto permite estudiar soberanía sin convertir nacionalidad en un criterio de calidad técnica.

---

# 18. Qué NO debemos hacer

Este documento fija varias prohibiciones metodológicas.

### No mezclar apertura con rendimiento

Un modelo más abierto no es necesariamente mejor.

### No mezclar pesos abiertos con Open Source AI

`open_weights` y `OSI_open_source` son campos distintos.

### No convertir el mapa Mozilla en ranking LEONES

Las puntuaciones de Mozilla sirven como evidencia externa y contexto.

### No confundir GitHub stars con calidad

Las estrellas son una señal de popularidad, no una medición de rendimiento.

### No confundir adopción con producción

Un proyecto puede tener enorme adopción y baja preparación operacional.

### No confundir agente con modelo

El modelo es un componente del sistema agentivo.

---

# 19. Integración con el Atlas

La integración recomendada es por relaciones, no copiando todo el informe dentro de la tabla de modelos.

```text
SOURCE
  │
  ├── ORGANIZATION
  ├── PROJECT
  ├── MODEL
  ├── RUNTIME
  ├── DATASET
  ├── BENCHMARK
  ├── HARNESS
  ├── PROTOCOL
  ├── MEMORY
  ├── SANDBOX
  └── GOVERNANCE
```

Cada entidad puede tener:

```text
source_id
source_version
source_date
source_url
observed_at
confidence
```

La fuente Mozilla queda así como **provenance**, no como autoridad única.

---

# 20. Nuevas entidades prioritarias para seguimiento

## Muy alta prioridad

- MCP
- A2A
- OPA
- LangGraph
- CrewAI
- AutoGen
- LlamaIndex
- LangChain
- LiteLLM
- Mem0
- Letta
- Zep
- E2B
- Daytona
- Langfuse
- Phoenix
- vLLM
- llama.cpp
- Ollama
- Unsloth
- LLaMA-Factory
- PEFT

## Alta prioridad

- SkyPilot
- GPUStack
- dstack
- Ray
- DeepSpeed
- OpenVINO / ecosistema Intel
- MLX / ecosistema Apple
- TensorRT-LLM / ecosistema NVIDIA
- OpenMetadata
- DataHub
- OpenCompass
- MTEB
- SWE-bench
- IFEval
- BFCL

---

# 21. Ficha canónica de un componente

Para futuras ingestas, LEONES debería normalizar como mínimo:

```yaml
component_id:
name:
organization:
category:
mozilla_layer:
mozilla_component:
project_type:
repository_url:
official_url:
license:
open_source_status:
open_weights_status:
protocols: []
runtimes: []
hardware: []
agent_capability:
memory_capability:
sandbox_capability:
permission_capability:
observability_capability:
production_readiness:
interoperability:
standardization:
enterprise_readiness:
source:
source_version:
source_date:
last_checked:
confidence:
notes:
```

Los campos desconocidos permanecen `unknown`; no se rellenan por inferencia silenciosa.

---

# 22. Cruce con los nueve pilares LEONES

| Pilar LEONES | Ecosistema Mozilla relacionado |
|---|---|
| Prospector | descubrimiento de proyectos y fuentes |
| Atlas | modelos, proyectos, runtimes y evidencia |
| Task Intelligence | benchmarks, datasets, harnesses |
| Router | LiteLLM, serving, runtimes |
| Quant | inference code, formatos y hardware |
| Fine-Tuning | Unsloth, DeepSpeed, PEFT, LLaMA-Factory |
| Agents | harness, MCP, A2A, memoria, sandbox |
| Runtime | llama.cpp, vLLM, Ollama y otros runtimes |
| Benchmark & Evaluation | lm-eval, SWE-bench, IFEval, BFCL, observabilidad |

La relación más importante es **Agents ↔ Runtime ↔ Benchmark & Evaluation**.

---

# 23. Qué puede aportar LEONES que Mozilla no mide

El informe de Mozilla es estratégico. LEONES puede aportar una capa empírica diferente.

### Hardware real

- CPU
- RAM
- VRAM
- ancho de banda
- consumo
- temperatura
- disponibilidad

### Inferencia real

- TTFT
- TPOT
- tokens/s
- p50/p95/p99
- memoria
- errores

### Ajuste a hardware de consumo

- CABE
- RULA
- RULA+
- perfiles 16/32/64/128 GB

### Combinaciones

- modelo + quant + runtime + hardware
- modelo + runtime + harness
- modelo + harness + tools
- agente + sandbox + permisos

Esto convierte a LEONES en una capa **empírica y operacional** encima del mapa estratégico.

---

# 24. Watchlist LEONES derivada de Mozilla

La fuente queda incorporada al seguimiento periódico mediante estas señales:

### Capability

- distancia open/closed;
- coding;
- reasoning;
- multimodalidad;
- agentic coding.

### Adoption

- uso;
- tokens;
- descargas;
- producción;
- región.

### Harness

- evolución de frameworks;
- adopción MCP;
- adopción A2A;
- interoperabilidad;
- governance;
- permisos portables.

### Market

- costes de inferencia;
- financiación;
- ingresos;
- infraestructura soberana;
- dependencia de proveedores.

### Trust & Safety

- misuse;
- eliminación de safety tuning;
- consentimiento;
- permisos de escritura;
- auditoría;
- revocación.

---

# 25. Indicadores internos derivados

Estos indicadores son **propuestas de LEONES**, no métricas de Mozilla.

## Open Deployment Gap

```text
open_production_rate - closed_production_rate
```

## Runtime Portability

Número de backends/hardware soportados con evidencia real.

## Agent Portability

Número de harnesses/protocolos en los que el mismo agente puede operar sin rediseño sustancial.

## Permission Maturity

Cobertura de:

```text
identity + scope + approval + budget + revocation + audit
```

## Sovereignty Dependency

Dependencia cuantificada de:

```text
external_API
external_compute
external_identity
external_memory
external_tools
```

Estos indicadores no sustituyen JGB, CABE, RULA ni la clasificación de apertura.

---

# 26. Decisión arquitectónica resultante

La incorporación de Mozilla refuerza una decisión importante:

> **LEONES debe recomendar sistemas ejecutables, no solamente modelos.**

La unidad de recomendación futura será progresivamente:

```text
SYSTEM =
MODEL
+ QUANT
+ RUNTIME
+ HARDWARE
+ HARNESS
+ MEMORY
+ TOOLS
+ SANDBOX
+ POLICY
+ EVALUATION
```

La recomendación seguirá siendo trazable a evidencia.

---

# 27. Estado de esta fuente

**Estado:** ACTIVA

**Prioridad:** ESTRATÉGICA

**Tipo:** fuente externa de conocimiento

**No sustituye:**

- clasificación Barahona;
- JGB;
- CABE/RULA;
- benchmarks LEONES;
- mediciones de hardware;
- evidencia primaria de cada proyecto.

**Actualización:** revisar nuevas ediciones de Mozilla y cambios relevantes del ecosistema.

**Última revisión:** agosto de 2026.

---

# 28. Fuentes

1. Mozilla — *The State of Open Source AI*, v1.0.1, julio de 2026: https://stateofopensource.ai/
2. Mozilla Blog — anuncio del informe, 14 de julio de 2026: https://blog.mozilla.org/en/mozilla/mozilla-state-of-open-source-ai-report/

Las cifras, nombres de proyectos y categorías procedentes del informe deben conservar siempre la referencia a su edición. Las interpretaciones y campos derivados de este documento son de LEONES y deben identificarse como tales.

---

## Principio final

Mozilla identifica el desplazamiento del valor desde el modelo hacia el sistema que lo rodea.

LEONES adopta esa observación como **hipótesis de arquitectura**, pero la somete a medición.

```text
MODELO
   ↓
RUNTIME
   ↓
HARNESS
   ↓
MEMORIA + TOOLS + SANDBOX
   ↓
PERMISOS + OBSERVABILIDAD
   ↓
EVALUACIÓN
   ↓
HARDWARE REAL
   ↓
EVIDENCIA
   ↓
RECOMENDACIÓN LEONES
```

**El objetivo no es saber qué modelo gana. Es saber qué sistema abierto funciona realmente, dónde, cómo y bajo qué condiciones.**
