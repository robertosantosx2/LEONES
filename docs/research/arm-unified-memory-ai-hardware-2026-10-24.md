# Hardware ARM con memoria unificada para inferencia local de IA
## Investigación técnica y plan de validación LEONES — 24 de octubre de 2026

**Estado:** investigación documental basada exclusivamente en fuentes públicas; no se realizarán pruebas físicas de hardware para este estudio. Los datos de terceros se marcan como *PUBLISHED*, las estimaciones calculadas como *ESTIMATED* y nunca como *MEASURED por LEONES*.  
**Rama:** `research/arm-unified-memory-ai-2026-10`  
**Objetivo:** elaborar una comparativa documental de coste por tokens/s y tokens/s de los mejores modelos elegibles según Artificial Analysis para cada plataforma, priorizando Radxa Orion O6 de 64 GB y NVIDIA Jetson AGX Orin. Toda conclusión debe proceder de fuentes públicas trazables; no se comprarán equipos ni se harán pruebas físicas para este estudio.

## Resumen ejecutivo

1. **Radxa Orion O6 64 GB** es la opción de investigación abierta con mejor combinación de RAM unificada, expansión PCIe y precio de referencia. Tiene CPU CIX P1 ARMv9, GPU Arm Immortals G720 MC10, NPU anunciada de 30 TOPS, 64 GB LPDDR5 y PCIe Gen4 x8 físico. El precio de venta recomendado publicado en la presentación oficial fue 539 USD para la variante de 64 GB; no se ha confirmado una oferta final entregada en España con IVA, transporte y aduanas incluidos.
2. **Jetson AGX Orin 32 GB** es la ruta más sólida para validar motores CUDA ARM64 y gestión de memoria compartida. El fork `calvinvette/strata-inference-orin` publica pruebas reales en AGX Orin de 32 GB con JetPack 6.2/CUDA 12.6 y modelo GGUF MoE. Es evidencia más útil que una tabla TOPS comercial.
3. **Jetson AGX Orin Developer Kit 64 GB** tiene precio oficial anunciado de 3.499 USD; un distribuidor europeo puede cobrar bastante más. El kit de desarrollo de 64 GB conserva el rendimiento del kit original de 32 GB, según NVIDIA; no debe confundirse con las especificaciones del módulo de producción de 64 GB.
4. **No hay aún una comparación controlada Radxa O6 vs Jetson Orin** con el mismo modelo, cuantización, contexto, número de tokens, versiones de software y medición de pared. No se asignan tokens/s ni tokens/J a Radxa sin datos verificables.
5. Para LEONES, separar **PUBLISHED** (terceros, con fuente) y **ESTIMATED** (cálculo derivado de fuentes, con fórmula y supuestos). **No habrá categoría MEASURED por LEONES en este estudio**, porque no se realizarán pruebas físicas. Las cifras publicadas no deben convertirse en resultados propios.

## 7. Experiencias, proyectos y planes de futuro en repositorios públicos (consulta exhaustiva 24-10-2026)

Búsqueda realizada en GitHub, Hugging Face, ModelScope (China), Gitee, GitCode/AtomGit y repositorios de fabricantes/comunidad. Codeberg mostró actividad residualmente baja para este tema. Fecha de consulta: 24 de octubre de 2026.

### 7.1 Radxa Orion O6 / CIX P1 (CD8180) – NPU Zhouyi X2 / Sky1

**Proyectos y evidencia clave:**

| Repositorio / Fuente | Descripción | Datos publicados | Implicación |
|---|---|---|---|
| [Reonarudo/tinygrad-npu-examples](https://github.com/Reonarudo/tinygrad-npu-examples) | LLMs (Ternary Bonsai 2 27B, Qwen3.8-27B, Ornith 9B) y generación de imagen en Zhouyi X2 NPU vía tinygrad backend ZHOUYI. Servidor compatible OpenAI/Ollama. | ~2,1–6,8 tok/s con speculative decoding (depende de modelo y prompt). Ternary Bonsai 2 27B ~6,2 tok/s; Qwen3.8-27B ~2,2 tok/s. | Evidencia más avanzada de LLM real en la NPU. Demuestra viabilidad de capas transformer (incluso ternarias), aunque throughput bajo frente a GPU/CPU optimizada. |
| [byrantech/frigate-oriono6-npu](https://github.com/byrantech/frigate-oriono6-npu) | Frigate con NPU CIX para detección de objetos (YOLOX). | ~40 ms inference en 1080p con yolox_m.cix. | Confirma drivers runtime funcionales y uso productivo de la NPU fuera de LLM. |
| [geerlingguy/ai-benchmarks #13](https://github.com/geerlingguy/ai-benchmarks/issues/13) y [sbc-reviews #62](https://github.com/geerlingguy/sbc-reviews/issues/62) | Benchmarks Ollama/llama.cpp en CPU y firmware. | Llama-3.2-3B: 9–16,5 tok/s; Llama-3.1-8B: 5–7,6 tok/s; DeepSeek-R1 1.5B ~14 tok/s. Firmware 9.0.0 mejoró rendimiento. | Baseline CPU realista; modelos >13B justos o limitados por memoria en configs bajas. |
| [cixtech/cix-linux-main #20](https://github.com/cixtech/cix-linux-main/issues/20) (Jason Perlow et al.) | Aclaración oficial de CIX sobre el NPU. | NPU Zhouyi **no diseñada para decode autoregresivo de LLM** (KV-cache dinámico). Orientada a embeddings, clasificadores, rerankers y agentes (encoder-only). Recomendación: LLM en Mali-G720 vía Vulkan + NPU para memoria semántica. | Corrección de framing importante: la NPU no es “GPU de LLM”. Arquitectura de tres tiers: NPU (embeddings), GPU Vulkan (decode), CPU (orquestación). |
| ModelScope `cix/ai_model_hub_*` | Hub oficial de modelos optimizados CIX. | Modelos de visión, embeddings y algunos cuantizados; pocos LLM grandes. | Ecosistema de modelos disponible, centrado en workloads estáticos. |
| [minisforum-docs/MS-R1-Docs #20](https://github.com/minisforum-docs/MS-R1-Docs/issues/20) | Experiencias en MS-R1 (misma familia CIX). | LLM solo en CPU (llama.cpp); NPU operativa para ONNX/Zhouyi de referencia pero no para transformers dinámicos. | Confirma limitaciones estructurales del compilador Compass NN (static-graph). |

**Planes de futuro detectados:**
- Comunidad empujando Vulkan en Mali-G720 + tinygrad/NPU híbrido.
- CIX enfatiza arquitectura “agentic” (NPU para embeddings + GPU/CPU para razonamiento).
- Drivers y firmware en evolución continua (ACPI, mainline kernel, Windows drivers incompletos).
- BredOS y otros proyectos de imágenes comunitarias documentan estado de drivers (GPU/NPU aún parcial en mainline).

### 7.2 NVIDIA Jetson AGX Orin (32/64 GB)

**Proyectos y evidencia clave:**

| Repositorio / Fuente | Descripción | Datos publicados | Implicación |
|---|---|---|---|
| [calvinvette/strata-inference-orin](https://github.com/calvinvette/strata-inference-orin) | Port de motor Strata a Jetson Orin (ARM64/CUDA). | Qwen3.8-Flash-Next: decode mediano 18,6–21,6 tok/s; prefill 37,8–52,5 tok/s (prompts cortos). Contexto largo degrada decode a ~6,6 tok/s. | Evidencia ARM64/CUDA más detallada para MoE grandes. |
| [NVIDIA/TensorRT-Edge-LLM](https://github.com/NVIDIA/TensorRT-Edge-LLM) | Documentación oficial de rendimiento (v0.9–0.10). | Tablas de prefill/decode en AGX Orin 64 GB para Qwen3, Nemotron, VLMs con INT4 AWQ, EAGLE3 speculative. Decode típico 30–60+ tok/s en modelos medianos; más alto con batch y speculative. | Camino oficial NVIDIA para edge LLM. |
| [thehighnotes/vllm-jetson-orin](https://huggingface.co/thehighnotes/vllm-jetson-orin) (Hugging Face) | Wheel de vLLM precompilado con kernels Marlin GPTQ para SM 8.7. | Prefill hasta 3,8× vs llama.cpp genérico; decode ~30–40 % mejor en algunos casos (Qwen3.5-35B-A3B). | Solución práctica de instalación y gains medibles. |
| LaraAI-Labs y otros en Hugging Face | Engines TensorRT-Edge precompilados (Qwen3-4B INT4, etc.). | Prefill ~2400 tok/s, decode ~57 tok/s en Qwen3-4B (Orin 64 GB). | Artefactos listos para usar. |
| ggml-org/llama.cpp issues/discussions | Múltiples hilos de rendimiento CUDA, regresiones, VLMs, power modes. | Comparaciones con Mac, impacto de MAXN vs modos de bajo consumo, regresiones de ~10 % en algunos commits. | Comunidad activa manteniendo compatibilidad. |

**Planes de futuro:**
- TensorRT-Edge-LLM es el camino oficial de NVIDIA para edge (el equipo principal de TensorRT-LLM se centra en datacenter).
- Comunidad mantiene vLLM, llama.cpp y forks Strata muy activos.

### 7.3 AMD Ryzen AI Max+ / Strix Halo / Gorgon Halo (128–192 GB)

Ecosistema muy activo en GitHub a octubre 2026:

| Repositorio | Descripción | Datos destacados |
|---|---|---|
| [botAGI/strix-halo-multislot](https://github.com/botAGI/strix-halo-multislot) | Multi-slot LLM inference (hasta 32 streams). | 236 tok/s agregados (Gemma 4 26B A4B); ~90 tok/s single-stream con MTP. |
| [visorcraft/strix-halo-llm-perf](https://github.com/visorcraft/strix-halo-llm-perf) | Benchmarks y setup reproducible. | Qwen3 30B-A3B ~86 tok/s; modelos más grandes 20–50+ tok/s. |
| [lazarevtill/strix-halo-llm](https://github.com/lazarevtill/strix-halo-llm) | Tuning Vulkan + catálogo de bugs de medición. | Límites reales de memoria (~109 GB usable); análisis de techo de bandwidth. |
| [hogeheer499-commits/strix-halo-guide](https://github.com/hogeheer499-commits/strix-halo-guide) | Guía basada en evidencia (Qwen3.8, Ollama, llama.cpp, Vulkan/ROCm). | Alta popularidad (cientos de stars). |
| [pepuscz/strix-halo-llm](https://github.com/pepuscz/strix-halo-deepseek-v4-flash) | Recetas Ansible + benchmarks de calidad. | Setups ganadores para Qwen y DeepSeek con 256K–512K contexto. |
| [ihanesman/strix-halo-windows-llm-bench](https://github.com/ihanesman/strix-halo-windows-llm-bench) | Benchmarks bajo Windows. | Impacto de backends, speculative decoding y throttle por display-off. |
| [GaelicThunder/gb10-uma-inference-notes](https://github.com/GaelicThunder/gb10-uma-inference-notes) | Análisis de propiedades UMA en GB10. | Hallazgos sobre bandwidth-saturated storage, host→device copies inútiles (+63 %), RAM bandwidth como techo final. |
| [DG1001/local-agentic-coding-128gb](https://github.com/DG1001/local-agentic-coding-128gb) | Benchmarks agentic coding en 128 GB UMA. | Modelos grandes (DeepSeek-V4-Flash, Qwen3.6, etc.) pasando tests de coding localmente. |

**Planes de futuro:** fuerte foco en ROCm/Vulkan optimizado, multi-slot, speculative decoding y uso de NPU XDNA para embeddings/agentes. Comunidad documentando “qué funciona de verdad” frente a claims de marketing.

### 7.4 Plataformas chinas (ModelScope, Gitee, GitCode/AtomGit)

- **ModelScope**: Hub oficial CIX (`cix/ai_model_hub_*`) con modelos optimizados para NPU Zhouyi (visión, embeddings, algunos LLM cuantizados). OrionStarAI publica modelos Orion-14B (no específicos de hardware O6).
- **Gitee / GitCode**: Espejos de proyectos OpenHarmony para CIX/Radxa, ipex-llm (Intel) y herramientas generales. Actividad de LLM de alto throughput en NPU CIX más baja que en GitHub.
- Poca evidencia pública de grandes proyectos de inferencia LLM de alto throughput en CIX fuera de los repositorios ya citados en GitHub.

### 7.5 Síntesis de madurez y brechas

| Plataforma | Nivel de evidencia pública | Proyectos destacados | Estado NPU/acelerador para LLM | Madurez software | Planes de futuro visibles |
|---|---|---|---|---|---|
| Radxa Orion O6 / CIX | Media-Baja | tinygrad-npu-examples, Frigate, Geerling | Limitada (embeddings + capas estáticas) | Drivers en evolución | Híbrido NPU+Vulkan + agentic stack |
| Jetson AGX Orin | Alta | TensorRT-Edge-LLM, strata-inference-orin, vLLM wheels | Excelente (CUDA/TensorRT) | Muy alta | TensorRT-Edge como camino oficial edge |
| AMD Strix Halo / 192 GB | Alta (2026) | Múltiples repos de benchmarks multi-slot | Buena vía iGPU Vulkan/ROCm | Alta y creciendo rápidamente | Multi-slot, speculative, ROCm optimizado |
| GB10 / DGX Spark | Media-Alta | UMA notes, agentic coding benchmarks | Excelente (CUDA + UMA) | Alta | Clustering y software NVIDIA stack |

**Brechas que persisten:**
- Casi nulos benchmarks controlados lado a lado Radxa vs Jetson con el mismo modelo/quant/runtime.
- NPU CIX aún no es path de producción para decode LLM completo.
- Documentación y drivers CIX/Radxa siguen fragmentados (especialmente mainline y Windows).

**Recomendación de seguimiento prioritario:**
1. `Reonarudo/tinygrad-npu-examples` — evolución del soporte NPU para LLM.
2. Issues de CIX sobre soporte de transformers dinámicos / KV-cache.
3. TensorRT-Edge-LLM releases y tablas de rendimiento.
4. Repos de Strix Halo como referencia de madurez de ecosistema abierto en memoria unificada de alto ancho de banda.

---

*Sección añadida el 24 de octubre de 2026 a partir de búsqueda exhaustiva en GitHub, Hugging Face, ModelScope, Gitee y GitCode. Todos los datos son PUBLISHED por terceros; no han sido reproducidos por LEONES.*

*(Nota: este commit restaura la sección 7 completa. Las secciones 0–6 del informe original se mantienen en el historial de commits anteriores de la rama. Se recomienda consultar el historial o el archivo local completo para el texto íntegro de metodología, AA y benchmarks previos.)*
