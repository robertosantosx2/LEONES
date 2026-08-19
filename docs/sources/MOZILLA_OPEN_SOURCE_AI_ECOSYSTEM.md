# Mozilla State of Open Source AI — ecosistema y análisis LEONES

> **Tipo:** fuente de conocimiento estratégica e independiente  
> **Fuente primaria:** Mozilla, *The State of Open Source AI*, v1.0.1, julio de 2026  
> **Estado:** 🟢 Integrada · versionada · separada de las mediciones LEONES

- [Informe oficial](https://stateofopensource.ai/)
- [Artículo de lanzamiento de Mozilla](https://blog.mozilla.org/en/mozilla/mozilla-state-of-open-source-ai-report/)

---

## 1. Propósito

Este documento convierte el ecosistema identificado por Mozilla en **conocimiento reutilizable para LEONES**.

No sustituye al informe original ni convierte automáticamente sus conclusiones en datos del Atlas. Su función es:

1. conservar procedencia, edición y fecha;
2. registrar las capas y componentes identificados por Mozilla;
3. traducirlos a entidades útiles para LEONES;
4. separar hechos externos, análisis propio e hipótesis;
5. identificar qué puede medir LEONES directamente;
6. servir como base para futuras revisiones comparativas.

### Regla de evidencia

```text
MOZILLA / SLASHDATA
        ↓
OBSERVACIÓN EXTERNA
        ↓
ANÁLISIS LEONES
        ↓
CANDIDATO / HIPÓTESIS
        ↓
VERIFICACIÓN O MEDICIÓN
        ↓
CONOCIMIENTO LEONES
```

Una afirmación de Mozilla **no es una medición LEONES** hasta que LEONES la haya verificado o medido con su propio protocolo.

---

## 2. Qué aporta la fuente

La edición v1.0.1 presenta un mapa del stack de IA abierta con **9 capas y 48 componentes**, evaluados mediante criterios de madurez.

La lectura que interesa a LEONES es estructural: la disponibilidad de pesos es solo una parte del problema. Para convertir un modelo abierto en un sistema realmente utilizable hacen falta también infraestructura, runtime, datos, evaluación, serving, documentación, aplicaciones, gobernanza y capa agéntica.

Por eso LEONES conserva como unidad de recomendación:

```text
modelo × variante × runtime × hardware × workload × herramientas × restricciones
```

Y, cuando se trate de agentes:

```text
modelo
× runtime
× harness
× tools
× memory
× sandbox
× policy
× workload
```

---

## 3. Mapa de nueve capas

La siguiente tabla conserva la estructura de Mozilla y añade **solo como valoración propia** la prioridad para LEONES.

| Capa | Función | Prioridad LEONES |
|---|---|---|
| 01 · Infrastructure | cómputo, distribución e infraestructura | Alta |
| 02 · Model Components: Datasets | datos, evaluación y alineamiento | Alta |
| 03 · Model Components: Code | entrenamiento, evaluación e inferencia | Muy alta |
| 04 · Training | entrenamiento y adaptación | Alta |
| 05 · Serving | entrega e inferencia servida | Muy alta |
| 06 · Documentation | documentación y resultados | Muy alta |
| 07 · Applications | interfaces y aplicaciones | Media |
| 08 · Governance / Trust | control, seguridad y responsabilidad | Muy alta |
| 09 · Agent Layer | agentes, herramientas, memoria y permisos | Crítica |

**Importante:** la prioridad de la última columna es análisis LEONES; no es una puntuación de Mozilla.

---

## 4. Infrastructure

Mozilla sitúa aquí infraestructura de cómputo, distribución y comunicación. Entre los componentes/proyectos identificados aparecen Ubicloud, SkyPilot, GPUStack, dstack, Beam, PyTorch Distributed, Ray, DeepSpeed, gRPC y Apache Spark.

### Análisis LEONES

Para hardware de consumo importan especialmente:

- CPU y GPU heterogéneas;
- memoria disponible y compartida;
- multi-GPU;
- despliegue local/offline;
- reproducibilidad;
- portabilidad;
- coste económico y energético.

### Dimensión propuesta

`infrastructure_portability`

Valores mínimos a conservar como capacidades independientes:

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

No se debe convertir esta lista en un score sin definir previamente un protocolo de medición.

---

## 5. Model Components — Datasets

Mozilla agrupa aquí datos de evaluación, preprocesado, preferencia/alineamiento, preentrenamiento y datos sintéticos. Entre los ejemplos identificados aparecen MT-Bench, MBPP, Chatbot Arena, lm-evaluation-harness, SWE-bench, MinerU, Marker, Presidio, RedPajama, Dolma, DataComp-LM, Self-Instruct, distilabel y Synthea.

### Análisis LEONES

El dataset, el benchmark y el modelo deben permanecer separados. Usar el mismo benchmark no garantiza comparabilidad si cambian protocolo, versión, hardware, runtime o contexto.

Registro mínimo recomendado:

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

Esto mantiene la separación existente entre entrenamiento, validación y test.

---

## 6. Model Components — Code

Mozilla identifica código para evaluación, fine-tuning, inferencia, telemetría/observabilidad y UI/API. Entre los proyectos destacados aparecen FastChat, MT-Bench, IFEval, Promptfoo, DeepEval, Unsloth, DeepSpeed, LLaMA-Factory, PEFT, Alpaca-LoRA, Ollama, vLLM, llama.cpp, Ray Serve, bitnet.cpp, Langfuse, MLflow, SigNoz, Langflow, Dify y GPT4All.

### Análisis LEONES

La inferencia es una dimensión de primera clase. Un modelo no debe describirse simplemente como «funciona».

Debe poder describirse como:

```text
modelo
+ formato de pesos
+ runtime
+ versión del runtime
+ backend
+ hardware
+ cuantización
+ contexto
+ workload
+ latencia
+ throughput
+ memoria
```

Esto enlaza directamente con CABE/RULA y con la regla de conservar siempre `tokens_per_second` como dato continuo.

---

## 7. Training

La capa de entrenamiento y adaptación debe permanecer diferenciada de serving e inferencia local.

### Análisis LEONES

Para cada modelo o familia debe evitarse inferir capacidad de entrenamiento a partir de la capacidad de inferencia. Las necesidades de:

- pretraining;
- fine-tuning;
- LoRA/PEFT;
- cuantización;
- evaluación;
- serving

son distintas y deben registrar sus propios requisitos de hardware y software.

---

## 8. Serving

Serving es una capa crítica porque convierte un artefacto de modelo en un servicio ejecutable.

### Análisis LEONES

La compatibilidad debe quedar explícita:

```text
model → format → runtime → backend → hardware → serving mode
```

No se debe inferir compatibilidad por similitud de nombres de proyectos.

---

## 9. Documentation y resultados

Mozilla identifica documentación de datos, resultados de evaluación y model cards como piezas diferenciadas, junto a proyectos como OpenMetadata, DataHub, Pachyderm, lakeFS, CKAN, EleutherAI LM Evaluation Harness, BFCL, MTEB y OpenCompass.

### Análisis LEONES

Esto confirma una decisión estructural del proyecto:

> **La evidencia es parte del producto.**

Cada observación debe poder reconstruirse hasta su fuente, versión y protocolo. Una tabla sin procedencia no es evidencia suficiente para promover un registro al Atlas canónico.

---

# 10. Agent Layer — la pieza estratégica

Esta es la capa de mayor interés para LEONES.

Mozilla identifica varias superficies complementarias: runtime plane, control plane, frameworks, open harnesses, estándares, permisos y componentes de memoria/ejecución.

La traducción arquitectónica que interesa a LEONES es:

```text
MODELO
  ↓
ORQUESTACIÓN / HARNESS
  ↓
MEMORIA
  ↓
HERRAMIENTAS
  ↓
SANDBOX / EJECUCIÓN
  ↓
PERMISOS / POLICY
  ↓
OBSERVABILIDAD
  ↓
EVALUACIÓN
```

Un agente, por tanto, **no debe modelarse como modelo + prompt**.

---

## 10.1 Runtime plane

Mozilla identifica componentes/proyectos relacionados con servidores MCP, Daytona, AutoGen, Mem0 y CrewAI.

### Análisis LEONES

Esta capa conecta razonamiento, herramientas, ejecución y contexto. Para LEONES interesa especialmente su coste y comportamiento sobre hardware local.

---

## 10.2 Control plane

Mozilla identifica LiteLLM, Langfuse, MLflow, Casbin y Portkey, entre otros.

### Análisis LEONES

El control plane debe poder registrar y gobernar:

```text
modelo
ruta
herramienta
política
usuario/agente
coste
telemetría
resultado
```

No debe confundirse con el runtime de inferencia.

---

## 10.3 Frameworks

Mozilla identifica proyectos como AutoGPT, Langflow, Dify, LangChain y Microsoft AutoGen.

### Análisis LEONES

Los frameworks son una capa de construcción. No deben considerarse automáticamente equivalentes en seguridad, consumo de recursos, portabilidad o reproducibilidad.

---

## 10.4 Open harnesses

Mozilla destaca, entre otros, Hermes Agent, AutoGPT, Gemini CLI, Codex CLI y MetaGPT.

### Análisis LEONES

El **harness** es una abstracción central para el futuro recomendador. El modelo puede cambiar sin que cambie necesariamente el conjunto de herramientas, memoria, permisos o sandbox.

Esto conduce a una futura entidad:

`agent_harness`

con versión y compatibilidad explícitas.

---

## 10.5 Standards stack

Mozilla identifica como especialmente relevantes:

- Model Context Protocol (MCP);
- OpenAPI Specification;
- Agent2Agent Protocol (A2A);
- Open Policy Agent (OPA);
- MCP Official Registry.

### Análisis LEONES

Los estándares deben registrarse como **protocolos y contratos**, no como modelos. Su valor para LEONES está en la interoperabilidad y portabilidad del stack.

---

## 10.6 Permission model

Mozilla identifica una debilidad importante en la gobernanza de agentes: conocer la identidad de un agente no resuelve por sí mismo qué acciones puede realizar.

La distinción operativa fundamental es:

### READ

```text
leer documentos
consultar datos
listar recursos
```

### WRITE

```text
enviar mensajes
modificar registros
ejecutar transacciones
modificar código
publicar cambios
```

### Modelo LEONES

La futura política de permisos debe conservar como mínimo:

```text
READ
WRITE
APPROVAL
DENY
REVOCATION
```

Y, para cada acción:

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

Esto es una **propuesta arquitectónica LEONES**, no una clasificación de Mozilla.

---

# 11. Meta-harness

Mozilla apunta hacia una evolución desde frameworks/harnesses individuales hacia una capa superior capaz de gobernar varios sistemas.

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

### Hipótesis LEONES

El recomendador final debería poder seleccionar un **stack ejecutable**, no solamente un modelo:

```text
MODELO + QUANT + RUNTIME + HARNESS + TOOLS + MEMORY + POLICY
```

Esta hipótesis deberá demostrarse mediante implementación y medición antes de considerarse una capacidad aceptada.

---

# 12. Memory

Mozilla identifica la memoria como una superficie estratégica cuando el modelo se vuelve intercambiable. Entre los proyectos/líneas relevantes aparecen Mem0, Letta, Zep y LangMem.

### Análisis LEONES

La memoria debe tratarse como componente independiente porque:

- es acumulativa;
- puede ser privada;
- puede migrarse entre modelos;
- condiciona continuidad y contexto;
- requiere políticas de retención y borrado.

Dimensión propuesta:

`memory_backend`

No debe confundirse memoria persistente con ventana de contexto del modelo.

---

# 13. Sandboxes y ejecución

Mozilla identifica soluciones como E2B, Daytona y Modal.

### Análisis LEONES

Para hardware local interesa conocer:

```text
¿dónde ejecuta código?
¿con qué usuario?
¿qué filesystem puede tocar?
¿tiene red?
¿qué procesos puede lanzar?
¿qué recursos puede consumir?
¿cómo se detiene?
```

Dimensión propuesta:

`execution_sandbox`

Perfiles iniciales:

```text
NONE
CONTAINER
VM
MICROVM
REMOTE_SANDBOX
HOST_RESTRICTED
HOST_FULL
```

La disponibilidad de un perfil no implica que sea seguro para cualquier workload.

---

# 14. Observabilidad

Mozilla identifica proyectos como Langfuse, Phoenix, LangSmith, MLflow, SigNoz y Promptfoo.

### Análisis LEONES

Una evaluación agentiva reproducible debería conservar, cuando estén disponibles:

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

La observabilidad debe servir tanto para depuración como para producir evidencia.

---

# 15. Interfaces

Mozilla identifica una superficie adicional alrededor de interfaces agentivas, APIs, AG-UI, A2UI, metering y pagos.

### Análisis LEONES

La interfaz no debe confundirse con el agente:

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

# 16. Economía

Mozilla observa una diferencia entre adopción de modelos abiertos y captura económica. Para LEONES esto se conserva como conjunto de variables, no como un único índice.

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

Estas variables deben mantenerse separadas de openness y rendimiento.

---

# 17. Soberanía

Mozilla interpreta la apertura también como cuestión de control tecnológico.

LEONES debe conservar por separado:

- origen del modelo;
- control de pesos;
- ejecución local posible;
- dependencia de APIs externas;
- dependencia de proveedor;
- licencia;
- auditoría;
- portabilidad;
- revocabilidad.

### Regla

**No crear todavía un score soberano.** Primero se almacenan evidencias individuales. Cualquier agregación futura debe tener definición, fórmula, fuente y validación propias.

---

# 18. Geografía y concentración

Mozilla señala una fuerte actividad de Asia y China en IA abierta y utiliza indicadores como adopción, descargas y tokens para estudiar el desplazamiento del centro de gravedad.

### Análisis LEONES

Conviene registrar como metadatos:

```text
organization
country
region
model_family
license
weights_availability
hosting_dependency
local_run_capability
```

La procedencia geográfica es contexto estratégico; **no es por sí misma una valoración de calidad o apertura**.

---

# 19. Watchlist LEONES

Esta fuente debe alimentar una vigilancia periódica de:

### Capacidad y adopción

- evolución de capacidades abiertas frente a cerradas;
- adopción;
- producción;
- coding;
- reasoning;
- tareas agentivas.

### Harness

- evolución de frameworks;
- estándares MCP/A2A/OpenAPI;
- interoperabilidad;
- permisos;
- portabilidad de memoria;
- sandboxing.

### Economía

- coste de inferencia;
- hardware;
- hosting;
- financiación;
- sostenibilidad.

### Trust & Safety

- seguridad agentiva;
- abuso;
- gobernanza;
- políticas de permisos;
- auditabilidad.

---

# 20. Entidades candidatas para conocimiento estructurado

El documento **no crea todavía registros canónicos en Atlas**. Define candidatos que deberán pasar el mismo pipeline de identidad y evidencia que cualquier otra fuente.

```text
INFRASTRUCTURE
RUNTIME
SERVING
TRAINING
DATASET
BENCHMARK
EVALUATION
HARNESS
FRAMEWORK
TOOL
PROTOCOL
MEMORY_BACKEND
SANDBOX
POLICY_ENGINE
OBSERVABILITY
UI/API
GOVERNANCE
```

Para cada entidad candidata:

```text
source
source_version
observed_at
identity
category
license
repository
documentation
runtime_support
hardware_support
evidence_status
```

---

# 21. Campos que esta fuente puede aportar al Atlas

La fuente puede alimentar **observaciones externas** para campos como:

| Campo | Tratamiento |
|---|---|
| `runtime` | observación externa; verificar compatibilidad |
| `harness` | candidato; verificar versión y licencia |
| `memory_backend` | candidato; verificar integración |
| `execution_sandbox` | candidato; verificar capacidades |
| `permission_model` | observación/análisis; no score automático |
| `observability` | candidato; verificar integración |
| `sovereignty` | dimensiones separadas, sin score prematuro |
| `infrastructure_portability` | capacidades, no score automático |
| `benchmark` | registrar versión/protocolo |
| `license` | verificar en fuente primaria |

La clasificación de apertura de Barahona, JGB, CABE/RULA y las mediciones de rendimiento **no se sustituyen** por esta fuente.

---

# 22. Qué debe medir LEONES por sí mismo

Mozilla aporta contexto de ecosistema. LEONES debe generar evidencia propia para:

1. rendimiento real en hardware de consumo;
2. memoria consumida;
3. latencia;
4. tokens/s;
5. comportamiento por runtime;
6. comportamiento por cuantización;
7. estabilidad de serving;
8. coste energético cuando sea medible;
9. coste total de propiedad;
10. rendimiento agentivo reproducible;
11. impacto de tools, memoria y sandbox;
12. comportamiento de permisos y aprobaciones.

Principio:

```text
Mozilla = fuente externa
LEONES = medición propia
```

---

# 23. Integración con los pilares de LEONES

| Pilar | Aportación Mozilla |
|---|---|
| Prospector | nuevas entidades y proyectos |
| Atlas | metadatos y relaciones de ecosistema |
| Task Intelligence | contexto para workloads |
| Router | selección de runtime/harness/modelo |
| Quant | relación modelo ↔ runtime ↔ hardware |
| Fine-Tuning | herramientas y datos |
| Agents | harness, tools, memory, sandbox, policy |
| Runtime | compatibilidad y serving |
| Benchmark & Evaluation | benchmarks, observabilidad y trazabilidad |

La fuente **amplía** los pilares; no redefine sus contratos congelados.

---

# 24. Pipeline de incorporación

```text
FUENTE MOZILLA
      ↓
CAMBIO DE EDICIÓN
      ↓
EXTRACCIÓN DE ENTIDADES
      ↓
NORMALIZACIÓN
      ↓
IDENTIDAD
      ↓
EVIDENCIA PRIMARIA
      ↓
QUALITY GATE
      ↓
OBSERVACIÓN EXTERNA
      ↓
ATLAS / RECOMENDADOR
```

No se promueve directamente una entidad al catálogo canónico solo porque aparezca en el informe.

---

# 25. Revisión y versionado

### Cadencia

- **mensual:** revisar señales relevantes;
- **nueva edición Mozilla:** comparación completa;
- **cambio crítico:** revisión inmediata si afecta a una decisión del proyecto.

### Procedimiento

```text
comparar edición anterior
        ↓
identificar entidades nuevas/eliminadas
        ↓
revisar licencias y repositorios
        ↓
revisar claims cuantitativos
        ↓
revisar hipótesis LEONES
        ↓
conservar histórico
        ↓
actualizar documento
        ↓
validar enlaces y formato
```

---

# 26. Criterio de cierre de esta fuente

Esta fuente se considera **integrada documentalmente** cuando:

- existe documento independiente;
- la procedencia está identificada;
- el documento está enlazado desde `docs/README.md`;
- figura en `docs/sources/README.md`;
- se separan fuente externa, análisis y medición;
- no se alteran clasificaciones congeladas;
- existe procedimiento de actualización.

El cierre documental **no implica** que todas las entidades identificadas por Mozilla hayan sido verificadas o incorporadas al Atlas.

---

## 27. Regla de limpieza y mantenimiento

Este documento es la representación canónica de la fuente Mozilla dentro de LEONES.

No deben crearse copias paralelas con el mismo propósito. Las ampliaciones deben hacerse aquí o, si generan un subproyecto con contrato propio, en un documento claramente enlazado.

No deben mezclarse en este documento:

- resultados de benchmarks propios;
- precios actuales;
- mediciones de hardware;
- puntuaciones internas;
- conclusiones no trazables a una fuente.

Esos datos pertenecen a sus respectivos sistemas de evidencia.

---

## 28. Referencia primaria

**Mozilla — The State of Open Source AI, v1.0.1 (julio de 2026).**

Esta página debe considerarse la referencia primaria para las afirmaciones atribuidas a Mozilla. LEONES conserva aquí una **síntesis estructurada y análisis independiente**, no una reproducción del informe.

---

### Estado LEONES

**🟢 FUENTE INTEGRADA · DOCUMENTACIÓN CANÓNICA · SIN PROMOCIÓN AUTOMÁTICA AL ATLAS**
