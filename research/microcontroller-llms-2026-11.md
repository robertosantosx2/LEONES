# Microcontroller-LLMs — LLMs en ESP32 y microcontroladores

**Fecha de incorporación:** 2026-11-21  
**Estado:** prospección documental; métricas y afirmaciones externas pendientes de reproducción independiente.  
**Categoría:** investigación de modelos, motores y técnicas.

## Objetivo

Investigar arquitecturas de modelos de lenguaje que ejecuten directamente en microcontroladores, especialmente ESP32/ESP32-S3, incluyendo memoria Flash como almacenamiento de pesos, PSRAM, modelos pequeños, MoE, cuantización extrema, distilación, optimización de kernels y clusters distribuidos.

No asumir que las métricas de terceros son benchmarks LEONES. Registrar hardware, firmware, tokenizer, contexto, cuantización, RAM/Flash, método de medición, tokens/s, latencia, energía y calidad de tarea.

## Hallazgos iniciales

| Proyecto / recurso | Arquitectura | Afirmación publicada / interés | Estado |
|---|---|---|---|
| [manjunathshiva/esp32-tinyllm](https://github.com/manjunathshiva/esp32-tinyllm) | 28,9 M parámetros; Per-Layer Embeddings (PLE), tabla de embeddings en Flash, núcleo denso | ~9,5–9,76 tok/s; ESP32-S3, 16 MB Flash / 8 MB PSRAM; TinyStories | Referencia primaria por inspeccionar y reproducir |
| [Bellman281/esp32-tinyLLM](https://github.com/Bellman281/esp32-tinyLLM) | Implementación Rust de la idea PLE | Reporta ~10,50 tok/s, optimización MSPI | Comparación Rust/C pendiente |
| [slvDev/esp32-ai](https://github.com/slvDev/esp32-ai) | Investigación de LLM en ESP32 y PLE | Antecedente relacionado | Revisar arquitectura y relación de derivación |
| [MoE de 5,2 M, Reddit](https://www.reddit.com/r/esp32/comments/1vjgbkk/i_ran_a_full_llm_model_on_an_esp32_dev_kit_v1/) | 16 expertos, INT4, lectura selectiva de pesos desde Flash; sin PSRAM según autor | ~5 tok/s y ~81 KB para motor, cifras del autor | Evidencia comunitaria, no validada |
| [Distributed AI 56 M](https://github.com/wladimiravila/esp32s3-distributed-ai) | Tres ESP32-S3, distribución de componentes y comunicación ESP-NOW | Arquitectura multi-nodo | Explorar particionado, tráfico y sincronización |
| [Cluster 7 ESP32-S3 / BitNet](https://www.reddit.com/r/esp32/comments/1vv7802/i_built_a_7node_esp32s3_cluster_to_run_a_04b_llm/) | Cluster SPI, modelo ~0,4 B y cuantización 1,58-bit declarada | Escalado por particionado de capas | Propuesta comunitaria; no validada |
| [ESP32-Tiny-LLM greenhouse assistant](https://github.com/marcelpetrick/ESP32-Tiny-LLM) | Decoder Transformer, KV cache, RoPE, GQA, INT8 y distilación | Modelo especializado reportado en ~804 KiB | Revisar código, dataset y evaluación |
| [Espressif esp-zerocode-blocks: on-device LLM](https://github.com/espressif/esp-zerocode-blocks/blob/main/docs/on-device-llm.md) | TinyStories y parser de comandos NL→JSON | Reporta 26,7 tok/s en ESP32-S31 y 17,6 tok/s en S3; parser ~270 KB y 88,8% exact match | Claims upstream; protocolo y hardware por verificar |
| [DaveBben/esp32-llm](https://github.com/DaveBben/esp32-llm) | llama2.c / ESP-DSP y uso dual-core | Optimización DSP y control de concurrencia | Inspeccionar y reproducir |
| [andrisgauracs/needle-2-esp32](https://github.com/andrisgauracs/needle-2-esp32) | Modelo ~45 M y tool calling restringido | Salida estructurada / gramática | Inspección de capacidades y licencia pendiente |

## Hipótesis y líneas de trabajo

1. **Flash-resident weights / PLE:** medir ancho de banda, patrón de acceso, latencia de lectura, cachés, coste de embeddings y output head.
2. **Flash-MoE:** cargar/consultar selectivamente expertos, comparar SRAM/PSRAM, latencia y consumo con modelos densos.
3. **Tiny Transformers:** modelos sub-MB para tareas estrechas; comparar distilación, calidad, tokenizer, contexto y recuperación.
4. **Cuantización extrema:** INT4, ternaria/BitNet y formatos de pesos compactos, con evaluación de degradación.
5. **Clusters:** estudiar distribución de capas, activaciones y KV, ESP-NOW frente a SPI y coste de comunicación.
6. **Kernels:** DSP, SIMD, multicore, Rust frente a C/C++, optimización del output head y tokenizer.
7. **Tool calling:** parsers, gramáticas restringidas, NL→JSON y controles de seguridad para acciones de firmware.
8. **Benchmark reproducible:** tokens/s, TTFT, latencia por token, energía, flash, RAM/PSRAM máxima, calidad de tarea, reproducibilidad y límites térmicos.

## Criterios de aceptación de futuras réplicas

- Identificar placa, SoC, revisión, frecuencia, Flash/PSRAM y firmware.
- Fijar repositorio, commit, licencia, modelo, tokenizer, dataset y hashes.
- Diferenciar métricas de autor, estimaciones y medidas físicas LEONES.
- Registrar RAM pico, memoria de pesos, KV cache, contexto, TTFT, throughput y energía cuando sea posible.
- Probar casos reproducibles de la tarea objetivo; la fluidez narrativa no demuestra capacidad general.
- Documentar restricciones de seguridad cuando el modelo pueda activar actuadores o herramientas.
- Aplicar HDAE: alcance, gates, artefactos, checkpoint y aceptación humana.

## Fuentes comunitarias para vigilancia

- [Reddit r/esp32: PLE, 28,9 M](https://www.reddit.com/r/esp32/comments/1v4mq5t/how_i_fit_a_289m_llm_on_an_esp32s3_9_toks_fully/)
- [Reddit r/esp32: MoE de 5,2 M](https://www.reddit.com/r/esp32/comments/1vjgbkk/i_ran_a_full_llm_model_on_an_esp32_dev_kit_v1/)
- [Reddit r/esp32projects: distribución 56 M](https://www.reddit.com/r/esp32projects/comments/1vaxdhi/a_project_that_runs_a_small_56mparameter_language/)
- [Reddit r/esp32: cluster BitNet de siete nodos](https://www.reddit.com/r/esp32/comments/1vv7802/i_built_a_7node_esp32s3_cluster_to_run_a_04b_llm/)
- [Búsqueda X: ESP32 LLM](https://x.com/search?q=ESP32%20LLM&src=typed_query)
- [Búsqueda X: ESP32-S3 TinyLLM](https://x.com/search?q=ESP32-S3%20TinyLLM&src=typed_query)
- [Búsqueda X: BitNet ESP32](https://x.com/search?q=BitNet%20ESP32&src=typed_query)
- [Búsqueda X: Per-Layer Embeddings ESP32](https://x.com/search?q=ESP32%20Per-Layer%20Embeddings&src=typed_query)

La indexación de X es irregular: estas son búsquedas de vigilancia, no publicaciones individuales verificadas.

## Próximos pasos

- [ ] Inspección recursiva y fijado de commits/licencias de cada repositorio.
- [ ] Matriz hardware-modelo-arquitectura y memoria.
- [ ] Protocolo común de benchmark y checklist de evidencia.
- [ ] Seleccionar dos experimentos: PLE single-node y MoE Flash.
- [ ] Evaluar cluster distribuido sólo tras obtener mediciones de tráfico y latencia.
- [ ] Automatizar prospección y actualización del catálogo mediante GitHub Actions/PR.

