# Informe de Infraestructura de IA Local: herramientas y modelos para hardware de consumo (edición 2026)

> Fuente aportada por el usuario para el conocimiento de LEONES. Este documento es una **fuente de prospección y análisis**, no una lista de hechos verificados.

## 1. Propósito dentro de LEONES

Este informe se incorpora como mapa estratégico del ecosistema de inferencia local de 2026. Su utilidad principal es descubrir proyectos, motores, formatos de cuantización, arquitecturas y patrones de despliegue que deben pasar posteriormente por el sistema de evidencia de LEONES.

### Regla de calidad

Los datos concretos del informe —versiones, licencias, velocidades, tamaños, compatibilidades, benchmarks, afirmaciones de eficiencia y características de modelos— se consideran inicialmente `reported` o `unknown`, según pueda verificarse la procedencia. **No se convierten automáticamente en `measured` ni `verified`.**

```text
INFORME APORTADO
      ↓
PROSPECCIÓN
      ↓
FUENTE PRIMARIA
      ↓
ATLAS / EVIDENCIA
      ↓
QUALITY GATE
      ↓
MEDICIÓN LEONES
```

## 2. Tesis estratégica

El informe identifica tres motores de la inferencia local:

1. control del coste de inferencia;
2. soberanía y privacidad de los datos;
3. aumento de la capacidad de los modelos de pesos abiertos.

Para LEONES, estas tesis deben contrastarse separadamente. Coste, privacidad, apertura y rendimiento son dimensiones distintas y no deben reducirse a una sola puntuación.

## 3. Proyectos y tecnologías a incorporar al radar

| Proyecto / tecnología | Papel potencial en LEONES | Prioridad de verificación |
|---|---|---|
| Rabbit | Inferencia de MoE muy grandes mediante streaming desde SSD | Alta |
| Lemonade | Inferencia multimodal/NPU, especialmente AMD Ryzen AI | Alta |
| llama.cpp | Runtime fundamental; GGUF y CPU/edge | Crítica |
| ODS | Despliegue de stack local completo | Crítica; ya integrado |
| Ollama | Runtime/UX multiplataforma | Alta |
| KoboldCpp | Runtime CPU/GPU doméstico y contexto | Media |
| MLX / MLX-LM | Apple Silicon / memoria unificada | Alta |
| vLLM | Servidor de alto throughput | Alta |
| Fox | Servidor local asociado a Rabbit | Media; verificar estado independiente |
| Colibrì | Runtime especializado para GLM | Alta; verificar proyecto y claims |
| GPT4All | UX local multiplataforma | Media |
| ExLlamaV2 | Inferencia cuantizada NVIDIA / EXL2 | Alta |
| llamafile | Distribución portable de modelos/runtime | Alta |
| LocalAI | API compatible con OpenAI y multimodalidad local | Alta |
| Jan | Desktop local-first | Media |
| AutoGPTQ | Cuantización GPTQ / legado y evolución | Media; verificar estado actual |
| AnythingLLM | RAG local / productividad | Alta |
| Aphrodite Engine | Serving para GPUs de consumo | Media/Alta |
| Tabby | Coding assistant local | Alta |
| text-generation-webui | Banco de pruebas/experimentación de LLM locales | Alta |
| SGLang | Serving y optimización de atención/caché | Alta |
| TGI | Serving de Hugging Face | Alta |
| TensorRT-LLM | Optimización NVIDIA | Alta |
| DirectKV | KV-cache / zero-copy | Alta; verificar madurez y hardware objetivo |

## 4. Formatos y técnicas que interesan especialmente

### GGUF / K-Quants

Debe mantenerse como eje del ecosistema CPU/consumer junto con llama.cpp, pero LEONES debe verificar compatibilidad y rendimiento por modelo/runtime en vez de asumir que todos los GGUF son equivalentes.

### AWQ / GPTQ / EXL2

Son relevantes para GPUs de consumo, pero su beneficio depende de arquitectura, backend, kernel, VRAM y versión del runtime.

### FP8 / INT4 / MXFP4

La cuantización debe registrarse como una propiedad de la ejecución, no solo del modelo. Para MoE interesa además saber si se cuantizan todos los pesos, expertos, activaciones o KV cache.

### Streaming de expertos

Rabbit se identifica como una línea de investigación particularmente interesante para LEONES: desacoplar capacidad total del modelo de la RAM disponible mediante streaming de expertos desde NVMe. La afirmación de que puede ejecutar modelos MoE de escala extrema debe tratarse como hipótesis hasta reproducirse o verificarse con fuente primaria.

### Zero-copy KV / offload

DirectKV representa otra línea de investigación: reducir el coste de mover KV cache entre memoria de CPU y GPU. Deben medirse TTFT, throughput, consumo de VRAM, ancho de banda y coste de transferencia.

## 5. Hardware de consumo frente a enterprise

El informe destaca la diferencia entre ancho de banda de memoria de sistemas de consumo y HBM enterprise. Para LEONES, esta diferencia debe convertirse en variables medibles:

- ancho de banda de memoria;
- latencia de memoria;
- VRAM y RAM disponibles;
- PCIe;
- rendimiento de almacenamiento;
- CPU SIMD;
- GPU/NPU;
- transferencia CPU↔GPU;
- consumo energético;
- temperatura y throttling.

La evaluación de hardware debe evitar reglas universales del tipo "más TFLOPS = más tokens/s": el cuello de botella depende del modelo, cuantización, contexto y runtime.

## 6. Motores de inferencia

El informe clasifica aproximadamente el ecosistema en tres grupos:

### Alto throughput / serving

- vLLM
- SGLang
- TensorRT-LLM
- TGI
- Aphrodite Engine

### Hardware restringido / consumer / CPU

- llama.cpp
- Ollama
- KoboldCpp
- LocalAI
- GPT4All
- llamafile
- ExLlamaV2

### Orquestación / experiencia / aplicaciones

- ODS
- AnythingLLM
- Jan
- Tabby
- text-generation-webui

LEONES debe conservar esta taxonomía como hipótesis de trabajo y revisarla mediante evidencia actual.

## 7. Modelos mencionados

El informe señala familias como Qwen, Llama, Gemma, Phi, Mistral, Devstral, gpt-oss, DeepSeek y Kimi/GLM. No se debe importar directamente al Atlas ninguna cifra de parámetros, licencia, contexto o benchmark contenida en el informe sin contrastarla con una fuente primaria.

Especial atención a:

- **gpt-oss** — verificar licencia, tamaños, requisitos y rendimiento real;
- **DeepSeek** — verificar denominaciones y disponibilidad reales de las variantes citadas;
- **Devstral** — relevante para agentes de coding;
- **Llama 4 Scout** — verificar contexto y condiciones de licencia;
- **Phi** — especialmente interesante para CPU/edge;
- **Qwen** — relevante para diferentes escalas y agentes;
- **Kimi / GLM** — candidatos para investigación de MoE y runtimes especializados.

## 8. Matriz de selección de hardware

El informe propone como orientación inicial:

| Hardware | Candidato orientativo |
|---|---|
| Portátil 16 GB | Phi pequeño / Gemma pequeño |
| GPU 24 GB | Gemma/Devstral de escala media |
| 48 GB VRAM | Qwen/gpt-oss de escala media |
| Servidor privado | MoE grandes con cuantización |

Estas recomendaciones **no se incorporan como recomendaciones finales de LEONES**. Deben pasar por LLMFit → Atlas → benchmark.

## 9. Reglas estratégicas que sí se incorporan

### Evitar model-chasing

La utilidad de un modelo debe medirse por tarea, latencia, coste y calidad, no por tamaño bruto.

### Separar despliegue local de API privada

Un servicio privado de terceros no equivale a soberanía física del hardware. LEONES debe registrar el modo de ejecución.

### Cuantización como variable experimental

Q4/FP8 pueden ser excelentes opciones, pero no deben declararse universalmente como "óptimas". El benchmark debe comparar calidad, velocidad, memoria y estabilidad.

### LLMFit como filtro inicial

Este informe refuerza el papel ya establecido de LLMFit:

```text
hardware → LLMFit → candidatos → Atlas → runtime/quant → benchmark → medición
```

## 10. Fuentes primarias que deben verificarse

- Rabbit: https://github.com/ferrumox/rabbit
- Lemonade: https://github.com/lemonade-sdk/lemonade
- llama.cpp: https://github.com/ggml-org/llama.cpp
- ODS: https://github.com/Osmantic/ODS
- Ollama: https://ollama.com/
- KoboldCpp: https://github.com/LostRuins/koboldcpp
- MLX: https://github.com/ml-explore/mlx
- vLLM: https://github.com/vllm-project/vllm
- ExLlamaV2: https://github.com/turboderp/exllamav2
- llamafile: https://github.com/Mozilla-Ocho/llamafile
- LocalAI: https://github.com/mudler/LocalAI
- Jan: https://github.com/janhq/jan
- AnythingLLM: https://github.com/Mintplex-Labs/anything-llm
- Aphrodite Engine: https://github.com/aphrodite-engine/aphrodite-engine
- Tabby: https://github.com/TabbyML/tabby
- text-generation-webui: https://github.com/oobabooga/text-generation-webui
- SGLang: https://github.com/sgl-project/sglang
- TGI: https://github.com/huggingface/text-generation-inference
- TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM

## 11. Siguiente trabajo derivado

1. Crear/actualizar fichas de cada runtime en Atlas.
2. Verificar repositorios, licencias y estado de mantenimiento.
3. Extraer hardware soportado y formatos de cuantización.
4. Identificar benchmarks reproducibles.
5. Incorporar candidatos al Prospector.
6. Cruzarlos con LLMFit.
7. Ejecutar benchmarks LEONES sobre hardware representativo.
8. Promover únicamente evidencia que supere el quality gate.

**Conclusión:** este informe queda incorporado como **fuente de conocimiento estratégico y de prospección**. No se trata como dataset factual verificado. Su principal valor para LEONES es ampliar el radar de runtimes, técnicas de eficiencia de memoria, modelos y estrategias de despliegue local que después pueden ser verificadas y medidas.
