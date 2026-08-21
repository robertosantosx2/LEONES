# FreeToken — edge-native MoE serving

**Estado en LEONES:** evidencia externa verificada; runtime candidato para benchmark/recomendación; integración ejecutable pendiente de validación en hardware compatible.

**Fuente primaria:** Shuo Yang et al., *FreeToken: Efficient Edge-Native MoE Serving with Bandwidth-Adaptive Execution*, arXiv:2608.16157, v1, 17-08-2026.

- Paper: https://arxiv.org/abs/2608.16157
- HTML: https://arxiv.org/html/2608.16157
- Código: https://github.com/FlashML-org/FreeToken
- Proyecto: https://flashml.ai

## 1. Qué aporta

FreeToken no trata una máquina personal como una GPU pequeña. Trata GPU, CPU, RAM y enlace PCIe como una plataforma de inferencia elástica y adapta dinámicamente dónde se ejecutan y residen los expertos de un MoE.

La arquitectura combina:

1. **Expert residency elástica:** el pool completo de expertos permanece en host memory; una caché LRU compartida mantiene en GPU el working set.
2. **Prefill con double buffering:** mientras la GPU procesa una capa, la siguiente se transfiere por PCIe.
3. **Semantic-aware state caching:** conserva checkpoints en fronteras semánticas de agentes (thinking, tool calls, outputs y turnos) para reducir recomputación después de editar el contexto.
4. **Bandwidth-adaptive execution:** los misses de expertos se dividen entre transferencia PCIe→GPU y ejecución directa en CPU.
5. **q-star policy:** el reparto se deriva de dos anchos de banda medidos en la máquina, no de una regla fija.
6. **Elastic memory management:** el presupuesto entre KV cache y caché de expertos puede reajustarse en runtime sin recargar el pool residente en host.
7. **FTW format:** formato de pesos preparado para el layout interno, reduciendo trabajo de descubrimiento/reempaquetado durante el arranque.
8. **CUDA-graph-compatible execution:** la ruta híbrida CPU/GPU está diseñada para evitar scheduling Python por token.

## 2. Evidencia cuantitativa primaria

La evaluación usa seis sistemas, cuatro cargas agenticas y compara contra llama.cpp, Ollama, KTransformers y MoE-Infinity.

### RTX 4060 Laptop 8 GB

- GPU: RTX 4060 Laptop, 8 GB.
- PCIe: 4.0 x8.
- Ancho de banda host→device medido: 11.8 GB/s.
- Ancho de banda efectivo del kernel MoE de CPU: 47.5 GB/s.
- Modelo: Qwen3.6-35B-A3B, variante NVFP4 para el portátil.
- Resultado: **39.3 tok/s** en la carga de coding-agent SWE/OpenCode.
- El paper indica que esto representa 1.8× al baseline más fuerte en esa configuración y 92% de la tasa de la RTX 4090 medida en el estudio.

### RTX PRO 6000 Blackwell 96 GB

- GPU: RTX PRO 6000 Blackwell, 96 GB.
- PCIe: 5.0 x16.
- Ancho de banda host→device medido: 51.5 GB/s.
- Ancho de banda efectivo CPU-side MoE: 178 GB/s.
- Modelo: **GLM-5.2, 753B parámetros / ~40B activos, NVFP4**.
- Resultado: **14.9 tok/s** en la carga matemática del estudio.
- Baseline llama.cpp: 7.3 tok/s.
- Relación: **2.0×**.
- TTFT medio: 7.5 s frente a 7.8 s de llama.cpp.
- KTransformers no dispone de una ruta ejecutable para este caso según el estudio.

### RTX 5090

- Qwen3.6-35B-A3B: 77–83 tok/s.
- DeepSeek-V4-Flash: 22–25 tok/s.
- Mejora reportada frente al mejor baseline por workload: 1.8–2.3× para Qwen3.6 y 1.5–1.9× para DeepSeek-V4-Flash.
- Peor TTFT reportado por FreeToken: <44 s en todas las cargas; cada baseline supera 150 s en al menos una configuración.

## 3. Qué NO debemos afirmar

La cifra de 14.9 tok/s **sí está respaldada por la fuente primaria**, pero debe citarse como resultado de laboratorio bajo la configuración exacta del paper, no como rendimiento universal de cualquier RTX PRO 6000.

La cifra de 39.3 tok/s también es una medición específica: RTX 4060 Laptop 8 GB, PCIe 4.0 x8, Qwen3.6-35B-A3B NVFP4 y workload de coding-agent definido por los autores.

La afirmación informal «2–4× más rápido que Ollama» no debe incorporarse como regla general. El paper informa comparaciones por modelo, hardware y workload; en algunas configuraciones Ollama no puede servir el modelo evaluado. LEONES conservará los speedups como **evidencia condicionada**, nunca como factor fijo.

## 4. Por qué es especialmente relevante para LEONES

FreeToken cambia el criterio de selección de runtime para MoE grandes. La decisión deja de ser solamente:

`VRAM >= modelo`

para convertirse en:

`modelo + VRAM + bandwidth PCIe + bandwidth RAM + CPU + KV + locality + workload agentic + runtime`

Esto encaja directamente con la arquitectura LEONES de selección de modelos, runtime-selection, benchmark medido y evidence.

### Nuevo tipo de candidato

**Runtime class:** `edge-moe-bandwidth-adaptive`

**Workload affinity:**
- MoE grande que excede VRAM.
- Coding agents.
- Tool calling y sesiones multi-turn.
- Hardware con GPU de consumo/workstation y memoria de host suficiente.
- Casos donde PCIe y RAM pueden explotarse como recursos de inferencia.

**No es primera opción para:**
- modelos densos pequeños que ya caben holgadamente en VRAM;
- serving multiusuario de producción sin validación específica;
- hardware sin CUDA/fast pinned-DMA path compatible;
- escenarios donde la latencia de transferencia sea dominante y no exista suficiente ancho de banda host.

## 5. Integración propuesta en el pipeline LEONES

```text
hardware discovery
    ↓
GPU VRAM + memory bandwidth
CPU + RAM bandwidth
PCIe topology/bandwidth
    ↓
model classifier
    ↓
MoE detection
    ↓
runtime candidates
 ├─ llama.cpp
 ├─ KTransformers
 ├─ AirLLM
 ├─ vLLM/SGLang
 └─ FreeToken  ← nuevo candidato
    ↓
runtime-selection.v1
    ↓
measured benchmark
    ↓
agentic harness
    ↓
grader / evidence
    ↓
router recommendation
```

FreeToken debe recibir del selector al menos:

- GPU model / architecture / VRAM;
- host RAM disponible;
- CPU model / cores;
- measured host-memory bandwidth;
- measured pinned PCIe transfer bandwidth;
- storage throughput;
- model total parameters;
- active parameters;
- expert count / routing characteristics;
- weight format and quantization;
- context length;
- workload class;
- concurrency;
- agent/tool-call pattern.

## 6. Qué debe medir LEONES antes de aceptar una cifra

No copiar los resultados de FreeToken como benchmark propio. Usarlos como **prior externo** y reproducirlos donde sea posible.

### Métricas mínimas

- TTFT p50/p95/p99.
- TPOT / decode tok/s.
- prefill tok/s.
- peak VRAM.
- host RAM utilizada.
- host-memory bandwidth efectiva.
- PCIe H→D bandwidth efectiva.
- cache hit/miss de expertos.
- porcentaje de expertos ejecutados en CPU vs GPU.
- tiempo de carga inicial / warm-up.
- estabilidad con contexto creciente.
- estabilidad multi-turn.
- tool-call latency.
- consumo energético cuando sea posible.
- tasa de éxito del agente y calidad del resultado.

## 7. Benchmark LEONES específico

Crear una matriz `freetoken-agentic-moe` con al menos:

1. Qwen3.6-35B-A3B — 8 GB RTX 4060 Laptop.
2. Qwen3.6-35B-A3B — RTX 5090.
3. DeepSeek-V4-Flash — RTX 5090.
4. GLM-5.2 — RTX PRO 6000 96 GB.

Workloads:

- AIME / razonamiento largo.
- SWE/OpenCode con herramientas.
- Claude-compatible coding-agent multi-turn.
- OpenClaw email/calendar agent.

La comparación debe conservar el mismo modelo/checkpoint, cuantización, prompts, harness y protocolo siempre que sea posible.

## 8. Relación con otros runtimes de LEONES

### KTransformers

FreeToken es especialmente relevante como competidor directo en MoE híbrido CPU/GPU. No debe sustituir KTransformers en la base de conocimiento: debe competir contra él mediante benchmarks reproducibles.

### llama.cpp

El paper ofrece una comparación primaria muy clara para GLM-5.2: 14.9 vs 7.3 tok/s en la RTX PRO 6000. Esta es una excelente celda de validación para LEONES.

### AirLLM

AirLLM y FreeToken comparten la idea general de reducir el requisito de memoria GPU mediante movimiento de pesos, pero la arquitectura y objetivo son distintos. AirLLM queda como runtime memory-constrained general; FreeToken como runtime especializado en MoE + agentes + adaptación a bandwidth.

### vLLM / SGLang

FreeToken reutiliza conceptos de su ecosistema (Paged KV/radix prefix reuse y componentes de kernels), pero su objetivo es edge MoE donde el pool de expertos excede VRAM. LEONES debe evaluar ambos en las mismas cargas cuando exista una ruta ejecutable comparable.

### LLMFit / Magnitude

FreeToken debe incorporarse al catálogo de runtimes que el recomendador puede proponer, pero **no** debe ser seleccionado solo porque el modelo quepa por capacidad. El selector necesita un criterio adicional de `host_gpu_interconnect_viability` y `moe_edge_affinity`.

## 9. Estado de evidencia

- **Primary evidence:** paper arXiv v1, 17-08-2026.
- **Code:** repositorio oficial indicado por el paper.
- **Reproducibility:** pendiente de ejecutar en el entorno LEONES.
- **Recommendation status:** candidato experimental, no aún runtime por defecto.
- **Claim strength:** alta para las cifras publicadas; no extrapolar fuera de hardware/modelo/workload.

## 10. Decisión LEONES

**ADOPTAR FreeToken como runtime candidato de primera clase para MoE edge/consumer, incorporar sus variables de hardware al selector y crear una suite de benchmark agentic específica.**

La innovación que LEONES debe conservar como conocimiento operativo es que el rendimiento depende de la relación dinámica entre **VRAM, RAM bandwidth, PCIe bandwidth, CPU execution bandwidth, expert locality y patrón de agente**, no solamente de la capacidad de VRAM.
