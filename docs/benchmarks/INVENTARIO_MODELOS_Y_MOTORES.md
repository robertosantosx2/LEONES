# Inventario maestro de modelos, motores y pruebas locales

**Última consolidación:** 2026-11-12 (incorporada evaluación documental de Mage-VL-Cowork y situación en Artificial Analysis)  
**Repositorio:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Equipo principal de referencia:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB · Ubuntu · driver 580.178.04 · CUDA 13.0.

Este documento es el índice único de modelos que se han investigado, descargado, ejecutado, medido o intentado ejecutar con distintos motores. Enlaza a los informes y artefactos originales; no los sustituye ni convierte pruebas distintas en un ranking.

> **Criterio:** “Ejecutado” significa inferencia local funcional; “medido” significa que existe una métrica capturada. Una descarga, compilación, prueba de catálogo o estimación de memoria no acredita inferencia. Las métricas no comparables se mantienen separadas y los datos ausentes se indican como N/D.

## 1. Resumen por motor

| Motor / proyecto | Estado en el laboratorio | Modelos o familias vinculados | Validación y notas |
|---|---|---|---|
| **llama.cpp CUDA** | Ejecutado y medido | Qwen3.5-4B, Qwen3-30B-A3B, **Clover-35B-A3B-Preview IQ2_S**, LFM3-1.7B, Ling-3.0-Tiny, Spark-X2.6-4B, TwIL-8B | LFM3 incorporado en v0.8.0 (PR #31252/#31257); el build histórico b11740 es anterior. Incluye sweep `llama-bench` de Qwen3-30B-A3B IQ3_XXS con `ngl=0/1/8` (3 repeticiones por ajuste); `ngl=1` obtuvo la mejor mediana PP128. Binarios locales en ~/llama.cpp-cuda/build/bin y /usr/local/bin. |
| **TensorFold CUDA** | Ejecutado y medido; integración TensorFold Web 1.2.0 en validación | Qwen3.5-2B, Qwen3.5-4B; estudios de Qwen3.5-9B y Qwen3.5-35B-A3B; intento LFM3-1.7B | Inferencia real con 2B y 4B. PR #1879 aborda la reserva CUDA diferida de scratch para 4B. LFM3-1.7B GGUF Q4_K_M no fue reconocido en 1.1.6. El 12-11-2026 se verificó TensorFold Native 1.2.0 con backend CUDA en `nvidia-sm86`, catálogo que incluye `mlx-community/Qwen3.5-4B-MLX-4bit` y opción `--dashboard`; la UI TensorFold Web/bridge funciona en 127.0.0.1:8787, pero el motor no estaba iniciado en 127.0.0.1:8080. Por tanto, esta integración web todavía no acredita una nueva inferencia ni benchmark. Los estudios 9B/35B no acreditan ejecución en el MSI. |
| **RustingStrata CUDA** | Ejecutado y medido | Qwen3.5-4B, Qwen3-30B-A3B | Bench nativo y CLI/API documentados. Algunas APIs no exponen tok/s internos: no derivarlos como si fueran métricas nativas. |
| **Tandem / llama.cpp CPU-MoE** | Ejecutado y medido | Qwen3.5-35B-A3B IQ2_XXS | Ensayo CPU-MoE con RTX 3050; decode 35,6 tok/s en la prueba no-thinking registrada. Evidencia bruta pendiente de consolidación completa en LEONES. |
| **Pithos** | Ejecutado y medido | LFM3-1.7B | Campañas del 6 y 7 de noviembre; CSV y log preservados en artifacts/pithos-0.5.1-2026-11-07/. |
| **Kinetic** | Compilado / pruebas de ejecución en curso | LFM3-1.7B GGUF; Qwen3.5-35B-A3B IQ2_XXS seleccionado para prueba | Se inspeccionaron versiones, binarios y catálogo; se prepararon y ejecutaron pruebas. No publicar velocidad sin log de benchmark completo y reproducible. |
| **Colibri** | Instalado / auditado técnicamente | Compatibilidad Qwen3.6 CUDA | Auditoría del parser de colocación y configuración CUDA. Compilación o validación de código no equivale a inferencia medida. |
| **YASAKANI** | Prueba exploratoria solicitada | Modelo/backend/resultados por consolidar | Mantener como experimento hasta que exista log que demuestre carga e inferencia. |
| **ThumbLLM (TeksEdge)** | Receta Windows auditada; reproducción Linux documentada, aún no ejecutada | Qwen3.5-4B GGUF Q4_K_M | Runtime fijado a llama.cpp build 10603 / commit `c060ca974`; receta CPU-only. La release configura `SPEC_TYPE=none`: MTP especulativo desactivado. La aplicación publicada es Windows x64, no un binario Linux. Guía Ubuntu en [LEONES](../../experimental/ThumbLLM-thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0/docs/UBUNTU-REPRODUCTION.md). |\n| **diffuse-cpp** | Investigado documentalmente; no instalado ni ejecutado | LLaDA-8B-Instruct, Dream-v0-Instruct-7B | Motor C++ basado en GGML para dLLM; publica cuantización Q4_K_M y optimizaciones de caché/planificación. Sus cifras upstream proceden de AMD EPYC 4465P de 12 núcleos, no del CPU Intel de referencia. Sin validación local. [Repositorio](https://github.com/iafiscal1212/diffuse-cpp). |\n| **Magnitude 0.2.15** | Instalado y servicio operativo; catálogo consultado | MiniCPM5 1B (Q4); antecedente Qwen3.5-4B en 0.2.10 | `magnitude status`: Runtime Ready, Owner Server, versión 0.2.15, `0.0.0.0:10100`; HTTP local 200. Catálogo: un modelo compatible (MiniCPM5 1B Q4). No hay modelo activo ni inferencia medida. La escucha en todas las interfaces exige clave API. La prueba histórica 0.2.10 con Qwen3.5-4B sigue documentada como ID no reconocido; no confundir ambas campañas. |
| **Ollama** | Incluido en matriz de runtimes; no instalado en el MSI según inventario previo | Sin ejecución local validada | No contabilizar como motor probado en este equipo. |
| **Transformers, vLLM, SGLang, KTransformers, Mistral.rs** | Evaluación de soporte / planificación | Varias familias candidatas | Sin benchmark local normalizado acreditado en este inventario. |
| **ThumbLLM / llama.cpp CPU (Ornith 1.5)** | Paquete Release 1 incorporado a LEONES; reproducción Linux preparada, pendiente de ejecutar | Ornith-1.5-9B-OBLITERATED Q4_K_M | El release original está orientado a Windows. Se añadieron receta y scripts Ubuntu para compilar llama.cpp b10603 (c060ca974) en CPU y servir en puerto 18088. Descarga, hash, compilación e inferencia en el MSI aún no verificados; no contabilizar como motor/modelo ejecutado. |
| **Project Maya** | Integrado documentalmente / adaptador deshabilitado; fuente upstream vendorizada en PR #142 | GLM-5.3, GLM-5.3-Flash, DeepSeek-V4.1-Flash, MiniMax-M3.1-Flash | Familia independiente y motores/model packs específicos; API OpenAI y Anthropic documentadas. La evaluación histórica v1.1.31 se conserva como referencia, pero la rama de integración posterior fija upstream en v1.1.58 (`a3582528bfb73175fed1757b485bfcaaf01aaeaa`). No ejecutar en MSI: 14 GiB RAM frente al mínimo documentado de 32 GiB; 4 GiB VRAM. Sin inferencia local ni rendimiento medido. Ver PR #142. |\n| **Uzu** | Evaluación documental cerrada; `RESEARCH_ONLY / NOT VERIFIED` | Qwen3.5-4B, Qwen3.5 MoE (compatibilidad investigada, no validada) | Integrado en `Experimental` mediante PR #119. No se compila, instala ni ejecuta en el MSI dentro del alcance acordado. Sin soporte Ubuntu/CUDA, GGUF ni Qwen MoE demostrado; no contabilizar como motor probado. Ver [evaluación Uzu](../../experimental/uzu/README.md). |
| **Mesh-LLM / REDIL** | Referencia arquitectónica documental; no ejecutado | Mesh-LLM como referencia principal de REDIL; Distributed Llama como backend opcional experimental | No es un motor validado en el MSI ni un benchmark. REDIL sigue en estado de propuesta/investigación, sin despliegue físico. La actualización documental está en PR #131. |
| **Mage-VL-Cowork (Microsoft Mage)** | Investigación documental; no instalado ni ejecutado en el MSI | Agente CUA multimodal 4B; GUI + código/terminal | 66,0% OSWorld-Verified (361 tareas, 50 pasos; media de dos ejecuciones publicada por el equipo); no es un resultado de Artificial Analysis ni un benchmark LEONES. Sin inferencia local ni compatibilidad Ubuntu/GGUF verificada. |
| **MLX** | Formato/artefacto usado por TensorFold | Qwen3.5-2B/4B MLX-4bit | No implica ejecución nativa de MLX en Ubuntu; TensorFold cargó artefactos MLX mediante backend CUDA. |

## 1.1 Liquid AI en llama.cpp — incorporación de LFM3 y modelos d1

La compatibilidad de la familia **LiquidAI LFM3** quedó reunida en la versión **llama.cpp v0.8.0** (28-10-2026). La incorporación al código principal fue progresiva; por tanto, los commits de desarrollo/pre-release no deben confundirse con la primera versión etiquetada que agrupa todo el soporte.

| Modelo / familia | Capacidades | PR upstream | Primera versión etiquetada |
|---|---|---|---|
| **LFM3-1.7B** | Texto | [#31252](https://github.com/ggml-org/llama.cpp/pull/31252) | **v0.8.0** |
| **LFM3-VL-2B** | Visión e imagen | [#31252](https://github.com/ggml-org/llama.cpp/pull/31252) | **v0.8.0** |
| **LFM3-Audio-2B** | ASR y TTS | [#31257](https://github.com/ggml-org/llama.cpp/pull/31257) | **v0.8.0** |
| **LFM3-Omni-2B** | Audio conversacional/multimodal | [#31257](https://github.com/ggml-org/llama.cpp/pull/31257) | **v0.8.0** |
| **d1-2B / d1-Omni-2B** | Modelos de decisión LiquidAI | [#31275](https://github.com/ggml-org/llama.cpp/pull/31275) | **v0.8.0** |

Referencias: [notas oficiales de llama.cpp v0.8.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0), [PR #31252 (texto/visión)](https://github.com/ggml-org/llama.cpp/pull/31252), [PR #31257 (audio/omni)](https://github.com/ggml-org/llama.cpp/pull/31257) y [PR #31275 (d1)](https://github.com/ggml-org/llama.cpp/pull/31275). El pre-release **b11938** ya incluía LFM3-1.7B y LFM3-VL-2B, pero no equivale a la versión etiquetada v0.8.0 que reúne la familia.

**Implicación para LEONES:** el build histórico local **llama.cpp 0.7.0-dev / b11740** es anterior a esta incorporación. Para probar LFM3 debe usarse un tag/commit posterior que incluya el soporte correspondiente y registrarse el backend, GGUF y componentes auxiliares requeridos por cada modalidad (por ejemplo, mmproj/audio). La disponibilidad upstream no demuestra que todos los modelos/modos se hayan ejecutado en el MSI; los resultados locales acreditados siguen siendo los recogidos en las tablas de pruebas.

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
| **Clover-35B-A3B-Preview** | GGUF IQ2_S (`Clover-35B-A3B-Preview-IQ2_S-exps-down3-hq.gguf`, 13.795.534.208 bytes) | llama.cpp CUDA · RTX 3050 4 GiB | `llama-speculative-simple` con `draft-self`: carga 21,94 s; prompt 2,36 tok/s (107 tokens); eval 2,80 tok/s; 17 tokens previstos, 7/7 aceptados; RSS 9.693.388 KB; salida coherente en inglés. Ejecuciones custom-Jinja: 95 tokens a 5,15 tok/s (prompt 2,79; carga 20,82 s) y 255 tokens a 4,90 tok/s (prompt 3,60; carga 20,39 s; RSS 10,08 GiB; exit 0). Ejecución convencional adicional: 127 tokens a 2,68 tok/s, prompt 2,21 tok/s, carga 20,67 s, con salida repetitiva. | **Inferencia local ejecutada y medida** con el artefacto IQ2_S concreto. Rendimiento bajo y calidad variable según plantilla/protocolo; no equivale a validar el modelo original BF16/INT4 ni su carga íntegra en VRAM. Mantener Experimental. |
| **LFM3-1.7B Uncensored** | GGUF AD-Q4_K_M | llama.cpp CUDA · RTX 3050 | llama-bench: PP512 4.326,68 tok/s; TG128 117,29 tok/s. CLI interactivo: decode aprox. 99,8–104,4 tok/s | Inferencia funcional y medición nativa. |
| **LFM3-1.7B** | GGUF de campaña Pithos | Pithos · RTX 3050 | CSV de resultados y log de sesión conservados | Consultar informes Pithos; no asumir artefacto/protocolo idéntico al de llama.cpp. |\n| **LFM3-1.7B** | GGUF Q4_K_M | TensorFold 1.1.6 CUDA · RTX 3050 sm_86 | `tensorfold-native capabilities --json`: no declara familia `lfm3`; `tensorfold-native info <archivo.gguf>` responde que el archivo no es un directorio ni un repo HF. | **Intento de compatibilidad, no ejecución.** No se cargó el modelo ni se midió rendimiento. El rechazo evidencia que el GGUF no es una entrada aceptada por esta interfaz y que la familia no figura en las capacidades de 1.1.6; no demuestra imposibilidad futura ni descarta una implementación/checkpoint distinto. No instalar, convertir ni descargar pesos alternativos como parte de esta prueba. |
| **Ling-3.0-Tiny** | GGUF IQ2_M | llama.cpp CUDA · RTX 3050 | Ejecución funcional: prompt 62,5 tok/s y generación 5,4 tok/s; primera ejecución truncada: 68,7 / 8,3 tok/s | Prueba de código factorial validada; primera salida truncada no es ejecución completa. |

### Ling-3.0-Tiny (Ling 3.0 Tiny 8B A1B): arquitectura, formatos y compatibilidad

La ficha oficial de [inclusionAI/Ling-3.0-tiny](https://huggingface.co/inclusionAI/Ling-3.0-tiny) identifica **7.893,4 millones de parámetros** y la arquitectura **`bailing_hybrid`**. El nombre A1B indica su clase de activación/cómputo reducido; no debe confundirse con el número de parámetros que hay que almacenar: el modelo completo ronda los 7,9B. La ficha declara licencia MIT. Existe además una distribución GGUF oficial: [inclusionAI/Ling-3.0-tiny-GGUF](https://huggingface.co/inclusionAI/Ling-3.0-tiny-GGUF).

**Estado en el MSI:** no es una mera estimación de viabilidad. La tabla de resultados anterior conserva una ejecución funcional real con **GGUF IQ2_M + llama.cpp CUDA en la RTX 3050 de 4 GiB** (62,5 tok/s de prompt y 5,4 tok/s de generación). La primera ejecución truncada (68,7 / 8,3 tok/s) se conserva como antecedente y no debe usarse como resultado representativo. Consultar el [informe de prueba Ling-3.0-Tiny en el MSI](../reports/ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md) para comandos, configuración y contexto.

**Lectura de viabilidad y límites:**
- La activación dispersa puede reducir el cómputo por token, pero no reduce el almacenamiento de pesos a solo 1B: deben alojarse los pesos completos de los expertos y demás componentes.
- La prueba IQ2_M demuestra que esta combinación concreta de modelo, cuantización y llama.cpp sí se ejecutó en el MSI. No extrapolar su velocidad a Q4_K_M, otros contextos, otros builds ni otros motores.
- La ficha GGUF por sí sola no acredita compatibilidad universal. La compatibilidad con llama.cpp queda demostrada para el artefacto/configuración de la prueba registrada; no se da por demostrada para TensorFold, RustingStrata, Magnitude u otros runtimes.
- No se ha registrado en este inventario una ejecución Ling-3.0-Tiny con TensorFold. Una eventual integración debe empezar por verificar el soporte de la arquitectura `bailing_hybrid` y del GGUF concreto, en una rama aislada.
- No reutilizar como hechos técnicos estimaciones genéricas de tamaños Q4/Q5/Q8 ni afirmaciones de una topología concreta de expertos/capas sin contrastarlas con los metadatos y el archivo exacto de la variante. El tamaño del fichero cuantizado tampoco equivale a la memoria RAM/VRAM total durante inferencia.

**Clasificación:** modelo ejecutado y medido en el MSI con llama.cpp CUDA (IQ2_M); análisis de portabilidad a otros motores pendiente. No es una nueva campaña ni una nueva medición.

| **Ling-3.0-Tiny** | GGUF Q4_K_M | llama.cpp CPU · GB-BXi7-5500 | PP 41,0 tok/s; generación 15,5 tok/s | Equipo distinto del MSI; mantener separado. |
| **Spark-X2.6-4B-abliterated** | GGUF Q4_K_M | llama.cpp CUDA · RTX 3050 | Prueba funcional: prefill 36,9 tok/s; generación 7,2 tok/s | Ejecución individual; faltan repeticiones y perfil de memoria normalizado. |
| **TwIL-8B** | GGUF Q4_K_M balanced | llama.cpp CUDA · RTX 3050 | Campaña de 24 y 26 capas GPU; protocolo y tres repeticiones en informe | Inferencia funcional medida. Arquitectura Granite no soportada por la capacidad observada de TensorFold 1.2.0. |
| **Qwen3.5-4B** | MLX-4bit | TensorFold PR #1879 · CUDA sm_86 | Build CUDA y suites host validadas; ejecución GPU real; decode aprox. 56,5 tok/s en esa ejecución | Validación del parche, no benchmark A/B formal ni prueba de todas las rutas. |

## 3. Intentos, estudios e investigación (no contar como benchmark)

### TensorFold Web standalone — estado de integración (12-11-2026)

Se verificó la rama de LEONES `feat/tensorfold-web-standalone` y su actualización local hasta el commit `20d5fc20`. La aplicación web y su bridge Python están ejecutándose en `127.0.0.1:8787`; el bridge apunta al motor en `http://127.0.0.1:8080`. El proceso del bridge observado fue `tensorfold-web-bridge.py`; no se detuvo ni se modificó durante esta comprobación.

**Versión y catálogo:** `tensorfold-native 1.2.0`, instalado en `~/.local/opt/tensorfold-1.2.0-linux-x86_64/bin/tensorfold-native`. `capabilities --json` declara engine Zig, chip `nvidia-sm86`, backend `cuda`, familia `qwen3_5` con formatos `mlx-q4g64` y `exl3`, y familia `qwen3_5_moe` con `mlx-q4g64`, `modelopt-mixed` y `modelopt-nvfp4`. El comando `models` devuelve, entre otros, `mlx-community/Qwen3.5-4B-MLX-4bit` y `Qwen/Qwen3.5-4B`. Esto acredita presencia en el catálogo local, no que los pesos estén descargados, que el modelo cargue correctamente ni que quepa en la VRAM disponible.

**Integración de la interfaz:** el bridge implementa `/api/engine/inspect`, `/api/engine/start`, `/api/engine/stop` y `/api/engine/status`. La vista Servidor permite inspeccionar la ayuda del binario, construir argumentos admitidos y gestionar el proceso hijo. La vista Panel integra el dashboard original en un iframe a través de `/api/dashboard`; la interfaz informa de que el motor debe iniciarse con `--dashboard` para habilitar `/dashboard` y `/stats`. La ayuda de TensorFold 1.2.0 confirma que `--dashboard` es una opción de `serve`.

**Estado real observado:** `/api/engine/status` devolvió `managed:false`, `running:false`, `pid:null`; el log del motor estaba vacío. No había proceso `tensorfold-native`, el puerto 8080 estaba libre y `http://127.0.0.1:8080/health` rechazaba la conexión. En consecuencia, la UI/bridge sí estaban activos, pero el motor TensorFold no estaba arrancado ni gestionado por la UI. No se registró inferencia, carga de modelo, dashboard nativo servido ni rendimiento en esta sesión.

**Próximo paso de validación:** inspeccionar `tensorfold-native info mlx-community/Qwen3.5-4B-MLX-4bit`, confirmar la disponibilidad real de los pesos y memoria libre, revisar el comando completo que construye el bridge y solo entonces iniciar una única instancia controlada con CUDA, puerto 8080, `--dashboard`, contexto conservador y paralelismo 1. Después, verificar `/health`, `/v1/models`, `/stats`, `/dashboard` y una petición de chat completa. Hasta completar esos pasos, clasificar TensorFold Web como **integración de interfaz en validación; motor e inferencia pendientes**, no como nuevo benchmark ni como una nueva ejecución de Qwen3.5-4B.

| Modelo / proyecto | Motor / entorno | Trabajo realizado | Estado correcto |
|---|---|---|---|| **Project Maya v1.1.31** | Evaluación documental del motor MoE especializado | Release [v1.1.31](https://github.com/mw00/project-maya/releases/tag/v1.1.31); modelos densos y MoE | Evaluación de arquitectura, gestión jerárquica VRAM/RAM/SSD, cuantización/model packs y API local. Modelos densos genéricos como Qwen3.5-4B y Qwen3.5-30B-A3B no tienen compatibilidad confirmada en esa release; no asumir soporte GGUF universal. Los motores especializados documentados se dirigen a GLM-5.3-Flash, DeepSeek-V4.1-Flash y MiniMax-M3.1-Flash. |\n| **Qwen3.5-35B-A3B** | TensorFold | Estimación de memoria y análisis de compatibilidad; pesos estimados en torno a 20,4 GB en el formato estudiado | Sin inferencia TensorFold validada en el MSI. |
| **Qwen3.5-35B-A3B IQ2_XXS** | Kinetic | Modelo identificado/seleccionado para campaña | Vincular log definitivo antes de declarar velocidad medida. |
| **Magnitude 0.2.15 — servicio y catálogo** | Servicio systemd `magnitude.service` / CLI | Actualización del paquete DEB a 0.2.15; servicio `Ready`, procesos `magnitude-service` y `magnitude-inference`; escucha `0.0.0.0:10100`, `requireApiKey=true`; `curl http://127.0.0.1:10100/` devolvió HTTP 200. `magnitude catalog list` mostró únicamente MiniCPM5 1B Q4. | **Instalación y disponibilidad del servicio verificadas**, no benchmark de inferencia. URL local `http://127.0.0.1:10100`; acceso desde otros dispositivos sujeto a clave de red. No había modelo activo. El HTML inicial declara `lang="en"`; esto solo acredita el idioma del documento raíz, no una auditoría completa de localización de la interfaz. |\n| **Qwen3.5-4B** | Magnitude 0.2.10 | Descarga/verificación de pesos y proyector; ID no reconocido por CLI | Sin inferencia. |
| **Qwen3.5-9B** | Estudio TensorFold / RTX 3050 | Informe de memoria, cuantización y viabilidad; comparación E-means frente a K-means | Estudio técnico, no ejecución local validada del 9B. |
| **Qwen3.5-122B-A10B** | Estudio RTX 5090 | Evaluación teórica de memoria y cuantización | No ejecutado en hardware local. |
| **Clover-35B-A3B-Preview** | Investigación documental + validación empírica de artefacto GGUF IQ2_S | Arquitectura MoE de difusión, 35B parámetros totales y aprox. 3B activos por token; contexto anunciado hasta 128K; pesos BF16 publicados aprox. 69,3 GB. | **El modelo original completo no es viable en el MSI**, pero un artefacto comunitario IQ2_S de 13.795.534.208 bytes sí se cargó y generó texto con llama.cpp CUDA; resultados en §2. RTX 3050 4 GiB VRAM y 14 GiB RAM física no permiten cargar el modelo BF16/INT4 completo. La ejecución IQ2_S no valida otras cuantizaciones ni otros backends. INT4/Q4 (~19–23 GB) y 2-bit (~11–14 GB) siguen siendo estimaciones, no pruebas. Mantener Experimental; distinguir el artefacto comunitario de los pesos oficiales. Referencias: [repositorio oficial](https://github.com/DiffuSpace/Clover-35B-A3B-Preview), [ficha upstream](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview), [GGUF IQ2_S probado](https://huggingface.co/na0x2c6/Clover-35B-A3B-Preview-GGUF), [anuncio técnico](https://diffuspace.ai/blog/clover-35b/). |
| **MiniCPM5 1B** | GGUF Q4 (ID de catálogo `minicpm5-1b:gguf:q4`) | Magnitude 0.2.15 · MSI Thin 15 B12UC | El catálogo local declara 3,9 GB de memoria, velocidad estimada ~68–101 tok/s, contexto 128K y aceleración `None`; es el único modelo que la versión presenta como compatible. | **Solo recomendación/estimación de catálogo.** No se descargó, cargó ni ejecutó; 68–101 tok/s no es una medición LEONES. La GPU RTX 3050 4 GB aparece detectada por `magnitude hardware`, pero el catálogo indica que este modelo no usa aceleración. Memoria GPU actual no disponible en el informe de hardware. |\n| **Qwen3.5-4B AWQ W4A16** | Inspección de modelo | Ficha/candidato evaluado | No ejecutado. |\n| **Qwen3.5-4B MTP-GGUF Q4_K_M (receta ThumbLLM)** | TeksEdge ThumbLLM / llama.cpp CPU | Modelo `unsloth/Qwen3.5-4B-MTP-GGUF`; SHA-256 de la receta: `3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630`. Runtime upstream `c060ca974` (build 10603). Contexto de receta 65.536, KV `q4_0`, batch/ubatch 2048/512, Flash Attention, mmap/repack. | Configuración de referencia analizada, no ejecutada aún en Ubuntu. Aunque el repositorio del modelo contiene MTP en el nombre, la receta usa `SPEC_TYPE=none`; no hay speculative decoding activo. El ejecutable de la release es Windows x64. La cifra upstream de ~18 tok/s es una observación durante generación, no un benchmark controlado y no comparable directamente. |
| **YASAKANI** | Prueba exploratoria | Investigación y preparación solicitadas | Sin resultado reproducible consolidado. |
| **Colibri / Qwen3.6 CUDA** | Auditoría de código | Parser de colocación, límites de componentes/segmentos y buffers | No atribuir rendimiento de inferencia a esta auditoría. |
| **Ornith-1.5-9B-OBLITERATED** | ThumbLLM Release 1 / llama.cpp CPU · Ubuntu MSI | Paquete upstream incorporado a rama experimental de LEONES; documentación de reproducción y scripts de setup/serve preparados. GGUF Q4_K_M, SHA-256 de referencia 88ce99bb696fbc921edc4f995c4beb12a66bf94319d00bfd5f44265d02fa6dfb; llama.cpp b10603, commit c060ca974; configuración de referencia: contexto 65.536, batch 2.048, ubatch 512, KV Q4_0, 8 hilos decode y 16 batch. | **Preparación, no ejecución local acreditada.** No hay todavía log de descarga, compilación, carga del GGUF ni generación en el MSI; no registrar tok/s. La receta de upstream cita aproximadamente 13,03 tok/s de generación y 1.302 tok/s de prompt en Ryzen 7 7840HS/Windows 11, cifras de referencia externa no reproducidas ni comparables con el MSI. |
| **Uzu inference runtime** | Uzu + Lalamo | Evaluación de fuentes públicas, plataforma Linux/Ubuntu, backend CUDA, formatos y compatibilidad potencial con Qwen3.5-4B y Qwen MoE. Registro definitivo en `Experimental`, PR #119 fusionado. | `RESEARCH_ONLY / NOT VERIFIED`; no se ejecutará en el laboratorio. No hay compilación, inferencia ni benchmark local acreditados. [Documento experimental](../../experimental/uzu/README.md). |
| **Mistral.rs, vLLM, SGLang, KTransformers** | Evaluación de runtimes | Instalación/soporte/requisitos estudiados | Sin benchmark local normalizado en este inventario. |

## 3.1 Project Maya — evaluación de versión y viabilidad en MSI

- **Release evaluada originalmente:** [Project Maya v1.1.31](https://github.com/mw00/project-maya/releases/tag/v1.1.31).
- **Integración posterior en LEONES:** PR [#142](https://github.com/robertosantosx2/LEONES/pull/142), rama `research/kinetic-audit-benchmark`; fuente fijada en `a3582528bfb73175fed1757b485bfcaaf01aaeaa` (línea v1.1.58), con snapshot upstream vendorizado. La versión 1.1.31 es la versión de esta evaluación, no la versión fijada actualmente en la integración.
- **Naturaleza:** familia de motor independiente, con implementaciones y model packs específicos. No tratarlo como backend genérico compatible con cualquier GGUF ni como sustituto directo de llama.cpp/TensorFold.
- **Arquitecturas/modelos:** el catálogo incorporado en PR #142 registra GLM-5.3, GLM-5.3-Flash, DeepSeek-V4.1-Flash y MiniMax-M3.1-Flash. La compatibilidad con Qwen3.5-4B denso y Qwen3.5-30B-A3B MoE no está acreditada por la evaluación v1.1.31; no registrar esos modelos como soportados sin una prueba explícita del upstream.
- **Memoria y MSI:** el upstream documenta un suelo de 32 GiB de RAM del sistema y almacenamiento NVMe rápido. El MSI de referencia dispone de 14 GiB RAM y RTX 3050 Laptop de 4 GiB VRAM. Por tanto, el equipo queda por debajo del mínimo de RAM; swap no sustituye RAM física y no convierte los modelos de decenas/cientos de GB en una opción práctica. **No descargar model packs ni ejecutar el setup de Maya en el MSI.**
- **Denso:** no hay evidencia de un motor denso universal ni de carga de Qwen3.5-4B. Para modelos densos pequeños del laboratorio, mantener TensorFold y llama.cpp como referencias validadas.
- **MoE:** el diseño de Maya distribuye pesos/expertos entre VRAM, RAM y SSD y optimiza modelos MoE concretos. Esa estrategia no elimina el requisito de memoria del host. Los model packs de Maya-XS citados en la integración posterior tienen tamaños de descarga desde decenas de GB (aprox. 73–93 GB para los más pequeños del catálogo, y bastante más para DeepSeek); no equivalen a memoria residente ni a una promesa de rendimiento.
- **Rendimiento:** los factores de aceleración anunciados por upstream para speculative decoding/decoding son resultados del entorno del proyecto. No son extrapolables a la RTX 3050 ni deben copiarse al inventario como mediciones LEONES.
- **Interfaces:** API compatibles con OpenAI `/v1/chat/completions` y Anthropic `/v1/messages`, además de interfaz web/monitorización según la integración documentada.
- **Licencias:** separar licencia del código del motor y licencia/condiciones de cada modelo y model pack; la licencia del repositorio no concede derechos de redistribución de pesos.
- **Estado LEONES:** `EXPERIMENTAL / DOCUMENTED / NOT RUN ON MSI`. El adaptador permanece deliberadamente deshabilitado; registro de fuentes/modelos y documentación no significan orquestación runtime completa. La ejecución física requiere un host compatible, setup/reload de model pack, procedencia de los binarios específicos y smoke test de API.

**Decisión:** conservar Project Maya en Experimental como familia independiente y como referencia arquitectónica para MoE de gran tamaño. No priorizar su ejecución en el MSI actual. No declarar compatibilidad con Qwen denso/MoE ni rendimiento local hasta disponer de evidencia reproducible.

## 3.2 Modelos de difusión de lenguaje (dLLM) — evaluación documental, CPU como referencia

Esta familia genera texto mediante refinamiento iterativo de tokens enmascarados o parcialmente definidos, en lugar de la decodificación causal token a token habitual. La generación paralela no implica por sí sola menor latencia: el coste depende del número de pasos de refinamiento, el tamaño de bloque, la cuantización, el hardware y la implementación del motor.

**Equipo de referencia para esta evaluación:** GB-BXi7-5500 con Intel Core i7-5500U (2 núcleos / 4 hilos), Ubuntu. La referencia autoregresiva local es LFM3-1.7B GGUF Q4_K_M, aproximadamente 15–16 tok/s de generación en la campaña archivada. Es una referencia orientativa: no existe todavía una comparación dLLM frente a LFM3 con idéntico prompt, longitud de salida y protocolo en ese equipo.

| Modelo / familia | Tamaño / arquitectura | Motor y compatibilidad | Viabilidad para el CPU de referencia | Estado LEONES |
|---|---|---|---|---|
| **LLaDA-8B-Instruct** | 8.02B parámetros; difusión por enmascaramiento, backbone tipo LLaMA | Implementación oficial PyTorch/Transformers; conversor y soporte declarados por diffuse-cpp | El modelo cuantizado Q4_K_M publicado por diffuse-cpp ocupa aproximadamente 4.5–5.1 GB según su documentación. Puede caber en 14 GiB de RAM en principio, pero no hay medición en i7-5500U y no se espera asumir velocidad interactiva. La RTX 3050 de 4 GiB no puede alojarlo íntegramente en VRAM. | Candidato de referencia para estudiar dLLM, no descargado ni ejecutado. |
| **Dream-v0-Instruct-7B** | 7.6B parámetros; difusión, backbone Qwen2.5 con GQA | Implementación oficial PyTorch; conversor y soporte declarados por diffuse-cpp | Mismas reservas de memoria y rendimiento que LLaDA-8B. Sin prueba en el i7-5500U. | Candidato secundario; no descargado ni ejecutado. |
| **iLLaDA-8B-Instruct** | 7.62B parámetros; difusión bidireccional enmascarada, contexto anunciado de 8.192 | Checkpoint publicado por GSAI-ML; el repositorio oficial indica reutilización del código LLaDA mediante `mask_id=5`. No se ha verificado conversión/compatibilidad con diffuse-cpp. | Demasiado grande para VRAM completa de 4 GiB; ejecución CPU no probada. Su benchmark de modelo no acredita rendimiento en este equipo. | Seguimiento documental; no ejecutar hasta verificar soporte del motor y cuantización. |
| **LLaDA-MoE-7B-A1B-Instruct** | MoE de 7B totales y aprox. 1B activos por inferencia, según el repositorio oficial | Implementación oficial LLaDA; diffuse-cpp no declara soporte para esta variante MoE | Los parámetros activos reducen cómputo por token, pero no eliminan el almacenamiento de expertos. No asumir que cabe en 4 GiB VRAM ni que diffuse-cpp lo soporte. | Investigación futura; sin ejecución ni benchmark. |
| **Tiny-A2D / repositorio dllm citado en conversación** | Identidad, arquitectura, número de parámetros y checkpoint no verificados con evidencia primaria suficiente | No se ha confirmado un runtime reproducible ni un artefacto descargable inequívoco | No clasificar como modelo pequeño ejecutable ni asignar requisitos/rendimiento. | Referencia no verificada; excluida de candidatos aprobados hasta identificar modelo, paper y pesos exactos. |

### Motor: diffuse-cpp

- [Repositorio upstream](https://github.com/iafiscal1212/diffuse-cpp): motor C++ basado en GGML para inferencia de modelos de difusión de lenguaje.
- El README declara soporte para **LLaDA-8B-Instruct** y **Dream-v0-Instruct-7B**, cuantización Q4_K_M y funciones como caché entre pasos y planificación adaptativa del número de iteraciones.
- El upstream publica resultados de **14–28 tok/s en prompts fáciles** con Q4_K_M, caché y salida adaptativa. Su tabla de benchmark identifica un **AMD EPYC 4465P de 12 núcleos / 12 hilos, 125 GB RAM**, por lo que estas cifras no son transferibles al Intel i7-5500U de 2 núcleos / 4 hilos. No se deben presentar como rendimiento esperado ni como resultado LEONES.
- La cifra de tamaño de los pesos cuantizados (aprox. 4.5–5.1 GB) no incluye necesariamente todos los buffers, contexto ni memoria de proceso.
- No confundir el paralelismo de refinamiento con generación causal. Las métricas de tokens/s de motores distintos pueden contar trabajo de forma diferente; una comparación justa debe fijar texto final, pasos, tokens útiles, latencia total y calidad.

### Decisión y plan de evaluación

1. Registrar **diffuse-cpp + LLaDA-8B-Instruct Q4_K_M** como primer experimento técnico, condicionado a verificar licencia, artefacto, dependencias y compatibilidad real del build con el CPU Intel.
2. Mantener **Dream-v0-Instruct-7B** como segundo candidato si la primera ruta funciona.
3. Seguir **iLLaDA-8B-Instruct** por su mejora declarada sobre LLaDA, pero no asumir compatibilidad GGUF/diffuse-cpp hasta que exista conversor o soporte explícito.
4. Mantener **LLaDA-MoE-7B-A1B** en investigación: el 1B activo no significa pesos totales de 1B y el motor diffuse-cpp no declara soporte MoE.
5. No descargar ni ejecutar todavía en el MSI RTX 3050 como objetivo primario. El primer benchmark debe ser CPU-only en el GB-BXi7-5500 y registrar RAM máxima, tiempo total, tokens útiles/s, número de pasos, calidad en español y estabilidad.
6. Comparar con LFM3-1.7B usando exactamente la misma batería de tareas (extracción, aritmética, razonamiento breve, comprensión y español), límites de salida y protocolo. El umbral de referencia es 15–16 tok/s de generación LFM3, no una cifra publicada en otro procesador.

**Fuentes primarias y cautelas:** [diffuse-cpp](https://github.com/iafiscal1212/diffuse-cpp) · [LLaDA oficial](https://github.com/ML-GSAI/LLaDA) · [Dream oficial](https://github.com/DreamLM/Dream) · [iLLaDA-8B-Instruct](https://huggingface.co/GSAI-ML/iLLaDA-8B-Instruct). Los resultados de benchmark y las capacidades se atribuyen a sus respectivos proyectos; no son pruebas locales LEONES.

### Resultados consolidados de modelos de difusión — mediciones locales y referencias externas

Esta tabla amplía el catálogo anterior con las cifras de rendimiento disponibles. Se mantiene la procedencia explícita: **MEASURED-LEONES** identifica una ejecución local comunicada/registrada en el laboratorio; **EXTERNAL_REFERENCE** identifica cifras publicadas por los proyectos upstream. No se mezclan en un ranking único porque los equipos, motores y definiciones de throughput son diferentes.

| Modelo | Runtime | Hardware | Resultado | Estado / interpretación |
|---|---|---|---:|---|
| **Open-dCoder 0.5B** | Transformers / Open-dLLM | MSI Thin 15 · RTX 3050 4 GiB | **140,30 posiciones/s**; VRAM observada **1,184 GiB** | **MEASURED-LEONES** según la ejecución local archivada en el historial del experimento. La unidad es posiciones/s; no convertir ni comparar como tok/s. |
| **Dream-7B** | diffuse-cpp | AMD EPYC 4465P · 12 hilos | **≈11,6 tok/s** promedio citado | **EXTERNAL_REFERENCE**. Configuración Q4_K_M con optimizaciones de caché/early-exit indicadas por upstream. |
| **LLaDA-8B** | diffuse-cpp | AMD EPYC 4465P · 12 hilos | **≈15,3 tok/s** promedio citado | **EXTERNAL_REFERENCE**. Configuración Q4_K_M con optimizaciones de caché/early-exit indicadas por upstream. |
| **Dream-v0-Instruct-7B** | llama.cpp, ejemplo de difusión | NVIDIA A100 | **11,98 tok/s** publicados; **166,91 ms/paso** | **EXTERNAL_REFERENCE**. Longitud máxima 512 y 256 pasos; no asumir que tok/s significa tokens nuevos/s. |

#### Resultados externos por tarea: diffuse-cpp

| Tarea | Dream-7B | LLaDA-8B |
|---|---:|---:|
| Pregunta factual | 21,6 tok/s | 24,4 tok/s |
| Traducción francesa | 14,3 tok/s | 27,7 tok/s |
| Aritmética | 21,6 tok/s | 15,7 tok/s |
| Traducción española | 13,2 tok/s | 22,9 tok/s |
| Programación | 8,2 tok/s | 4,9 tok/s |
| Escritura creativa | 4,5 tok/s | 5,3 tok/s |

Las cifras por tarea son resultados upstream y no deben combinarse con los promedios generales de la tabla anterior sin reproducir el mismo protocolo. Para Dream en A100, el desglose publicado es 108,24 ms de forward/cálculo y 58,67 ms de muestreo por paso; total medio 166,91 ms/paso.

#### Modelos sin resultado de rendimiento verificable en el inventario

Dream-Coder-7B, DiffuCoder-7B, DiffuLLaMA, ELYZA-Diffusion-Instruct, DiffusionGemma-26B-A4B, LLaDA2.x, iLLaDA-8B y LLaDA-MoE permanecen como **PENDIENTE / NO MEDIDO**. La disponibilidad de pesos, una ficha de modelo o una cifra de parámetros no acredita ejecución ni velocidad.

**Clover-35B-A3B-Preview** dispone de un experimento local separado con llama.cpp CUDA y cuantización IQ2_S. Sus cifras (decode 4,90 tok/s y prefill 3,60 tok/s en la prueba Jinja de 256 tokens) se conservan en su [informe específico](../CLOVER-35B-A3B-PREVIEW-RTX3050-2026-10-31.md). No se agregan a las métricas de diffuse-cpp/Dream/LLaDA: el runtime y la ruta de ejecución son distintos y la métrica de throughput no demuestra por sí sola equivalencia metodológica con los DLM anteriores.

#### Criterios de comparación

- **posiciones/s** de Open-dCoder no es intercambiable con tokens/s.
- Diferenciar tokens nuevos/s, tokens de secuencia/s y throughput agregado; verificar la definición de cada benchmark upstream.
- Registrar pasos de denoising, tokens resueltos por paso, longitud de prompt/salida, early-exit, caché, cuantización y tiempo de muestreo.
- No extrapolar los resultados de EPYC o A100 al i7-12650H/RTX 3050.
- No atribuir a TensorFold compatibilidad con dLLM: sigue **no acreditada** en la matriz de runtimes.
**Fuentes:** [Open-dLLM / Open-dCoder](https://github.com/pengzhangzhi/Open-dLLM) · [diffuse-cpp y benchmarks](https://github.com/iafiscal1212/diffuse-cpp) · [Dream](https://github.com/DreamLM/Dream) · [LLaDA](https://github.com/ML-GSAI/LLaDA) · [llama.cpp — benchmark Dream](https://github.com/ggml-org/llama.cpp/discussions/22972).

## 3.3 NVIDIA DeepSeek-V4.1-Flash-1017-NVFP4 — evaluación documental inicial (12-11-2026)

**Artefacto oficial identificado:** [`nvidia/DeepSeek-V4.1-Flash-1017-NVFP4`](https://huggingface.co/nvidia/DeepSeek-V4.1-Flash-1017-NVFP4), publicado bajo la cuenta oficial `nvidia` de Hugging Face. No confundirlo con las cuantizaciones comunitarias de nombre parecido.

**Metadatos consultados en Hugging Face (12-11-2026):**
- Autor: NVIDIA (`nvidia`); arquitectura declarada: `deepseek_v41`.
- Tarea declarada por el Hub: `image-text-to-text`; biblioteca: Model Optimizer.
- Formato/etiquetas: Safetensors, ModelOpt, cuantización FP4/NVFP4; el repositorio también lleva etiquetas FP8/8-bit y referencia como modelo base a `deepseek-ai/DeepSeek-V4.1-Flash-1017`.
- Licencia declarada en el Hub: MIT.
- Parámetros mostrados por los metadatos del repositorio: 664.898,4 M. Esta cifra se transcribe como metadato del Hub y no se interpreta aquí como número de parámetros activos.
- Última actualización que mostraba la ficha al consultarla: 30-10-2026.

**Aclaración sobre los 81 GB:** la identificación del repositorio confirma que existe un checkpoint oficial NVIDIA NVFP4, pero la consulta de metadatos realizada no expuso un tamaño total de descarga de 81 GB ni un manifiesto de archivos que permita verificar esa cifra. Por tanto, **81 GB queda como dato comunicado/pendiente de verificar**, no como tamaño confirmado del checkpoint. No reutilizar cifras de otros repositorios, variantes o estimaciones de memoria como si fueran el tamaño de este artefacto. Antes de descargar, comprobar en la pestaña *Files and versions* el tamaño acumulado de todos los shards y los archivos auxiliares; distinguir tamaño en disco, memoria residente, VRAM y memoria total requerida durante inferencia.

**Viabilidad preliminar en el MSI Thin 15 B12UC:** equipo de referencia con Intel Core i7-12650H, 14 GiB RAM, RTX 3050 Laptop 4 GiB VRAM, Ubuntu, driver NVIDIA 580.178.04 y swap de 32 GiB. No se ha descargado ni ejecutado este modelo. La VRAM no permite alojar el modelo completo y la RAM física del equipo está muy por debajo de lo que cabe esperar para un checkpoint MoE de esta escala. El swap no debe contabilizarse como sustituto de RAM ni como solución de rendimiento. La activación de un subconjunto de expertos por token tampoco elimina la necesidad de almacenar/acceder a los pesos de los expertos y componentes auxiliares.

**Compatibilidad/runtime:** el repositorio está etiquetado para NVIDIA Model Optimizer y Safetensors. No se ha demostrado que este checkpoint sea GGUF ni que pueda cargarse directamente con los binarios locales de llama.cpp, TensorFold, RustingStrata, Kinetic o Colibri. Tampoco se ha validado una receta de ejecución en la RTX 3050. No atribuirle compatibilidad con vLLM/SGLang ni requisitos exactos de GPU sin comprobar la configuración oficial de inferencia y las versiones de runtime asociadas a este checkpoint.

**Estado LEONES:** `RESEARCH_ONLY / OFFICIAL_CHECKPOINT_IDENTIFIED / NOT_DOWNLOADED / NOT_RUN_ON_MSI`. No es benchmark ni prueba de compatibilidad. Siguiente paso: auditar la lista completa de archivos y su tamaño real, revisar la configuración/model card oficial de NVIDIA y comprobar si existe una modalidad de despliegue remoto o particionado que no requiera cargar todos los pesos en el MSI. No iniciar una descarga masiva hasta cerrar esa auditoría.

**Fuente primaria:** [NVIDIA — DeepSeek-V4.1-Flash-1017-NVFP4 en Hugging Face](https://huggingface.co/nvidia/DeepSeek-V4.1-Flash-1017-NVFP4).


### Mage-VL-Cowork (Microsoft Mage, 4B) — agente híbrido de uso del ordenador

**Clasificación LEONES:** `RESEARCH_ONLY / DOCUMENTED / NOT RUN ON MSI`. Es un agente multimodal de *computer use* (CUA), no un modelo conversacional general ni un motor de inferencia. Una única política visión-lenguaje decide entre dos canales de actuación: (1) GUI, basada en capturas de pantalla y acciones de ratón/teclado, y (2) código/terminal, para operar mediante comandos, scripts y bibliotecas de aplicaciones. El objetivo es alternar ambos canales dentro del mismo agente, sin depender de un router externo para escogerlos.

**Aportación técnica:** el informe del equipo Microsoft Mage describe un currículo progresivo de cinco etapas: GUI-oriented midtraining, GUI-agent SFT, coding/terminal SFT, hybrid CUA SFT y online hybrid RL. La página del proyecto informa de 293.806 tareas sintéticas, 6.915 habilidades y 318.837 trayectorias retenidas para la construcción del corpus. El resultado de entrenamiento que debe destacarse no es solo el tamaño 4B, sino el aprendizaje de cuándo conviene interactuar visualmente con una aplicación y cuándo ejecutar código o comandos para completar la misma tarea.

**Resultados publicados por Microsoft (no reproducidos por LEONES):**

| Evaluación | Resultado | Protocolo / interpretación |
|---|---:|---|
| OSWorld-Verified — checkpoint final RL | **66,04%** (redondeado por el proyecto a 66,0%) | Media de dos pasadas independientes: 65,33% y 66,75%; 361 tareas retenidas, excluyendo Google Drive; presupuesto de 50 pasos; escritorio 1920×1080. |
| OSWorld — GUI Agent SFT | 45,56% | Etapa GUI previa a la unificación híbrida. |
| OSWorld — Hybrid CUA SFT | 55,84% | Etapa posterior a la combinación GUI + terminal. |
| OSWorld — Online Hybrid RL | 66,04% | Mejora de 10,20 puntos porcentuales frente a Hybrid CUA SFT (la página también informa +10,16 pp usando valores internos no redondeados). |
| WebVoyager-Static — checkpoint SFT | **58,6% (377/643)** | Evaluación estática en 15 sitios; resultado del checkpoint SFT, no del checkpoint RL final. |

La tabla de categorías OSWorld publicada por el proyecto da 87,5% en tareas de sistema operativo, 64,9% en Office, 65,0% en uso diario, 66,3% en tareas profesionales y 62,7% en workflows multiaplicación. Estas cifras pertenecen al protocolo y harness del equipo autor; no son una puntuación de inteligencia general ni deben mezclarse con benchmarks de LLM de texto.

**Artificial Analysis:** a fecha de esta actualización no se ha localizado una ficha individual verificable de Mage-VL-Cowork en el catálogo público de modelos de Artificial Analysis ni una puntuación suya en el Intelligence Index. Por tanto, registrar **Artificial Analysis Intelligence Index: N/D — no listado/verificado**, no asignarle posición ni estimar un índice a partir del 66,0% de OSWorld. OSWorld mide éxito de tareas de interacción con escritorio; Artificial Analysis Intelligence Index mide capacidades generales mediante otra batería. No son magnitudes intercambiables.

**Compatibilidad y viabilidad en el MSI Thin 15 B12UC:** el equipo de referencia tiene Intel Core i7-12650H, 14 GiB de RAM y RTX 3050 Laptop de 4 GiB VRAM. El checkpoint oficial está publicado en Hugging Face y el repositorio oficial ofrece código de entrenamiento/evaluación, pero esta revisión documental no ha verificado un paquete GGUF oficial, soporte de la arquitectura en llama.cpp/TensorFold, una ruta de inferencia CUDA para Ubuntu ni memoria total en ejecución. No asumir que 4B parámetros equivalen a 4 GB de memoria ni reutilizar tamaños de cuantización comunitaria sin verificar artefactos, hashes, arquitectura y runtime. El agente también requiere un entorno de ejecución de herramientas y escritorio compatible; cargar los pesos por sí solo no reproduce el sistema CUA.

**Estado experimental:** no descargado, compilado, cargado ni ejecutado en el MSI; no hay velocidad, TTFT, consumo máximo RAM/VRAM ni tasa de éxito local. El 66,0% y el 58,6% son resultados upstream, no resultados LEONES. Antes de planificar una prueba local, auditar el README y los requisitos de inferencia del repositorio oficial, verificar formato/arquitectura y dependencias, y preparar un escritorio de prueba aislado con permisos mínimos. No conceder al agente acceso irrestricto al host, credenciales ni archivos personales.

**Fuentes primarias:**
- [Página técnica oficial de Mage-VL-Cowork](https://microsoft.github.io/Mage/cowork/)
- [Informe técnico arXiv: 2610.40747](https://arxiv.org/abs/2610.40747)
- [Modelo y model card oficial en Hugging Face](https://huggingface.co/microsoft/Mage-VL-Cowork)
- [Código oficial Microsoft/Mage — mage_vl_cowork](https://github.com/microsoft/Mage/tree/main/mage_vl_cowork)


## 3.4 Comparación documental: Qwen3.5-35B-A3B y Nemotron 3.5 Lightning (12-11-2026)

Esta comparación amplía la evaluación de familias MoE. **No es un benchmark LEONES**: los resultados de inteligencia proceden de las fichas y evaluaciones oficiales de cada fabricante, con protocolos distintos. No deben interpretarse como una prueba head-to-head.

| Característica | Qwen3.5-35B-A3B | NVIDIA Nemotron 3.5 Lightning 30B-A3B |
|---|---:|---:|
| Parámetros totales declarados | 35B (≈36B en el resumen de artefactos HF) | 30B |
| Parámetros activos por token | 3B | 3B |
| Arquitectura | Híbrida Gated DeltaNet + Gated Attention + MoE | Híbrida Mamba-2 + MoE + atención |
| Expertos | 256; 8 routed + 1 shared activados | 128 routed; top-6 + 1 shared |
| Contexto | 262.144 nativo; extensible hasta ≈1,01M | Hasta 1M anunciado por NVIDIA |
| Modalidad | Texto con encoder de visión | Texto |
| Enfoque destacado | Modelo general multimodal, razonamiento y código | Ejecución eficiente, agentes de larga duración y uso de herramientas |
| Estado en el MSI | Ejecutado con Tandem/llama.cpp CPU-MoE, IQ2_XXS; véase tabla de mediciones | No ejecutado ni medido en el MSI |

**¿Cuál es más pesado?** Qwen3.5-35B-A3B: tiene 5B parámetros más (aprox. 16,7 % más que 30B). Ambos activan aproximadamente 3B por token. La activación similar no significa que ocupen la misma memoria: deben almacenarse o recuperarse los pesos de todos los expertos, además de embeddings, capas compartidas, cachés y estados.

**¿Cuál parece más capaz?** Los resultados oficiales publicados por Qwen son superiores en varias pruebas comunes de razonamiento y programación: Qwen informa GPQA Diamond 84,2, MMLU-Pro 85,3 y SWE-bench Verified 69,2. NVIDIA informa para Nemotron Lightning NVFP4 GPQA Diamond 75,57, MMLU-Pro 81,62 y SWE-bench Verified 52,80. Son cifras de evaluaciones de cada fabricante y no se han obtenido con un protocolo común; por ello son indicios, no una clasificación concluyente. La lectura prudente es que Qwen tiene mejores cifras publicadas en esos indicadores, mientras que Nemotron está especialmente orientado a cargas agentic, ejecución sostenida y decodificación especulativa (MTP, DFlash/DSpark). No afirmar que Nemotron sea globalmente menos inteligente a partir de esta tabla.

**Compatibilidad TensorFold:** la instalación local verificada es TensorFold Native 1.2.0. Su salida de capacidades declara la familia `qwen3_5_moe` con formatos `mlx-q4g64`, `modelopt-mixed` y `modelopt-nvfp4`; esto no demuestra que cualquier checkpoint Qwen3.5-35B-A3B pueda cargarse en el MSI ni que quepa en 4 GiB de VRAM. En esa versión local no se registró la familia Nemotron Lightning en `capabilities --json`. La presencia de recetas o soporte en la rama actual de TensorFold no debe atribuirse retroactivamente al binario 1.2.0. Nemotron requiere una verificación específica de arquitectura, formato, kernels y memoria antes de intentar su ejecución.

**Viabilidad en el MSI Thin 15 B12UC:** con 14 GiB de RAM y RTX 3050 Laptop de 4 GiB, ninguno debe considerarse un modelo íntegramente residente en VRAM. Qwen ya cuenta con una ejecución real en Tandem/llama.cpp CPU-MoE: IQ2_XXS, contexto 1024, decode ≈35,6 tok/s en la prueba no-thinking, con RSS ≈9,27 GiB y swap ≈7,5 GiB. Ese resultado no predice el rendimiento de TensorFold ni es comparable con Nemotron. Nemotron permanece como candidato de investigación; no descargar ni declarar viabilidad local solo por su NVFP4 o por los 3B activos.

**Conclusión para el inventario:** Qwen3.5-35B-A3B es el más pesado; ambos tienen 3B activos. Qwen presenta mejores puntuaciones publicadas en varios benchmarks generales citados, pero la superioridad global no está demostrada en una evaluación común. Nemotron merece una prueba independiente si se habilita una ruta compatible con el hardware y el runtime.

**Fuentes primarias:** [Qwen3.5-35B-A3B — model card y benchmarks](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) · [Nemotron 3.5 Lightning — NVIDIA model card y benchmarks](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) · [Nemotron 3.5 Lightning — especificaciones técnicas de NVIDIA NeMo](https://github.com/NVIDIA-NeMo/Nemotron/blob/main/docs/nemotron/lightning35/README.md) · [Informe NVIDIA Nemotron 3.5 Super y Lightning](https://research.nvidia.com/labs/nemotron/Nemotron-3.5-Super-and-Lightning/).

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
- [Project Maya v1.1.31 — release upstream](https://github.com/mw00/project-maya/releases/tag/v1.1.31)
- [Project Maya — PR de integración, catálogo y snapshots (#142)](https://github.com/robertosantosx2/LEONES/pull/142)
- [TwIL-8B Q4_K_M — RTX 3050](../TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md)
- [Qwen3.5-9B / RTX 3050 — español](../QWEN3.5-9B-RTX3050-2026-11-11.md)
- [Qwen3.5-9B / RTX 3050 — English](../QWEN3.5-9B-RTX3050-2026-11-11-EN.md)
- [Spark-X2.6-4B abliterated — RTX 3050](spark-x26-4b-abliterated-rtx3050-2026-10-30.md)
- [Clover-35B-A3B-Preview — ficha experimental y arquitectura](../../research/clover-35b-a3b-preview-experimental-2026-10.md)
- [Clover-35B-A3B-Preview — repositorio GGUF IQ2_S probado](https://huggingface.co/na0x2c6/Clover-35B-A3B-Preview-GGUF)
- [Magnitude + Qwen3.5-4B — prueba de catálogo](magnitude-qwen35-4b-2026-10-21.md)\n- [ThumbLLM Qwen3.5-4B — guía de auditoría y reproducción Ubuntu](../../experimental/ThumbLLM-thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0/docs/UBUNTU-REPRODUCTION.md)\n- [ThumbLLM upstream — release Qwen3.5-4B CPU Windows](https://github.com/TeksEdge/ThumbLLM/releases/tag/thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0)
- [Ling-3.0-Tiny — MSI RTX 3050](../reports/ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md)
- [Ling-3.0-Tiny — GB-BXi7-5500](../reports/ling-3.0-tiny-ubuntu-gb-bxi7-5500-2026-10-29.md)
- [Pithos LFM3-1.7B — campaña 06-11](../PITHOS-LFM3-1.7B-RTX3050-2026-11-06.md)
- [Pithos LFM3-1.7B — campaña 07-11](../PITHOS-LFM3-1.7B-RTX3050-2026-11-07.md)\n- [LFM3-1.7B — benchmark llama.cpp CUDA RTX 3050 (PR #125)](../reports/lfm3-1.7b-rtx3050-cuda-20261028.md)\n- [PR #125 — evidencias LFM3-1.7B CUDA](https://github.com/robertosantosx2/LEONES/pull/125)

### REDIL — malla distribuida y referencia Mesh-LLM

- [Mesh-LLM — repositorio upstream, referencia principal de REDIL](https://github.com/Mesh-LLM/mesh-llm)
- [README de REDIL con Mesh-LLM establecido como base de referencia](https://github.com/robertosantosx2/LEONES/blob/docs/redil-mesh-llm-primary-foundation/docs/subprojects/REDIL-IA-distribuida/README.md)
- [Figura de arquitectura general de REDIL (SVG)](https://github.com/robertosantosx2/LEONES/blob/docs/redil-mesh-llm-primary-foundation/docs/subprojects/REDIL-IA-distribuida/REDIL_Arquitectura_General.svg)
- [PR #131 — referencia principal Mesh-LLM y actualización de figuras](https://github.com/robertosantosx2/LEONES/pull/131)
- [Distributed Llama — backend externo opcional](https://github.com/b4rtaz/distributed-llama)

**Clasificación en el inventario:** Mesh-LLM se registra como referencia arquitectónica principal del subsistema REDIL, no como motor probado. REDIL propone federar/orquestar servicios especializados entre nodos; Distributed Llama queda diferenciado como backend opcional para repartir una misma inferencia entre root y workers. No se ha acreditado instalación, integración ni validación física de Mesh-LLM o Distributed Llama en el MSI. La figura SVG es conceptual: los nodos, GPUs y motores rotulados son ejemplos de topología, no resultados de compatibilidad. La documentación de esta actualización se encuentra en la PR #131 y aún no está fusionada en main.
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
- Ejecutar y archivar la reproducción Ubuntu de ThumbLLM/Ornith 1.5 9B: log de descarga y SHA-256, commit/flags de compilación, versión resultante de llama.cpp, configuración efectiva, log de carga/inferencia y métricas PP/TG; solo entonces promoverla a ejecución medida.- Mantener Colibri como auditoría/compilación hasta disponer de inferencia reproducible.
- Incorporar futuras pruebas como campañas fechadas, sin sobrescribir resultados históricos.

---
**Nota de precisión:** este inventario combina informes versionados de LEONES con resultados de laboratorio comunicados durante las sesiones. Los registros que todavía no tienen artefacto bruto versionado quedan identificados como pendientes de archivo; no se presentan como evidencia independiente auditada.