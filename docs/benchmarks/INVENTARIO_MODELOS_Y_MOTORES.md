# Inventario maestro de modelos, motores y pruebas locales

**Última consolidación:** 2026-11-12 (incorporada prueba de compatibilidad LFM3-1.7B con TensorFold 1.1.6; PR #119 y campaña LFM3 #125)  
**Repositorio:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Equipo principal de referencia:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB · Ubuntu · driver 580.178.04 · CUDA 13.0.

Este documento es el índice único de modelos que se han investigado, descargado, ejecutado, medido o intentado ejecutar con distintos motores. Enlaza a los informes y artefactos originales; no los sustituye ni convierte pruebas distintas en un ranking.

> **Criterio:** “Ejecutado” significa inferencia local funcional; “medido” significa que existe una métrica capturada. Una descarga, compilación, prueba de catálogo o estimación de memoria no acredita inferencia. Las métricas no comparables se mantienen separadas y los datos ausentes se indican como N/D.

## 1. Resumen por motor

| Motor / proyecto | Estado en el laboratorio | Modelos o familias vinculados | Validación y notas |
|---|---|---|---|
| **llama.cpp CUDA** | Ejecutado y medido | Qwen3.5-4B, Qwen3-30B-A3B, LFM3-1.7B, Ling-3.0-Tiny, Spark-X2.6-4B, TwIL-8B | Incluye sweep `llama-bench` de Qwen3-30B-A3B IQ3_XXS con `ngl=0/1/8` (3 repeticiones por ajuste); `ngl=1` obtuvo la mejor mediana PP128. Binarios locales en ~/llama.cpp-cuda/build/bin y /usr/local/bin. |
| **TensorFold CUDA** | Ejecutado y medido; compatibilidad LFM3 no soportada/verificada en 1.1.6 | Qwen3.5-2B, Qwen3.5-4B; estudios de Qwen3.5-9B y Qwen3.5-35B-A3B; intento LFM3-1.7B | Inferencia real con 2B y 4B. PR #1879 aborda la reserva CUDA diferida de scratch para 4B. LFM3-1.7B GGUF Q4_K_M no fue reconocido: `info` rechaza el archivo (espera directorio de checkpoint o repo HF) y `capabilities --json` no declara familia `lfm3`. No se llegó a cargar ni ejecutar. Los estudios 9B/35B no acreditan ejecución en el MSI. |
| **RustingStrata CUDA** | Ejecutado y medido | Qwen3.5-4B, Qwen3-30B-A3B | Bench nativo y CLI/API documentados. Algunas APIs no exponen tok/s internos: no derivarlos como si fueran métricas nativas. |
| **Tandem / llama.cpp CPU-MoE** | Ejecutado y medido | Qwen3.5-35B-A3B IQ2_XXS | Ensayo CPU-MoE con RTX 3050; decode 35,6 tok/s en la prueba no-thinking registrada. Evidencia bruta pendiente de consolidación completa en LEONES. |
| **Pithos** | Ejecutado y medido | LFM3-1.7B | Campañas del 6 y 7 de noviembre; CSV y log preservados en artifacts/pithos-0.5.1-2026-11-07/. |
| **Kinetic** | Compilado / pruebas de ejecución en curso | LFM3-1.7B GGUF; Qwen3.5-35B-A3B IQ2_XXS seleccionado para prueba | Se inspeccionaron versiones, binarios y catálogo; se prepararon y ejecutaron pruebas. No publicar velocidad sin log de benchmark completo y reproducible. |
| **Colibri** | Instalado / auditado técnicamente | Compatibilidad Qwen3.6 CUDA | Auditoría del parser de colocación y configuración CUDA. Compilación o validación de código no equivale a inferencia medida. |
| **YASAKANI** | Prueba exploratoria solicitada | Modelo/backend/resultados por consolidar | Mantener como experimento hasta que exista log que demuestre carga e inferencia. |
| **ThumbLLM (TeksEdge)** | Receta Windows auditada; reproducción Linux documentada, aún no ejecutada | Qwen3.5-4B GGUF Q4_K_M | Runtime fijado a llama.cpp build 10603 / commit `c060ca974`; receta CPU-only. La release configura `SPEC_TYPE=none`: MTP especulativo desactivado. La aplicación publicada es Windows x64, no un binario Linux. Guía Ubuntu en [LEONES](../../experimental/ThumbLLM-thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0/docs/UBUNTU-REPRODUCTION.md). |\n| **Magnitude** | Integración investigada; prueba de catálogo fallida | Qwen3.5-4B | Pesos/proyector descargados y hashes verificados, pero el CLI no reconoció el ID. No hubo inferencia. |
| **Ollama** | Incluido en matriz de runtimes; no instalado en el MSI según inventario previo | Sin ejecución local validada | No contabilizar como motor probado en este equipo. |
| **Transformers, vLLM, SGLang, KTransformers, Mistral.rs** | Evaluación de soporte / planificación | Varias familias candidatas | Sin benchmark local normalizado acreditado en este inventario. |
| **ThumbLLM / llama.cpp CPU (Ornith 1.5)** | Paquete Release 1 incorporado a LEONES; reproducción Linux preparada, pendiente de ejecutar | Ornith-1.5-9B-OBLITERATED Q4_K_M | El release original está orientado a Windows. Se añadieron receta y scripts Ubuntu para compilar llama.cpp b10603 (c060ca974) en CPU y servir en puerto 18088. Descarga, hash, compilación e inferencia en el MSI aún no verificados; no contabilizar como motor/modelo ejecutado. |
| **Uzu** | Evaluación documental cerrada; `RESEARCH_ONLY / NOT VERIFIED` | Qwen3.5-4B, Qwen3.5 MoE (compatibilidad investigada, no validada) | Integrado en `Experimental` mediante PR #119. No se compila, instala ni ejecuta en el MSI dentro del alcance acordado. Sin soporte Ubuntu/CUDA, GGUF ni Qwen MoE demostrado; no contabilizar como motor probado. Ver [evaluación Uzu](../../experimental/uzu/README.md). |
| **MLX** | Formato/artefacto usado por TensorFold | Qwen3.5-2B/4B MLX-4bit | No implica ejecución nativa de MLX en Ubuntu; TensorFold cargó artefactos MLX mediante backend CUDA. |

## 2. Modelos con inferencia funcional y/o medición

| Modelo | Cuantización / artefacto | Motor / equipo | Resultado disponible | Estado y cautela |
|---|---|---|---|---|
| **Qwen3.5-2B** | MLX-4bit | TensorFold CUDA · RTX 3050 | Campaña API de octubre (5 peticiones, 66 entrada/128 salida): media 105,421 y mediana 106,455 tok/s; media TTFT 77,956 ms (mediana 84,646 ms); prefill medio 74,142 ms. Además, ensayos previos de 95,08 tok/s (32 tokens) y 105,71 tok/s (128). | Inferencia funcional. Las cinco respuestas llegaron al límite de 128 tokens; aceptación especulativa reportada 1/56 (1,7857%). No comparar directamente con `llama-bench`. |
| **Qwen3.5-4B** | MLX-4bit | TensorFold CUDA · RTX 3050 | 53,64 tok/s (64 tokens), 53,42 tok/s (128); API de tres peticiones: mediana 54,708 tok/s, TTFT 130,3 ms y prefill aprox. 228–232 tok/s | Inferencia funcional. Hubo un primer rechazo de memoria; después se completaron ejecuciones. |
| **Qwen3.5-4B** | GGUF Q4_K_M | llama.cpp CUDA · RTX 3050 | CLI: prefill 141,2 tok/s y decode 42,4 tok/s; API de tres peticiones: mediana decode 47,646 tok/s | Inferencia funcional. CLI y API son protocolos distintos. |
| **Qwen3.5-4B** | GGUF Q4_K_M | RustingStrata CUDA · RTX 3050 | Bench nativo: PP128 915,3 tok/s; PP512 986,5 tok/s; TG64 46,6 / 46,1 tok/s. API sin tok/s interno expuesto | Inferencia funcional y benchmark nativo. API no comparable en tok/s. |
| **Qwen3-30B-A3B-Instruct-2507** | GGUF IQ3_XXS | llama.cpp CUDA · RTX 3050 | Head-to-head de seis ejecuciones; mediana decode calculada 1,985 tok/s; PP128 mediana 24,42 / 76,25 / 26,38 tok/s con 0 / 1 / 8 capas GPU | Inferencia funcional con offload. Las longitudes y configuraciones varían entre ensayos. |
| **Qwen3-30B-A3B-Instruct-2507** | GGUF IQ3_XXS | llama.cpp `llama-bench` CUDA · RTX 3050 | Sweep `ngl=0/1/8`, PP128 (media/mediana): 22,553/24,420; 74,473/76,250; 34,957/26,380 tok/s. TG32: media 1,487; 1,660; 1,827 tok/s, respectivamente. Tres repeticiones por ajuste. | Nueve ejecuciones con código 0. `ngl=8` mostró alta variabilidad PP128; `ngl=1` tuvo la mejor mediana PP128. Benchmark separado del head-to-head y de Strata. |
| **Qwen3-30B-A3B-Instruct-2507** | GGUF IQ3_XXS | RustingStrata CUDA · RTX 3050 | Head-to-head de seis ejecuciones; mediana decode calculada 30,01 tok/s; RSS aprox. 7–8 GiB | Inferencia funcional. No es comparación perfectamente equivalente con llama.cpp. |
| **Qwen3-30B-A3B** | GGUF IQ3_XXS / configuración PICCHIO | MSI RTX 3050 | Campaña de memoria dual-channel y ejecución documentada en informe PICCHIO | Consultar informe específico; no mezclar con el head-to-head anterior. |
| **Qwen3.5-35B-A3B** | GGUF IQ2_XXS | Tandem / llama.cpp CPU-MoE · RTX 3050 + CPU/RAM | Decode aprox. **35,6 tok/s** en prueba no-thinking; prompt 46,5 tok/s; RSS aprox. 9,27 GiB; swap aprox. 7,5 GiB; GPU aprox. 2345 MiB | Ejecución real medida. Contexto 1024; no extrapolar a TensorFold. |
| **LFM3-1.7B Uncensored** | GGUF AD-Q4_K_M | llama.cpp CUDA · RTX 3050 | llama-bench: PP512 4.326,68 tok/s; TG128 117,29 tok/s. CLI interactivo: decode aprox. 99,8–104,4 tok/s | Inferencia funcional y medición nativa. |
| **LFM3-1.7B** | GGUF de campaña Pithos | Pithos · RTX 3050 | CSV de resultados y log de sesión conservados | Consultar informes Pithos; no asumir artefacto/protocolo idéntico al de llama.cpp. |\n| **LFM3-1.7B** | GGUF Q4_K_M | TensorFold 1.1.6 CUDA · RTX 3050 sm_86 | `tensorfold-native capabilities --json`: no declara familia `lfm3`; `tensorfold-native info <archivo.gguf>` responde que el archivo no es un directorio ni un repo HF. | **Intento de compatibilidad, no ejecución.** No se cargó el modelo ni se midió rendimiento. El rechazo evidencia que el GGUF no es una entrada aceptada por esta interfaz y que la familia no figura en las capacidades de 1.1.6; no demuestra imposibilidad futura ni descarta una implementación/checkpoint distinto. No instalar, convertir ni descargar pesos alternativos como parte de esta prueba. |
| **Ling-3.0-Tiny** | GGUF IQ2_M | llama.cpp CUDA · RTX 3050 | Ejecución funcional: prompt 62,5 tok/s y generación 5,4 tok/s; primera ejecución truncada: 68,7 / 8,3 tok/s | Prueba de código factorial validada; primera salida truncada no es ejecución completa. |
| **Ling-3.0-Tiny** | GGUF Q4_K_M | llama.cpp CPU · GB-BXi7-5500 | PP 41,0 tok/s; generación 15,5 tok/s | Equipo distinto del MSI; mantener separado. |
| **Spark-X2.6-4B-abliterated** | GGUF Q4_K_M | llama.cpp CUDA · RTX 3050 | Prueba funcional: prefill 36,9 tok/s; generación 7,2 tok/s | Ejecución individual; faltan repeticiones y perfil de memoria normalizado. |
| **TwIL-8B** | GGUF Q4_K_M balanced | llama.cpp CUDA · RTX 3050 | Campaña de 24 y 26 capas GPU; protocolo y tres repeticiones en informe | Inferencia funcional medida. Arquitectura Granite no soportada por la capacidad observada de TensorFold 1.2.0. |
| **Qwen3.5-4B** | MLX-4bit | TensorFold PR #1879 · CUDA sm_86 | Build CUDA y suites host validadas; ejecución GPU real; decode aprox. 56,5 tok/s en esa ejecución | Validación del parche, no benchmark A/B formal ni prueba de todas las rutas. |

## 3. Intentos, estudios e investigación (no contar como benchmark)

| Modelo / proyecto | Motor / entorno | Trabajo realizado | Estado correcto |
|---|---|---|---|
| **Qwen3.5-35B-A3B** | TensorFold | Estimación de memoria y análisis de compatibilidad; pesos estimados en torno a 20,4 GB en el formato estudiado | Sin inferencia TensorFold validada en el MSI. |
| **Qwen3.5-35B-A3B IQ2_XXS** | Kinetic | Modelo identificado/seleccionado para campaña | Vincular log definitivo antes de declarar velocidad medida. |
| **Qwen3.5-4B** | Magnitude 0.2.10 | Descarga/verificación de pesos y proyector; ID no reconocido por CLI | Sin inferencia. |
| **Qwen3.5-9B** | Estudio TensorFold / RTX 3050 | Informe de memoria, cuantización y viabilidad; comparación E-means frente a K-means | Estudio técnico, no ejecución local validada del 9B. |
| **Qwen3.5-122B-A10B** | Estudio RTX 5090 | Evaluación teórica de memoria y cuantización | No ejecutado en hardware local. |
| **Clover-35B-A3B-Preview** | Investigación documental / viabilidad MSI | MoE de difusión, 35B parámetros totales y aprox. 3B activos por token; generación por bloques con atención bidireccional dentro del bloque; contexto anunciado de hasta 128K. Pesos BF16 publicados: aprox. 69,3 GB. | **No viable en el MSI actual y no probado.** RTX 3050 Laptop 4 GiB VRAM y 14 GiB RAM física: no permiten cargar el modelo completo; el carácter MoE reduce cómputo por token, no el almacenamiento de todos los expertos. INT4/Q4 (~19–23 GB) y 2-bit (~11–14 GB) son únicamente estimaciones de tamaño, no cuantizaciones oficiales verificadas ni pruebas de ejecución; incluso la estimación 2-bit deja poco o ningún margen para runtime, contexto y Ubuntu. El swap de 32 GB no sustituye RAM y previsiblemente produciría paginación severa. No descargar pesos originales (69,3 GB), convertir ni intentar inferencia local en esta configuración. Mantener en `Experimental / research-only`, pendiente de cuantizaciones compactas verificables y soporte real de motores. Referencias: [repositorio oficial](https://github.com/DiffuSpace/Clover-35B-A3B-Preview), [Hugging Face](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview), [anuncio técnico](https://diffuspace.ai/blog/clover-35b/). |
| **Qwen3.5-4B AWQ W4A16** | Inspección de modelo | Ficha/candidato evaluado | No ejecutado. |\n| **Qwen3.5-4B MTP-GGUF Q4_K_M (receta ThumbLLM)** | TeksEdge ThumbLLM / llama.cpp CPU | Modelo `unsloth/Qwen3.5-4B-MTP-GGUF`; SHA-256 de la receta: `3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630`. Runtime upstream `c060ca974` (build 10603). Contexto de receta 65.536, KV `q4_0`, batch/ubatch 2048/512, Flash Attention, mmap/repack. | Configuración de referencia analizada, no ejecutada aún en Ubuntu. Aunque el repositorio del modelo contiene MTP en el nombre, la receta usa `SPEC_TYPE=none`; no hay speculative decoding activo. El ejecutable de la release es Windows x64. La cifra upstream de ~18 tok/s es una observación durante generación, no un benchmark controlado y no comparable directamente. |
| **YASAKANI** | Prueba exploratoria | Investigación y preparación solicitadas | Sin resultado reproducible consolidado. |
| **Colibri / Qwen3.6 CUDA** | Auditoría de código | Parser de colocación, límites de componentes/segmentos y buffers | No atribuir rendimiento de inferencia a esta auditoría. |
| **Ornith-1.5-9B-OBLITERATED** | ThumbLLM Release 1 / llama.cpp CPU · Ubuntu MSI | Paquete upstream incorporado a rama experimental de LEONES; documentación de reproducción y scripts de setup/serve preparados. GGUF Q4_K_M, SHA-256 de referencia 88ce99bb696fbc921edc4f995c4beb12a66bf94319d00bfd5f44265d02fa6dfb; llama.cpp b10603, commit c060ca974; configuración de referencia: contexto 65.536, batch 2.048, ubatch 512, KV Q4_0, 8 hilos decode y 16 batch. | **Preparación, no ejecución local acreditada.** No hay todavía log de descarga, compilación, carga del GGUF ni generación en el MSI; no registrar tok/s. La receta de upstream cita aproximadamente 13,03 tok/s de generación y 1.302 tok/s de prompt en Ryzen 7 7840HS/Windows 11, cifras de referencia externa no reproducidas ni comparables con el MSI. |
| **Uzu inference runtime** | Uzu + Lalamo | Evaluación de fuentes públicas, plataforma Linux/Ubuntu, backend CUDA, formatos y compatibilidad potencial con Qwen3.5-4B y Qwen MoE. Registro definitivo en `Experimental`, PR #119 fusionado. | `RESEARCH_ONLY / NOT VERIFIED`; no se ejecutará en el laboratorio. No hay compilación, inferencia ni benchmark local acreditados. [Documento experimental](../../experimental/uzu/README.md). |
| **Mistral.rs, vLLM, SGLang, KTransformers** | Evaluación de runtimes | Instalación/soporte/requisitos estudiados | Sin benchmark local normalizado en este inventario. |

## 4. Informes y artefactos primarios

### Material formativo sobre LLM (no es benchmark)
- [Curso interactivo de fundamentos de LLM — versión española](../../cursollm-es.html)

El curso es un recurso didáctico interactivo sobre Transformers y modelos de lenguaje; no representa una ejecución ni una comparación de modelos o motores del laboratorio. En la validación local de la traducción se detectaron regresiones JavaScript en revisiones anteriores (`querySelectorTodo`, claves de datos traducidas y eventos/etiquetas de entrada). Un candidato local con las correcciones recuperó la estructura esperada (293 botones, 84 elementos de flujo y 34 secciones) y no produjo excepciones JavaScript durante la carga. Esta comprobación no equivale a una batería funcional completa ni certifica la copia exacta publicada en GitHub: quedan pendientes las interacciones exhaustivas de pasos, animaciones, cuestionarios, glosario, tokenizer y tema. La copia remota sí contiene las correcciones estáticas revisadas (`querySelectorAll`, `heads` y eventos `input`).


### Inventarios y comparativas generales
- [Inventario comparativo histórico (30-10-2026)](inventario-comparativo-ejecuciones-modelos-ubuntu-2026-10-30.md)
- [Informe reproducible de inferencia RTX 3050 — español](../reports/report-inferencia-dense_Octubre26.md)
- [Reproducible RTX 3050 inference report — English](../reports/report-inference-dense-october-2026.md)
- [Paquete de evidencias del benchmark de octubre (tar.gz)](../reports/artifacts/inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz)
- [Script recolector de evidencias](../../scripts/benchmarks/collect-inferencia-rtx3050-oct26.sh)
- [Qwen3.5-4B: tres runtimes](qwen35-4b-three-runtimes-2026-10-20.md)
- [CSV Qwen3.5-4B / tres runtimes](qwen35-4b-three-runtimes-2026-10-20.csv)
- [Inventario experimental Qwen3.5 TensorFold / llama.cpp](../experimental/inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md)

### Informes de modelos
- [TwIL-8B Q4_K_M — RTX 3050](../TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md)
- [Qwen3.5-9B / RTX 3050 — español](../QWEN3.5-9B-RTX3050-2026-11-11.md)
- [Qwen3.5-9B / RTX 3050 — English](../QWEN3.5-9B-RTX3050-2026-11-11-EN.md)
- [Spark-X2.6-4B abliterated — RTX 3050](spark-x26-4b-abliterated-rtx3050-2026-10-30.md)
- [Magnitude + Qwen3.5-4B — prueba de catálogo](magnitude-qwen35-4b-2026-10-21.md)\n- [ThumbLLM Qwen3.5-4B — guía de auditoría y reproducción Ubuntu](../../experimental/ThumbLLM-thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0/docs/UBUNTU-REPRODUCTION.md)\n- [ThumbLLM upstream — release Qwen3.5-4B CPU Windows](https://github.com/TeksEdge/ThumbLLM/releases/tag/thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0)
- [Ling-3.0-Tiny — MSI RTX 3050](../reports/ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md)
- [Ling-3.0-Tiny — GB-BXi7-5500](../reports/ling-3.0-tiny-ubuntu-gb-bxi7-5500-2026-10-29.md)
- [Pithos LFM3-1.7B — campaña 06-11](../PITHOS-LFM3-1.7B-RTX3050-2026-11-06.md)
- [Pithos LFM3-1.7B — campaña 07-11](../PITHOS-LFM3-1.7B-RTX3050-2026-11-07.md)\n- [LFM3-1.7B — benchmark llama.cpp CUDA RTX 3050 (PR #125)](../reports/lfm3-1.7b-rtx3050-cuda-20261028.md)\n- [PR #125 — evidencias LFM3-1.7B CUDA](https://github.com/robertosantosx2/LEONES/pull/125)

### Artefactos y proyectos de motor
- [Uzu — evaluación documental del motor experimental (PR #119)](../../experimental/uzu/README.md)
- [Qwen3-30B-A3B head-to-head — README](artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/README.md)
- [Qwen3-30B-A3B — CSV de resultados](artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/results-summary.csv)
- [Qwen3-30B-A3B — manifiesto de logs brutos](artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/raw-archive-manifest.md)
- [PICCHIO — Qwen3-30B-A3B en MSI](../subprojects/REDIL-IA-distribuida/PICCHIO-QWEN3-30B-A3B-MSI-2026-11-07.md)
- [PICCHIO — perfil RAM dual-channel](../reports/picchio-ram-dual-channel-msi-2026-11-08.md)
- [PICCHIO — referencia de implementación MoE](../PICCHIO-MOE-IMPLEMENTATION-REFERENCE-2026-11-08.md)
- [TensorFold — README del subproyecto](../subprojects/TensorFold/README.md)
- [TensorFold — regresión de memoria CUDA](../subprojects/TensorFold/CUDA-MEMORY-REGRESSION-2026-11-01.md)
- [TensorFold — corrección CUDA lazy scratch / PR #1879](../subprojects/TensorFold/CUDA-LAZY-SCRATCH-FIX-PR1879-2026-11-02.md)
- [Pithos — CSV de benchmark](../../artifacts/pithos-0.5.1-2026-11-07/benchmark-results.csv)
- [Pithos — log de sesión](../../artifacts/pithos-0.5.1-2026-11-07/benchmark-session.log)

### ThumbLLM — Ornith 1.5 9B CPU (reproducción Ubuntu)

- [Paquete ThumbLLM Release 1 incorporado a LEONES](https://github.com/robertosantosx2/LEONES/tree/experimental/thumbllm-release-1-ornith-1.5-9b-cpu/ThumbLLM-Release-1-Ornith-1.5-9B-CPU)
- [Guía de reproducción en Ubuntu](https://github.com/robertosantosx2/LEONES/blob/experimental/thumbllm-release-1-ornith-1.5-9b-cpu/ThumbLLM-Release-1-Ornith-1.5-9B-CPU/docs/ubuntu-reproduction.md)
- [Script de instalación, descarga, verificación y compilación CPU](https://github.com/robertosantosx2/LEONES/blob/experimental/thumbllm-release-1-ornith-1.5-9b-cpu/ThumbLLM-Release-1-Ornith-1.5-9B-CPU/scripts/ubuntu-ornith-cpu-setup.sh)
- [Script de servicio local (puerto 18088)](https://github.com/robertosantosx2/LEONES/blob/experimental/thumbllm-release-1-ornith-1.5-9b-cpu/ThumbLLM-Release-1-Ornith-1.5-9B-CPU/scripts/ubuntu-ornith-cpu-serve.sh)
- [Release upstream ThumbLLM](https://github.com/TeksEdge/ThumbLLM/releases/tag/Release-1-Ornith-1.5-9B-CPU)

La reproducción se mantiene aislada del servicio ODS en el puerto 8080: el servidor previsto escucha en 127.0.0.1:18088. La guía fija como referencia el tag de ThumbLLM y el commit histórico de llama.cpp declarados por el release. Hasta ejecutar el setup y conservar el log completo, este trabajo es preparación reproducible, no benchmark.

### Infraestructura de registro
- [Matriz de runtimes del smoke test](../../scripts/local/llm-smoke-test/RUNTIME_MATRIX.md)
- [README del smoke test local](../../scripts/local/llm-smoke-test/README.md)
- [Contrato de evidencia runtime v1.1](../runtime-benchmark-evidence-v1.1.md)
- [Manifiesto de benchmark del LEONES Lab Agent](../../projects/leones-lab-agent/docs/benchmark-manifest-v1.md)

### Campaña reproducible de inferencia densa — 22-10-2026

El informe fusionado en [PR #112](https://github.com/robertosantosx2/LEONES/pull/112) añade una campaña independiente con dos ensayos que deben mantenerse separados:

- **llama.cpp + Qwen3-30B-A3B IQ3_XXS:** `llama-bench`, PP128/TG32, `ngl=0/1/8`, tres repeticiones por ajuste. La mediana PP128 más alta fue 76,250 tok/s con `ngl=1`; `ngl=8` fue inestable (PP128 entre 9,41 y 69,08 tok/s). Decode TG32 quedó entre 1,40 y 2,14 tok/s.
- **TensorFold 1.1.1 + Qwen3.5-2B MLX-4bit:** cinco peticiones API secuenciales, 66 tokens de entrada y 128 de salida reportados; velocidad media 105,421 tok/s, mediana 106,455 tok/s y TTFT medio 77,956 ms. Todas alcanzaron el límite de salida, por lo que deben tratarse como respuestas potencialmente truncadas.

El informe también documenta diagnósticos de carga CUDA de Qwen3-30B-A3B (buffer de modelo CUDA 3290,68 MiB, KV 26 MiB, compute 86,25 MiB), comandos de referencia, advertencias `CUDA_Host` no fatales y estado de los artefactos. La captura `nvidia-smi` posterior a la ejecución no equivale a telemetría de pico. No mezclar estos datos con el head-to-head anterior ni usarlos para ordenar motores con modelos/protocolos distintos.

## 5. Reglas para mantenerlo actualizado

1. No confundir modelo investigado con modelo ejecutado. Descarga, ficha consultada, compilación o análisis de memoria no acreditan inferencia.
2. Separar prefill, decode, TTFT, latencia de petición, llama-bench, CLI y API.
3. Registrar modelo, repositorio, archivo, cuantización, hash, motor, versión/commit, backend, contexto y parámetros.
4. Conservar resultados brutos: CSV/JSONL/log y comando exacto.
5. Anotar el equipo real. Las mediciones del GB-BXi7-5500 y del MSI no se mezclan.
6. No rellenar N/D con estimaciones. Las estimaciones pertenecen a informes de viabilidad.
7. Actualizar la tabla al cerrar cada campaña; una prueba solo pasa a “medida” con evidencia reproducible.
8. Usar el manifiesto de evidencia LEONES para nuevos benchmarks y mantener esta página como índice humano.

## 6. Pendientes de consolidación

- Archivar en LEONES los logs, JSONL, manifiesto y configuración íntegra de Tandem Qwen3.5-35B-A3B IQ2_XXS si no están ya completos.
- Clonar y auditar el código fuente de ThumbLLM en Ubuntu, compilar el runtime CPU fijado, verificar el GGUF y portar/validar el frontend Linux; registrar una campaña reproducible antes de marcarlo como ejecutado.\n- Consolidar los resultados finales de Kinetic por modelo, cuantización, backend y versión.
- Completar YASAKANI solo cuando exista una ejecución verificable.
- Ejecutar y archivar la reproducción Ubuntu de ThumbLLM/Ornith 1.5 9B: log de descarga y SHA-256, commit/flags de compilación, versión resultante de llama.cpp, configuración efectiva, log de carga/inferencia y métricas PP/TG; solo entonces promoverla a ejecución medida.
- Mantener Colibri como auditoría/compilación hasta disponer de inferencia reproducible.
- Incorporar futuras pruebas como campañas fechadas, sin sobrescribir resultados históricos.

---
**Nota de precisión:** este inventario combina informes versionados de LEONES con resultados de laboratorio comunicados durante las sesiones. Los registros que todavía no tienen artefacto bruto versionado quedan identificados como pendientes de archivo; no se presentan como evidencia independiente auditada.
