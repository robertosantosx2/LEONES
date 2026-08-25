# Auditoría consolidada del conocimiento — 2026-08-25

## Propósito

Este documento consolida la auditoría de las fuentes prioritarias del conocimiento LEONES y fija, para cada una, la separación estricta entre:

1. **Fuente / Descubrimiento** — qué declara o proporciona el proyecto externo.
2. **Evidencia** — qué está respaldado por documentación, código, paper o artefacto primario.
3. **Estimación** — qué calcula, predice, puntúa o recomienda una herramienta externa.
4. **Medición LEONES** — qué ha ejecutado y medido físicamente LEONES.

La regla es irreversible: una capa superior no convierte automáticamente una capa inferior en evidencia propia. En particular, `reported`, `estimated` y `observed` nunca se promocionan a `measured` sin una ejecución reproducible del pipeline LEONES.

---

## 1. FreeToken — runtime edge-native MoE

**Papel LEONES:** candidato de primera clase para inferencia MoE en hardware de consumo/workstation cuando el conjunto de expertos supera la VRAM disponible.

### Fuente / Descubrimiento

FreeToken se presenta como un motor de serving MoE orientado a hardware heterogéneo. Su diseño trata GPU, CPU, memoria de host e interconexión como recursos de ejecución y adapta la residencia de expertos. El repositorio oficial describe serving de modelos MoE grandes en hardware personal y proporciona CLI, servidor y API compatibles con OpenAI y Anthropic.

### Evidencia

La documentación y el paper describen, entre otros elementos, residencia elástica de expertos, caché LRU, double buffering de transferencias, caching de estados, ejecución adaptada al ancho de banda y gestión dinámica entre KV cache y caché de expertos. El repositorio declara soporte para una familia concreta de checkpoints/modelos y requisitos Linux x86_64 + NVIDIA + CUDA 13 para la ruta documentada.

Las cifras publicadas deben conservar siempre su contexto: modelo, checkpoint, cuantización, GPU, PCIe y workload. No se convierten en rendimiento universal.

### Estimación

Para el selector LEONES, FreeToken debe considerarse especialmente cuando concurren:

- arquitectura MoE;
- working set de expertos superior a la VRAM;
- RAM suficiente;
- ancho de banda host↔GPU/PCIe suficiente;
- CPU capaz de ejecutar la parte asignada;
- workload agentivo o multi-turn donde el caching aporte valor.

La variable conceptual relevante pasa de `VRAM >= model` a una viabilidad conjunta de `VRAM + RAM bandwidth + PCIe + CPU + KV + locality + workload + runtime`.

### Medición LEONES

**Pendiente.** Las cifras del paper son evidencia externa. LEONES debe ejecutar su propio benchmark y registrar al menos TTFT, TPOT/decode tok/s, prefill tok/s, VRAM, RAM, PCIe efectivo, cache hit/miss, CPU/GPU expert placement, warm-up, estabilidad, tool-call latency y resultado agentivo.

### Decisión

**ADOPTAR como runtime candidato**, no como runtime por defecto. Añadir al contrato `runtime-selection.v1` los campos necesarios para evaluar afinidad MoE/interconexión.

---

## 2. El otro FreeToken — referencia nominal FlashML

**Papel LEONES:** ficha independiente para conservar la denominación solicitada y evitar mezclarla con cualquier otro proyecto denominado FreeToken.

### Fuente / Descubrimiento

La referencia es el proyecto oficial `FlashML-org/FreeToken`.

### Evidencia

La evidencia primaria es el repositorio, su documentación y el paper asociado. La documentación actual incluye servidor, APIs OpenAI/Anthropic, integración con agentes de coding y lista de checkpoints conocidos.

### Estimación

La utilidad para LEONES se concentra en MoE edge-native y ejecución bandwidth-adaptive. Las recomendaciones derivadas de documentación externa son hipótesis, no resultados propios.

### Medición LEONES

**Pendiente.** La ficha debe compartir el mismo protocolo de benchmark que FreeToken para evitar duplicar mediciones o crear una segunda semántica.

### Decisión

Mantener la ficha como **alias documental independiente**, pero con una única identidad técnica y una única fuente primaria para evitar duplicación factual.

---

## 3. Odysseus — workspace/harness local-first

**Papel LEONES:** referencia de workspace/harness y capa de interacción/orquestación; no es el sustituto del runtime de inferencia.

### Fuente / Descubrimiento

Odysseus se define como workspace AI autoalojado para chat, agentes, herramientas, investigación, documentos, email, workflows y serving, con orientación local-first/privacy-first.

### Evidencia

La documentación actual muestra integración con hosts/endpoints LLM, Cookbook y rutas de serving. También evidencia que el sistema puede conectarse a Ollama y otros backends y que su Cookbook puede servir modelos mediante rutas específicas. Issues actuales muestran que las capacidades de API y algunos caminos de backend siguen evolucionando.

### Estimación

Odysseus puede servir como referencia para el diseño de experiencias agentivas y para comprobar compatibilidad de endpoints. Sus elecciones de backend no deben convertirse en el selector LEONES ni en una recomendación universal de runtime.

### Medición LEONES

**Pendiente.** Debe evaluarse como workload/harness separado: mismo modelo + mismo endpoint + mismas tareas, midiendo tiempo, éxito, trayectoria, herramientas y estabilidad.

### Decisión

**Adoptar como referencia de workspace/harness**, manteniendo runtime y selección en capas independientes.

---

## 4. LLMFit — preselector de encaje modelo↔hardware

**Papel LEONES:** primera estimación rápida y barata antes de descargar/ejecutar candidatos.

### Fuente / Descubrimiento

LLMFit detecta RAM, CPU, GPU/VRAM y disponibilidad de proveedores de runtime; trabaja con un catálogo de modelos y ofrece TUI, CLI, API, planificación y recomendaciones.

### Evidencia

La fuente oficial documenta detección de hardware, catálogo de modelos, cuantización, MoE, multi-GPU, modos GPU/CPU+GPU/CPU y proveedores como Ollama, llama.cpp, MLX, Docker Model Runner y LM Studio.

### Estimación

LLMFit calcula fit, calidad, velocidad, contexto y selección de cuantización/run mode. Todo resultado procedente de ese cálculo se conserva como **estimated**. Su `estimated_tps` no es `measured_tps`.

### Medición LEONES

LEONES ya dispone de una observación real de LLMFit sobre hardware concreto, pero esa observación valida la ejecución de LLMFit, no el rendimiento de inferencia del runtime recomendado. Para cerrar el ciclo hay que ejecutar el runtime seleccionado y comparar `estimated_tps` frente a `measured_tps`.

### Decisión

**Mantener como front-end de estimación** del selector. Nunca como fuente de verdad ni como benchmark.

---

## 5. AirLLM — runtime memory-constrained

**Papel LEONES:** candidato para escenarios donde el cuello de botella principal es la capacidad de memoria disponible.

### Fuente / Descubrimiento

AirLLM es un proyecto de inferencia orientado a ejecutar modelos grandes mediante estrategias de gestión/offload de memoria.

### Evidencia

La evidencia primaria debe tomarse del repositorio y de la versión concreta instalada. Compatibilidad, precisión, modelo y hardware deben quedar registrados porque las estrategias de memoria no garantizan una misma ruta para todos los checkpoints.

### Estimación

La hipótesis LEONES es que AirLLM puede ampliar el conjunto de modelos ejecutables cuando la VRAM es insuficiente. Eso no implica que sea la opción más rápida ni que el modelo sea operativo para una tarea real.

### Medición LEONES

**Pendiente.** Benchmark mínimo: TTFT, prefill/decode, RAM, VRAM, I/O, contexto, estabilidad y calidad. Debe compararse con al menos un runtime alternativo bajo el mismo protocolo.

### Decisión

**Runtime candidato memory-constrained**, no preselector ni fuente de benchmark.

---

## 6. ODS — despliegue/orquestación de stacks IA

**Papel LEONES:** referencia de despliegue de stacks completos, no sustituto de Atlas, LLMFit ni runtime-selection.

### Fuente / Descubrimiento

ODS se utiliza como plataforma para instalar/conectar componentes de inferencia, UI, voz, agentes, workflows, RAG y otros servicios.

### Evidencia

La evidencia debe mantenerse por componente: instalador, Compose, CLI, autodetección de hardware, backend y configuración efectiva. Una afirmación de que ODS selecciona automáticamente un modelo/backend es evidencia de la conducta documentada del sistema, no una medición de rendimiento.

### Estimación

Las selecciones automáticas de ODS son señales externas de despliegue. LEONES puede usarlas como fuente de hipótesis o como cross-check, pero no debe incorporarlas directamente al score del selector sin contrato explícito.

### Medición LEONES

**Pendiente.** Medir instalación, backend efectivo, configuración, estabilidad y rendimiento posterior en un perfil de hardware concreto.

### Decisión

**Referencia de despliegue/integración**, separada de la capa de selección.

---

## 7. Magnitude — agente + perfilado/inferencia local

**Papel LEONES:** referencia para coding-agent, perfilado de hardware y relación entre agente, modelo e inference engine.

### Fuente / Descubrimiento

Magnitude combina capacidades de agente de coding con ejecución/inferencia local y configuración orientada al hardware.

### Evidencia

La fuente primaria debe conservarse por versión: código, documentación, modelos/runtimes soportados y mecanismos de perfilado/configuración.

### Estimación

Las recomendaciones de hardware/modelo y throughput procedentes de Magnitude se consideran **estimated/reported** según su origen. No se mezclan con `measured` de LEONES.

### Medición LEONES

**Pendiente.** El benchmark debe ser agentivo, no solamente tokens/segundo: trayectoria, outcome, herramientas, latencia, coste y tasa de éxito.

### Decisión

**Candidato de referencia para agentic coding y perfilado**, útil para validar el diseño del selector, pero no autoridad sobre el selector LEONES.

---

## 8. Runtimes locales — capa comparativa

La serie técnica incorporada al conocimiento refuerza una distinción que debe permanecer en LEONES: el runtime no es el modelo. La inferencia depende de hardware, memoria, bandwidth, KV cache, prefill/decode, batching, scheduler, formato de cuantización, interconexión y workload.

### Fuente / Descubrimiento

El radar LEONES conserva runtimes como llama.cpp, MLX/MLX-LM, vLLM, SGLang, TensorRT-LLM, OpenVINO, ONNX Runtime GenAI y otros.

### Evidencia

Cada runtime debe conservar su propia fuente primaria, versión y soporte real de hardware/modelos.

### Estimación

Una tabla de afinidad es una hipótesis inicial. No debe decir que un runtime es "más rápido" sin una medición comparable.

### Medición LEONES

Cada benchmark debe fijar explícitamente: modelo/checkpoint, cuantización, runtime/version, hardware, contexto, entrada/salida, concurrencia y configuración. Medir TTFT, TPOT, throughput, memoria y, cuando corresponda, coste/energía.

### Decisión

`runtime-selection.v1` selecciona una **combinación ejecutable**, no un nombre de runtime aislado.

---

## 9. Benchmarks y evaluaciones

### Fuente / Descubrimiento

Benchmarks externos son fuentes de conocimiento y descubrimiento de candidatos.

### Evidencia

Cada resultado debe conservar benchmark, versión, protocolo, modelo/checkpoint, fecha, hardware y procedencia. Un leaderboard es evidencia externa, no medición LEONES.

### Estimación

Los benchmarks pueden orientar hipótesis de selección y priorización, pero no deben transformarse en scores mezclados con throughput físico sin normalización y contrato.

### Medición LEONES

La medición LEONES debe usar un protocolo congelado y reproducible. Para agentes, medir tarea completa, trayectoria, herramientas, outcome, grader, tiempo y coste además de métricas de inferencia.

### Regla de contaminación

La documentación LLM de Cero a Héroe incorporada al conocimiento establece una regla especialmente importante: una prueba usada repetidamente para optimizar modelo, prompt o scaffold deja de ser una prueba limpia de generalización. LEONES debe separar evaluaciones de desarrollo de evaluaciones de auditoría y conservar el protocolo antes de la medición final.

---

# Contrato de integración definitivo

```text
FUENTE / DESCUBRIMIENTO
        │
        ▼
EVIDENCIA / VERIFICACIÓN
        │
        ▼
ESTIMACIÓN / HIPÓTESIS
        │
        ▼
RECOMMENDATION CANDIDATES
        │
        ▼
selector
        │
        ▼
runtime-selection.v1
        │
        ▼
A01 executor
        │
        ▼
grader
        │
        ▼
runtime benchmark
        │
        ▼
MEDICIÓN LEONES
        │
        ▼
evidence
        │
        ▼
Router
```

## Reglas de no mezcla

- Fuente externa ≠ evidencia verificada.
- Evidencia verificada ≠ estimación.
- Estimación ≠ benchmark.
- Benchmark externo ≠ medición LEONES.
- Medición LEONES ≠ recomendación automática sin quality gate.
- Runtime ≠ modelo.
- Workspace/harness ≠ runtime.
- Preselector ≠ selector final.
- Capacidad de memoria ≠ rendimiento.
- Tokens/segundo ≠ calidad agentiva.

## Resultado de esta auditoría

La web de conocimiento debe consumir `web/data/knowledge.json` como **registro documental único**. Las fichas ampliadas de `docs/sources/` son la documentación profunda y la web es su representación navegable; ninguna de las dos debe crear una quinta capa ni recombinar las cuatro existentes.

El siguiente paso de implementación es conectar los registros de `knowledge.json` con el adaptador `llmfit → recommendation candidates` y, posteriormente, con `runtime-selection.v1`, A01, grader y benchmark, conservando la procedencia de cada transición.
