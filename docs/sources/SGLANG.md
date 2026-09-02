# LEONES — SGLang

**Estado:** conocimiento incorporado · fuente primaria externa · no sustituye benchmarks LEONES.

**Fecha de revisión:** 2026-09-02

## Fuente primaria

- Proyecto: https://github.com/sgl-project/sglang
- Documentación: https://docs.sglang.io/
- Web: https://www.sglang.io/

## Qué es

SGLang es un framework de serving de alto rendimiento para modelos de lenguaje y multimodales. Está orientado a inferencia de baja latencia y alto throughput, desde una GPU hasta clústeres distribuidos.

## Capacidades relevantes

La documentación y el repositorio destacan, entre otras, RadixAttention para reutilización de prefijos/KV cache, continuous batching, paged attention, speculative decoding, prefill/decode disaggregation, structured outputs, chunked prefill, paralelismo tensor/pipeline/expert/data, cuantización FP4/FP8/INT4/AWQ/GPTQ y multi-LoRA batching.

SGLang declara soporte para modelos como Llama, Qwen, DeepSeek, Kimi, GLM, Gemma y Mistral, además de modelos multimodales y diffusion. También documenta soporte para NVIDIA, AMD, Intel Xeon, Google TPU y Ascend, con compatibilidad con modelos de Hugging Face y APIs OpenAI.

## Encaje en LEONES

**Clase:** `runtime-candidate`

SGLang debe incorporarse como candidato de runtime/serving, especialmente para workloads donde importan concurrencia, contexto largo, prefijo compartido, salidas estructuradas, MoE, routing o despliegue distribuido.

No sustituye al baseline físico de `llama.cpp`. La selección debe seguir siendo consecuencia de `hardware × modelo × cuantización × workload × objetivo de serving`.

## Evidencia y límites

La información anterior procede de las fuentes primarias de SGLang. Sus cifras de rendimiento, claims de adopción y resultados publicados son evidencia externa y **no** son mediciones LEONES.

Para convertir SGLang en evidencia LEONES hay que ejecutar una configuración concreta y registrar, como mínimo: modelo/revisión, cuantización, versión de SGLang, hardware, configuración de paralelismo, contexto, prompt protocol, warm-up, número de mediciones, TTFT, TPOT, throughput, concurrencia, memoria y `execution_id`.

## Benchmark LEONES propuesto

Comparar SGLang con los runtimes que resulten candidatos para el mismo `modelo × quant × hardware × workload`. No comparar sólo tokens/s de un único usuario: incluir TTFT, TPOT, p50/p95/p99, throughput agregado, memoria, concurrencia y comportamiento de KV/prefix caching cuando aplique.

## Semántica

- **Fuente / descubrimiento:** SGLang y su documentación oficial.
- **Evidencia:** capacidades y documentación publicadas por el proyecto.
- **Estimación:** hipótesis de que puede ser especialmente adecuado para serving concurrente, contexto largo, MoE y workloads estructurados.
- **Medición LEONES:** pendiente hasta ejecución reproducible mediante el pipeline canónico.
