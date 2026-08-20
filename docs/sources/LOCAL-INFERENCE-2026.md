# Informe de Infraestructura de IA Local: herramientas y modelos para hardware de consumo (edición 2026)

> Fuente aportada para el conocimiento de LEONES. Este documento es una **fuente de prospección y análisis**, no una lista de hechos verificados.

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

La lista original del informe se conserva como punto de partida. El estado resultante de la comprobación individual está en [`LOCAL-INFERENCE-2026-VERIFICATION.md`](LOCAL-INFERENCE-2026-VERIFICATION.md) y la decisión de promoción en [`LOCAL-INFERENCE-2026-CANDIDATES.md`](LOCAL-INFERENCE-2026-CANDIDATES.md).

| Proyecto / tecnología | Papel potencial en LEONES | Estado tras verificación |
|---|---|---|
| Rabbit | Inferencia MoE con streaming desde SSD | `verified-primary` |
| Lemonade | Inferencia local GPU/NPU | `verified-primary` |
| llama.cpp | Runtime fundamental; GGUF y CPU/edge | `verified-primary` |
| ODS | Despliegue de stack local completo | `verified-primary` / integración propia |
| Ollama | Runtime/UX multiplataforma | `verified-primary` |
| KoboldCpp | Runtime CPU/GPU doméstico | `verified-primary` |
| MLX / MLX-LM | Apple Silicon / memoria unificada | `verified-primary` |
| vLLM | Servidor de alto throughput | `verified-primary` |
| Fox | Servidor asociado a Rabbit | `unresolved` |
| Colibrì | Runtime especializado | `verified-primary` |
| GPT4All | UX local multiplataforma | `verified-primary` |
| ExLlamaV2 | Inferencia cuantizada NVIDIA / EXL2 | `archived` |
| llamafile | Distribución portable | `verified-primary` |
| LocalAI | API compatible con OpenAI y multimodalidad local | `verified-primary` |
| Jan | Desktop local-first | `verified-primary` |
| AutoGPTQ | Cuantización GPTQ / legado | `archived` |
| AnythingLLM | RAG local / productividad | `verified-primary` |
| Aphrodite Engine | Serving para GPUs de consumo | `verified-primary` |
| Tabby | Coding assistant local | `verified-primary` |
| text-generation-webui | Banco de pruebas/experimentación | `verified-primary` |
| SGLang | Serving y optimización | `verified-primary` |
| TGI | Serving de Hugging Face | `archived` |
| TensorRT-LLM | Optimización NVIDIA | `verified-primary` |
| DirectKV | KV-cache / zero-copy | `unresolved` |

## 4. Formatos y técnicas que interesan especialmente

### GGUF / K-Quants

Debe mantenerse como eje del ecosistema CPU/consumer junto con llama.cpp, pero LEONES debe verificar compatibilidad y rendimiento por modelo/runtime en vez de asumir que todos los GGUF son equivalentes.

### AWQ / GPTQ / EXL2

Son relevantes para GPUs de consumo, pero su beneficio depende de arquitectura, backend, kernel, VRAM y versión del runtime.

### FP8 / INT4 / MXFP4

La cuantización debe registrarse como una propiedad de la ejecución, no solo del modelo. Para MoE interesa además saber si se cuantizan todos los pesos, expertos, activaciones o KV cache.

### Streaming de expertos

Rabbit se identifica como una línea de investigación particularmente interesante para LEONES: desacoplar capacidad total del modelo de la RAM disponible mediante streaming de expertos desde NVMe. Las cifras de rendimiento y capacidad se conservan como claims/evidencia del proyecto hasta que exista reproducción independiente.

### Zero-copy KV / offload

DirectKV representa una línea de investigación potencial para reducir el coste de mover KV cache entre memoria de CPU y GPU. Como la entidad no ha quedado resuelta documentalmente en esta pasada, no se promociona ni se usa para recomendaciones.

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
- TGI *(histórico: archivado)*
- Aphrodite Engine

### Hardware restringido / consumer / CPU

- llama.cpp
- Ollama
- KoboldCpp
- LocalAI
- GPT4All
- llamafile
- ExLlamaV2 *(histórico: archivado)*

### Orquestación / experiencia / aplicaciones

- ODS
- AnythingLLM
- Jan
- Tabby
- text-generation-webui

Esta taxonomía es orientativa y no constituye un ranking.

## 7. Modelos mencionados

El informe señala familias como Qwen, Llama, Gemma, Phi, Mistral, Devstral, gpt-oss, DeepSeek y Kimi/GLM. No se importa directamente al Atlas ninguna cifra de parámetros, licencia, contexto o benchmark contenida en el informe sin contrastarla con una fuente primaria.

Los resultados de la primera verificación documental están en [`LOCAL-INFERENCE-2026-VERIFICATION.md`](LOCAL-INFERENCE-2026-VERIFICATION.md).

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

Q4/FP8 pueden ser buenas opciones, pero no deben declararse universalmente como óptimas. El benchmark debe comparar calidad, velocidad, memoria y estabilidad.

### LLMFit como filtro inicial

Este informe refuerza el papel ya establecido de LLMFit:

```text
hardware → LLMFit → candidatos → Atlas → runtime/quant → benchmark → medición
```

## 10. Fuentes primarias

Las URLs originales del informe son referencias de descubrimiento. La verificación uno a uno y el estado actual de cada entidad quedan centralizados en [`LOCAL-INFERENCE-2026-VERIFICATION.md`](LOCAL-INFERENCE-2026-VERIFICATION.md), evitando duplicar afirmaciones que puedan quedar obsoletas.

## 11. Trabajo derivado

1. Mantener fichas de runtimes y modelos que hayan superado identidad primaria.
2. Cruzarlos con LLMFit.
3. Identificar hardware, cuantización y runtime concretos.
4. Ejecutar benchmarks LEONES reproducibles.
5. Promover a `measured` únicamente resultados obtenidos físicamente.
6. Retirar o marcar como archivadas las tecnologías que pierdan mantenimiento.
7. Mantener `unresolved` fuera de recomendaciones y registros canónicos.

**Conclusión:** este informe queda incorporado como **fuente de conocimiento estratégico y de prospección**. Su valor para LEONES es ampliar el radar de runtimes, técnicas de eficiencia de memoria, modelos y estrategias de despliegue local; la verdad operativa se obtiene después mediante fuentes primarias, quality gate y medición.
