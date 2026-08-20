# Candidatos de prospección — Infraestructura IA local 2026

Estos proyectos han sido incorporados al radar de prospección de LEONES a partir de `LOCAL-INFERENCE-2026.md`.

**Estado inicial de todos:** `candidate / unverified`.

No son todavía componentes de LEONES, ni recomendaciones, ni hechos verificados. El objetivo de esta lista es que Prospector/Atlas los someta al mismo proceso de identidad, licencia, mantenimiento, hardware, cuantización, benchmarks y utilidad.

## Runtimes / inferencia

| Proyecto | Repositorio | Prioridad | Qué debemos verificar |
|---|---|---:|---|
| Rabbit | https://github.com/ferrumox/rabbit | P0 | estado, licencia, arquitectura MoE, streaming NVMe, claims de Kimi/GLM |
| Lemonade | https://github.com/lemonade-sdk/lemonade | P0 | licencia, backends, NPU/GPU AMD, modelos y benchmarks |
| llama.cpp | https://github.com/ggml-org/llama.cpp | P0 | versión, licencia, GGUF, backends y benchmarks CPU/consumer |
| Ollama | https://github.com/ollama/ollama | P1 | licencia, backend, modelos, gestión hardware y API |
| KoboldCpp | https://github.com/LostRuins/koboldcpp | P1 | licencia, CPU/GPU, GGUF y gestión de contexto |
| MLX / MLX-LM | https://github.com/ml-explore/mlx | P0 | licencia, Apple Silicon, cuantización y benchmarks |
| vLLM | https://github.com/vllm-project/vllm | P0 | backends consumer, throughput y compatibilidad |
| ExLlamaV2 | https://github.com/turboderp/exllamav2 | P1 | estado, EXL2, NVIDIA y rendimiento |
| llamafile | https://github.com/Mozilla-Ocho/llamafile | P1 | estado, licencia y portabilidad |
| LocalAI | https://github.com/mudler/LocalAI | P1 | API, backends, multimodalidad y hardware |
| SGLang | https://github.com/sgl-project/sglang | P0 | RadixAttention, serving, hardware y benchmarks |
| TGI | https://github.com/huggingface/text-generation-inference | P1 | estado, soporte de hardware y serving |
| TensorRT-LLM | https://github.com/NVIDIA/TensorRT-LLM | P1 | licencia, hardware NVIDIA, cuantización y rendimiento |
| Aphrodite Engine | https://github.com/aphrodite-engine/aphrodite-engine | P1 | estado, relación con vLLM, GPUs consumer y serving |
| text-generation-webui | https://github.com/oobabooga/text-generation-webui | P1 | estado, licencia, loaders y formatos |

## Servidores / aplicaciones / agentes

| Proyecto | Repositorio | Prioridad | Qué debemos verificar |
|---|---|---:|---|
| Fox | https://github.com/ferrumox/rabbit/tree/fox | P2 | si es componente independiente, licencia, API y mantenimiento |
| GPT4All | https://github.com/nomic-ai/gpt4all | P1 | repositorio canónico, licencia, runtime y hardware |
| Jan | https://github.com/janhq/jan | P1 | licencia, runtimes, offline y extensiones |
| AnythingLLM | https://github.com/Mintplex-Labs/anything-llm | P1 | licencia, RAG, backends y despliegue local |
| Tabby | https://github.com/TabbyML/tabby | P1 | licencia, coding, modelos y latencia |

## Técnicas / proyectos de investigación

| Proyecto | Referencia | Prioridad | Qué debemos verificar |
|---|---|---:|---|
| DirectKV | fuente indicada en el informe; identificar repositorio primario | P0 | existencia/estado, licencia, zero-copy KV, hardware GH200/GB200 y benchmarks |
| Colibrì | referencia indicada como parte de Rabbit | P0 | existencia independiente, código, licencia, alcance y claims |
| AutoGPTQ | https://github.com/AutoGPTQ/AutoGPTQ | P2 | estado actual, relación con llm-compressor, licencia y relevancia |

## Modelos que pasan al radar de verificación

Estos modelos/familias también entran como **candidatos de conocimiento**, no como registros verificados:

- Qwen3
- gpt-oss
- Gemma 3
- Phi-4-mini
- Devstral
- Llama 4 Scout
- Mistral Small 3.1
- Kimi / variantes citadas en Rabbit
- GLM / variantes citadas en Rabbit
- DeepSeek / variantes citadas en el informe

Cada uno debe contrastarse en Atlas contra su fuente primaria y registrar identidad, licencia, pesos, arquitectura, contexto, cuantización disponible, hardware objetivo y benchmarks.

## Orden de ejecución

```text
P0 → identidad + repositorio + licencia + estado
 ↓
P0 → hardware / backend / cuantización
 ↓
P0 → benchmarks reproducibles
 ↓
P1 → integración con Prospector
 ↓
LLMFit → primera estimación de encaje
 ↓
Atlas → evidencia canónica
 ↓
LEONES benchmark → medición física
 ↓
Recommender → posible recomendación
```

## Regla de promoción

Un candidato solo puede promocionarse a conocimiento verificado cuando supera el quality gate correspondiente. En particular:

- un repositorio descubierto ≠ software recomendado;
- una licencia declarada ≠ licencia verificada;
- un benchmark externo ≠ medición LEONES;
- una estimación de LLMFit ≠ rendimiento medido;
- una afirmación de fabricante ≠ hecho independiente.

La lista se mantendrá como cola de prospección hasta completar las verificaciones.
