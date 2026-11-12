# Inventario maestro de modelos, motores y pruebas locales

**Última consolidación:** 2026-11-12 (incorporada evaluación DSpine en llama.cpp y verificación CI del drafter Qwen3.8-27B)
**Repositorio:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Equipo principal de referencia:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB · Ubuntu · driver 580.178.04 · CUDA 13.0.

Este documento es el índice único de modelos que se han investigado, descargado, ejecutado, medido o intentado ejecutar con distintos motores. Enlaza a los informes y artefactos originales; no los sustituye ni convierte pruebas distintas en un ranking.

> **Criterio:** “Ejecutado” significa inferencia local funcional; “medido” significa que existe una métrica capturada. Una descarga, compilación, prueba de catálogo o estimación de memoria no acredita inferencia. Las métricas no comparables se mantienen separadas y los datos ausentes se indican como N/D.

## 1. Resumen por motor

| Motor / proyecto | Estado en el laboratorio | Modelos o familias vinculados | Validación y notas |
|---|---|---|---|
| **llama.cpp CUDA** | Ejecutado y medido | Qwen3.5-4B, Qwen3-30B-A3B, **Clover-35B-A3B-Preview IQ2_S**, LFM3-1.7B, Ling-3.0-Tiny, Spark-X2.6-4B, TwIL-8B | LFM3 incorporado en v0.8.0 (PR #31252/#31257); el build histórico b11740 es anterior. Incluye sweep `llama-bench` de Qwen3-30B-A3B IQ3_XXS con `ngl=0/1/8` (3 repeticiones por ajuste); `ngl=1` obtuvo la mejor mediana PP128. Binarios locales en ~/lla| **TensorFold CUDA** | Ejecutado y medido; PR #1879 validado en GPU; integración TensorFold Web en validación | Qwen3.5-2B, Qwen3.5-4B; estudios de Qwen3.5-9B y Qwen3.5-35B-A3B; intento LFM3-1.7B | Inferencia real con 2B y 4B. El parche de scratch diferido se compiló y probó en `sm_86`; Qwen3.5-4B MLX-4bit cargó y generó en RTX 3050 4 GiB (≈56 tok/s), mientras el binario `main` de comparación rechazó el arranque por presupuesto CUDA insuficiente con la misma configuración. Qwen3.5-2B MLX-4bit también se ejecutó (≈112–116 tok/s). La validación se hizo con el árbol candidato basado en PR #1879 y TensorFold Native 1.2.6; **no significa que el parche esté ya integrado en una release**. TensorFold 1.2.7 se publicó el 11-11-2026, pero a la comprobación del 12-11 no constaba la incorporación del commit del PR #1879 y el PR seguía abierto. LFM3-1.7B GGUF Q4_K_M no fue reconocido en 1.1.6. La integración TensorFold Web se verificó separadamente con 1.2.0; su bridge/UI no acredita por sí sola una nueva inferencia. Los estudios 9B/35B no acreditan ejecución en el MSI. |9B/35B no acreditan ejecución en el MSI. |
| **llama.cpp CUDA — Ripple/Ricursive** | Port upstream en revisión; no compilado localmente | Ripple-65B-Preview (Ricursive) | PR #31715 sustituye #31692; soporte de arquitectura y conversor GGUF propuestos. No confundir soporte de código en PR con ejecución local. No hay benchmark LEONES ni prueba en el MSI. |
| **TensorFold CUDA — Ripple** | No soportado por el binario local 1.2.0; implementación upstream experimental Metal | Ripple-65B-Preview / NVFP4 / DFlash2 | `capabilities --json` del binario local no declara familia `ricursive`/`ripple`. PR #2231 añade Ripple para Metal; PR #2260 añade DFlash2 sobre Metal. No hay ruta CUDA validada. No descargar ni intentar cargar en el MSI. |
| **RustingStrata CUDA** | Ejecutado y medido en otros modelos; compatibilidad Qwen3.6-35B-A3B evaluada documentalmente, prueba MSI pendiente | Qwen3.5-4B, Qwen3-30B-A3B; **Qwen3.6-35B-A3B UD-Q2_K_XL (candidato, no ejecutado localmente)** | Motor Rust v1.2.1 con CUDA NVRTC y offload híbrido de expertos CPU/GPU; admite arquitectura Ampere sm_80+. La RTX 3050 sm_86 cumple el umbral arquitectónico, pero no figura entre las GPU probadas para este modelo. Referencia Qwen3.6 publicada en RTX 3060 12 GiB + 32 GiB RAM; no extrapolar sus velocidades al MSI. Ver §3.6. |
| **Tandem / llama.cpp CPU-MoE** | Ejecutado y medido | Qwen3.5-35B-A3B IQ2_XXS | Ensayo CPU-MoE con RTX 3050; decode 35,6 tok/s en la prueba no-thinking registrada. Evidencia bruta pendiente de consolidación completa en LEONES. |
| **Pithos 0.5.1 / 0.6.1** | Ejecutado y medido; Pandora Web documentada, instalación web 0.6.1 pendiente | LFM3-1.7B; LFM2.5-8B-A1B Q4_K_M y Q4_0 | Campañas 0.5.1 del 6–7 de noviembre y validación 0.6.1 del 9–10 de noviembre. En 0.6.1 se midieron CPU, OpenCL y Vulkan en RTX 3050; OpenCL requiere `TMPDIR` fuera de `/tmp` por `EDQUOT`. Benchmark 512/128: Q4_K_M OpenCL caliente PP/TG 292,39/72,54 tok/s; Vulkan 36,50/30,65. Pandora está integrada según el proyecto, pero el arranque web de 0.6.1 aún no ha sido confirmado en este equipo. Ver informe y CSV enlazados en §4. |
| **Kinetic** | Compilado / pruebas de ejecución en curso | LFM3-1.7B GGUF; Qwen3.5-35B-A3B IQ2_XXS seleccionado para prueba | Se inspeccionaron versiones, binarios y catálogo; se prepararon y ejecutaron pruebas. No publicar velocidad sin log de benchmark completo y reproducible. |
| **Colibri — Qwen3.6 CUDA** | Desarrollo en fork; PR draft abierto; pruebas y validación MSI pendientes | Qwen3.6 CUDA: presupuesto de expertos, colocación automática de cadena y ciclo de vida de setup | Rama [`research/qwen36-cuda-chain-planner`](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner), PR draft [#1](https://github.com/robertosantosx2/colibri/pull/1). Incluye clamp del presupuesto `CUDA_EXPERT_GB` respetando headroom de 1 GiB, reserva y trunk; admisión all-or-nothing de tensores de cadena (GPU si caben todos, CPU si no); limpieza de setup parcial y registro temprano de `cc_shutdown`; regresiones fake-CUDA añadidas. **No se han compilado ni ejecutado estas pruebas**, no hay CI acreditada ni validación CUDA/sm_86 en el MSI. No hay inferencia ni métricas de rendimiento. El PR upstream contra `JustVugg/colibri` no pudo abrirse por permisos del conector; el PR #1 existe solo en el fork. Ver §3.8 y el [runbook MSI](https://github.com/robertosantosx2/LEONES/blob/main/docs/subprojects/Colibri/research/msi-qwen36-cuda-validation-runbook-2026-11-10.md). |
| **YASAKANI** | Evaluación solicitada para el MSI; identificación del repositorio y prueba física pendientes | Proyecto YASAKANI; modelo, runtime/backend y requisitos aún por determinar | A 12-11-2026 no hay en esta campaña una ubicación local/repo confirmado, versión, instalación, compilación ni inferencia verificable. No asignar compatibilidad CUDA ni estimar rendimiento antes de auditar los requisitos. Plataforma de referencia para la futura prueba: MSI Thin 15 B12UC, Intel Core i7-12650H, 14 GiB RAM, RTX 3050 Laptop 4 GiB (sm_86), Ubuntu, driver 580.178.04 y CUDA Toolkit 13.4.92 (runtime NVIDIA 13.0). Mantener como investigación pendiente; no contabilizar como motor ejecutado o medido. |
| **ThumbLLM (TeksEdge)** | Receta Windows auditada; reproducción Linux documentada, aún no ejecutada | Qwen3.5-4B GGUF Q4_K_M | Runtime fijado a llama.cpp build 10603 / commit `c060ca974`; receta CPU-only. La release configura `SPEC_TYPE=none`: MTP especulativo desactivado. La aplicación publicada es Windows x64, no un binario Linux. Guía Ubuntu en [LEONES](../../experimental/ThumbLLM-thumbllm-qwen3.5-4b-mtp-q4_k_m-cpu-win-x64-v0.1.0/docs/UBUNTU-REPRODUCTION.md). |\n| **diffuse-cpp** | Investigado documentalmente; no instalado ni ejecutado | LLaDA-8B-Instruct, Dream-v0-Instruct-7B | Motor C++ basado en GGML para dLLM; publica cuantización Q4_K_M y optimizaciones de caché/planificación. Sus cifras upstream proceden de AMD EPYC 4465P de 12 núcleos, no del CPU Intel de referencia. Sin validación local. [Repositorio](https://github.com/iafiscal1212/diffuse-cpp). |\n| **Magnitude 0.2.15** | Instalado y servicio operativo; catálogo consultado | MiniCPM5 1B (Q4); antecedente Qwen3.5-4B en 0.2.10 | `magnitude status`: Runtime Ready, Owner Server, versión 0.2.15, `0.0.0.0:10100`; HTTP local 200. Catálogo: un modelo compatible (MiniCPM5 1B Q4). No hay modelo activo ni inferencia medida. La escucha en todas las interfaces exige clave API. La prueba histórica 0.2.10 con Qwen3.5-4B sigue documentada como ID no reconocido; no confundir ambas campañas. |
| **LocalAI / Parakeet.cpp** | Investigación documental; benchmark local pendiente | LocalAI como proveedor experimental; Parakeet.cpp (ASR) y backends de audio asociados | Estudio arquitectónico incorporado el 12-11-2026. No instalado ni ejecutado en el MSI; no hay mediciones locales de precisión, RTF, latencia, RAM o VRAM. Propuesta: LocalAI opcional detrás de ODS; comparar wrapper LocalAI con Parakeet.cpp directo antes de decidir adopción. Ver §3.4. |\n| **Ollama** | Incluido en matriz de runtimes; no instalado en el MSI según inventario previo | Sin ejecución local validada | No contabilizar como motor probado en este equipo. |
| **MiniCPM5-2B Q4_K_M / llama.cpp CUDA** | Ejecutado y medido en el MSI; evaluación DSpark cerrada sin instalación | MiniCPM5-2B Q4_K_M; borrador MiniCPM5-2B-DSpark evaluado documentalmente | RTX 3050 Laptop 4 GiB, sm_86. CPU: 54,3/21,5 tok/s (prefill/generación); CUDA ctx 512: 755,3/86,5; CUDA ctx 2048: 817,40/85,50. Offload 43/43 capas; KV CUDA 84 MiB. SGLang + DSpark BF16 no viable por memoria y sin receta validada para esta GPU; GPTQ + DSpark no documentado. Auditoría local: Python 3.14.4, PyTorch/SGLang/Triton/FlashInfer ausentes. Ver informe fechado 11-11-2026 en §4. |\n| **Phi-4-mini-instruct / llama.cpp CUDA** | Candidato priorizado; descarga e inferencia local pendientes | Phi-4-mini-instruct 3.8B GGUF Q4_K_M (2,49 GB) | Modelo denso de Microsoft; GGUF comunitario de Unsloth documenta uso con llama.cpp. Adecuado como candidato de prueba, no como ejecución acreditada. En MSI comenzar con contexto 2048 y offload GPU conservador; el contexto anunciado de 128K no es objetivo práctico para 4 GiB VRAM. Ver §3.7. |
| **Infernix** | Investigación documental; no compilado ni ejecutado | Qwen3.8-Flash-Next, Qwen3.8-27B, Qwen3.6, Qwen3.5-122B-A10B | Motor C++/CUDA orientado a RTX 50/Blackwell; el README exige RTX 50-series para otros equipos. Sin soporte sm_86 documentado ni modelo pequeño confirmado. No viable para el MSI actual; ver §3.5. |
| **Transformers, vLLM, SGLang, KTransformers, Mistral.rs, DynaLM** | Evaluación de soporte / planificación; sin prueba local de TwIL-8B | TwIL-8B Granite GGUF Q4_K_M como caso de compatibilidad pendiente | No hay inferencia ni benchmark de TwIL-8B acreditados con estos motores. vLLM se considera una ruta a investigar con pesos compatibles/Safetensors, no una garantía de carga directa de este GGUF. DynaLM queda como candidato documental citado en la conversación, con soporte Granite/GGUF/CUDA aún no verificado independientemente. |
| **ThumbLLM / llama.cpp CPU (Ornith 1.5)** | Paquete Release 1 incorporado a LEONES; reproducción Linux preparada, pendiente de ejecutar | Ornith-1.5-9B-OBLITERATED Q4_K_M | El release original está orientado a Windows. Se añadieron receta y scripts Ubuntu para compilar llama.cpp b10603 (c060ca974) en CPU y servir en puerto 18088. Descarga, hash, compilación e inferencia en el MSI aún no verificados; no contabilizar como motor/modelo ejecutado. |
| **Project Maya** | Investigación documental ampliada; integración en LEONES deshabilitada / no ejecutada | GLM-5.3 (744B), GLM-5.3-Flash (321B), DeepSeek-V4.1-Flash-1017 (748B), MiniMax-M3.1-Flash (428B), Qwen-3.8-Flash-Next / CYBER-FROST | Motor especializado MoE con engines y packs por familia; GGUF/EXL3 según modelo, API OpenAI/Anthropic y UI web. Documentación upstream revisada el 12-11-2026. En el MSI no hay modelo ejecutable soportado: Maya exige al menos 32 GB de RAM física y NVMe; el equipo tiene 14 GiB RAM + 4 GiB VRAM (18 GiB combinados). Qwen UD-IQ2_XS es el candidato menos exigente (47 GB para el modelo residente; 64 GB VRAM+RAM recomendados), pero sigue por debajo del mínimo de RAM física. Sin descarga, instalación, inferencia ni benchmark local. Ver §3.7 y PR #142. |\n| **Uzu** | Evaluación documental cerrada; `RESEARCH_ONLY / NOT VERIFIED` | Qwen3.5-4B, Qwen3.5 MoE (compatibilidad investigada, no validada) | Integrado en `Experimental` mediante PR #119. No se compila, instala ni ejecuta en el MSI dentro del alcance acordado. Sin soporte Ubuntu/CUDA, GGUF ni Qwen MoE demostrado; no contabilizar como motor probado. Ver [evaluación Uzu](../../experimental/uzu/README.md). |
| **Mesh-LLM / REDIL** | Referencia arquitectónica documental; no ejecutado | Mesh-LLM como referencia principal de REDIL; Distributed Llama como backend opcional experimental | No es un motor validado en el MSI ni un benchmark. REDIL sigue en estado de propuesta/investigación, sin despliegue físico. La actualización documental está en PR #131. |
| **Mage-VL-Cowork (Microsoft Mage)** | Investigación documental; no instalado ni ejecutado en el MSI | Agente CUA multimodal 4B; GUI + código/terminal | 66,0% OSWorld-Verified (361 tareas, 50 pasos; media de dos ejecuciones publicada por el equipo); no es un resultado de Artificial Analysis ni un benchmark LEONES. Sin inferencia local ni compatibilidad Ubuntu/GGUF verificada. |
| **MLX** | Formato/artefacto usado por TensorFold | Qwen3.5-2B/4B MLX-4bit | No implica ejecución nativa de MLX en Ubuntu; TensorFold cargó artefactos MLX mediante backend CUDA. |
| **Open-dLLM / Transformers CUDA** | Ejecutado y medido | Open-dCoder-0.5B BF16 | Inferencia local con `model.diffusion_generate` en RTX 3050; campañas V1/V2 single-sequence y V3 batch real. Máximo V3: 198,22 posiciones/s agregadas (batch 4, 16 pasos). | Modelo de difusión; posiciones/s no son directamente comparables con tokens/s autoregresivos. Validación funcional limitada a una tarea factorial. Ver §3.3. |

### Kairos — candidato a base de LEONES AI OS (evaluación documental, 12-11-2026)

**Clasificación:** plataforma de sistema operativo y ciclo de vida de nodos; **no es un motor de inferencia ni un modelo**. No se incluye en rankings de velocidad, prefill, decode o inteligencia. Esta evaluación es documental: Kairos no está instalado, compilado ni validado en el MSI de referencia. No hay todavía imagen LEONES, prueba de arranque, medición de consumo ni validación GPU.

**Hipótesis de arquitectura:** utilizar Kairos como base inmutable y reproducible de una futura edición **LEONES AI OS**, manteniendo LEONES como capa de gestión de IA:
- **Kairos:** sistema base, imagen de arranque, instalación, configuración declarativa, particiones de estado/persistencia, actualizaciones atómicas A/B y recuperación.
- **Capa hardware:** kernel, firmware y driver NVIDIA; compatibilidad CUDA y acceso a GPU desde los servicios.
- **Runtime de cargas:** contenedores y servicios locales; Kubernetes/K3s opcional para nodos/cluster, sin imponerlo al perfil Desktop.
- **LEONES:** catálogo y ciclo de vida de modelos/motores, enrutamiento, APIs, agentes, observabilidad y experiencia de usuario.
- **REDIL / ODS:** posibles capas superiores para coordinación distribuida y orquestación, sujetas a validación independiente.

**Ventajas documentadas:**
- Kairos se define como una metadistribución Linux inmutable y modular, construida sobre distribuciones base como Ubuntu o Alpine; permite generar imágenes de sistema y personalizar componentes.
- El sistema operativo se distribuye como imagen OCI con kernel e initramfs incluidos. Las actualizaciones emplean slots A/B, imagen de transición, evaluación de arranque y mecanismos de fallback/recuperación.
- La configuración declarativa mediante cloud-init/cloud-config permite definir instalación y etapas del ciclo de vida. Los datos persistentes se separan del sistema base; pueden añadirse rutas persistentes mediante configuración de bind mounts.
- K3s/K0s y los componentes de clustering son opciones del stack, no una razón para imponer Kubernetes a una estación de trabajo individual.

**Riesgos y cuestiones no demostradas para LEONES:**
1. **NVIDIA/CUDA:** no se ha demostrado que una imagen Kairos concreta soporte el driver 580.178.04, CUDA 13.0, la RTX 3050 Laptop (sm_86) ni la gestión de módulos NVIDIA tras cambios de kernel. Hay que fijar y validar kernel, driver, firmware e initramfs.
2. **Motores:** no se ha probado llama.cpp CUDA, TensorFold 1.2.x, LocalAI, Parakeet ni RustingStrata dentro de Kairos. La compatibilidad de esos motores con Ubuntu no se transfiere automáticamente.
3. **Persistencia:** pesos y cachés deben residir fuera de la imagen A/B. Un rollback del sistema no garantiza por sí solo la reversión ni la integridad de los datos persistentes; hacen falta política de versiones, espacio, copias y compatibilidad de esquemas.
4. **Perfil Desktop:** validar instalación, arranque, suspensión/reanudación, red, audio, Wi-Fi, gráficos híbridos y consumo de RAM/CPU antes de considerarlo sustituto de Ubuntu en un portátil.
5. **Complejidad operativa:** medir el coste de construir y mantener imágenes, actualizaciones y recuperación frente a Ubuntu convencional.

**Plan de validación propuesto (sin ejecución acreditada):**
- P0: seleccionar versión/base Kairos y construir una imagen de laboratorio reproducible x86-64; documentar kernel, initramfs, bootloader y particiones.
- P1: probar arranque e instalación en VM y después en hardware no crítico; verificar persistencia, actualización A/B, rollback y recuperación.
- P2: validar RTX 3050, driver y CUDA con pruebas de detección, compilación y carga CUDA; conservar logs y versiones exactas.
- P3: desplegar llama.cpp CUDA y TensorFold como cargas independientes; medir memoria host/VRAM, prefill, decode, latencia y estabilidad con protocolos comparables a los de LEONES.
- P4: evaluar LocalAI y Parakeet como servicios de audio/API; no asumir que compatibilidad documental equivale a ejecución.
- P5: solo después, preparar perfiles **LEONES Desktop** y **LEONES Cluster**, con K3s opcional en Desktop y habilitado en Cluster si los resultados lo justifican.

**Criterio de decisión:** Kairos pasa de candidato documental a base validada únicamente cuando exista una imagen reproducible que arranque en el hardware objetivo, conserve los datos de modelos durante actualización/rollback y ejecute al menos una inferencia CUDA real con logs versionados. Hasta entonces, Ubuntu sigue siendo el entorno de desarrollo y benchmark de referencia del MSI.

**Fuentes primarias:**
- [Kairos — arquitectura inmutable](https://kairos.io/docs/architecture/immutable/)
- [Kairos — metadistribución y componentes](https://kairos.io/docs/architecture/meta/)
- [Kairos — imágenes basadas en contenedores y actualizaciones A/B](https://kairos.io/docs/architecture/container/)
- [Kairos — cloud-init y configuración declarativa](https://kairos.io/docs/architecture/cloud-init/)
- [Kairos — repositorio oficial](https://github.com/kairos-io/kairos)

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

## 1.2 Pithos 0.6.1 — LFM2.5-8B-A1B en RTX 3050 (9–10-11-2026)

**Equipo:** MSI Thin 15 B12UC · Intel Core i7-12650H · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB · Ubuntu · NVIDIA driver 580.178.04 · CUDA runtime 13.0.  
**Motor:** Pithos 0.6.1 Linux x86-64 · modelo principal `LFM2.5-8B-A1B-Q4_K_M.gguf`; contraste Q4_0.  
**Controladores evaluados:** CPU, OpenCL NVIDIA (dispositivo 1) y Vulkan NVIDIA (dispositivo 1). Velocidades en tokens/s; prefill = procesamiento del prompt y TG/inferencia = generación.

### Incidencia de OpenCL y solución

La inicialización OpenCL fallaba porque NVVM intentaba crear `/tmp/dep-*.d` y el sistema devolvía `EDQUOT` (cuota de usuario excedida). No era falta de espacio en el SSD. El `/tmp` de esta sesión era tmpfs con cuotas. Se validó el workaround local:
```bash
mkdir -p "$HOME/.cache/pithos-tmp"
TMPDIR="$HOME/.cache/pithos-tmp" ./pithos ...
```

Con ese `TMPDIR`, OpenCL inicializó, asignó expertos a la RTX 3050 y completó inferencia. No se modificaron globalmente cuotas ni permisos de `/tmp`.

### Resultados Q4_K_M — generación corta

Mismo prompt, contexto 512, 8 threads, batch 32, reasoning desactivado, seed 42 y 64 tokens de generación; tres repeticiones por backend.

| Controlador / dispositivo | Prefill medio (tok/s) | Inferencia media (tok/s) | Repeticiones prefill | Repeticiones inferencia |
|---|---:|---:|---|---|
| CPU · Intel Core i7-12650H | 4,63 | 4,79 | 5,0 · 4,7 · 4,2 | 5,36 · 4,51 · 4,50 |
| OpenCL · NVIDIA RTX 3050 | 4,20 | 13,77 | 3,7 · 4,0 · 4,9 | 10,24 · 15,00 · 16,07 |
| Vulkan · NVIDIA RTX 3050 | 5,87 | 9,10 | 5,7 · 4,5 · 7,4 | 12,11 · 7,51 · 7,68 |

Estas pruebas cortas no deben mezclarse con el benchmark 512/128.

### Benchmark Q4_K_M `--bench 512,128`

Misma sesión, modelo y RTX 3050; una ejecución por backend y estado de caché. OpenCL usó 284 slots de expertos (≈1,89 GB; 40% de expertos) y ≈0,55 GB de capas densas. Vulkan descargó 67 matrices (≈471 MB) y ejecutó los expertos en CPU; por tanto, no representa el mismo reparto de trabajo.

| Controlador / GPU | Estado | Prefill PP512 (tok/s) | Inferencia TG128 (tok/s) | Working set |
|---|---|---:|---:|---:|
| OpenCL · NVIDIA RTX 3050 | Primera pasada | 102,33 | 46,66 | 2,59 / 2,72 GB |
| OpenCL · NVIDIA RTX 3050 | Caliente | **292,39** | **72,54** | 2,62 / 2,79 GB |
| Vulkan · NVIDIA RTX 3050 | Primera pasada | 40,90 | 27,13 | 3,38 / 3,34 GB |
| Vulkan · NVIDIA RTX 3050 | Caliente | 36,50 | 30,65 | 3,30 / 3,30 GB |

En la pasada caliente, OpenCL fue ≈8,01× más rápido en prefill y ≈2,37× en generación que Vulkan. Es una comparación de una sola ejecución por condición, no una estimación estadística. El perfil confirma ejecución GPU de expertos MoE en OpenCL (≈53 expertos/token en generación caliente); Vulkan mantuvo el cómputo de expertos en CPU. Los page faults son contadores reportados por Pithos y no deben interpretarse como bytes leídos directamente del SSD.

### Contraste Q4_0 y pruebas breves posteriores

| Modelo / prueba | Controlador y dispositivo efectivo | Prefill (tok/s) | Inferencia (tok/s) | Nota |
|---|---|---:|---:|---|
| Q4_0 · generación corta | CPU · Intel Core i7-12650H | 2,50 | 8,21 | CPU |
| Q4_0 · generación corta | OpenCL solicitado · fallback CPU | 6,90 | 7,82 | Formatos de expertos no soportados; cero expertos GPU |
| Q4_0 · generación corta | Vulkan · NVIDIA RTX 3050 | 8,70 | 33,42 | 1 matriz / ≈219 MB en GPU; matmuls |
| Q4_K_M · smoke test, 8 tokens | OpenCL · NVIDIA RTX 3050 | 3,50 | 1,33 | Prompt 11 tokens; comprobación corta, no benchmark |
| Q4_K_M · generación 16 tokens | OpenCL · NVIDIA RTX 3050 | 4,20 | 5,51 | Prompt 22 tokens; 1.465 ejecuciones de expertos GPU |

Las pruebas Q4_0 no son comparables directamente con Q4_K_M. Tampoco deben compararse directamente smoke test y generación de 16 tokens con la campaña de 64 tokens o el benchmark 512/128.

### Fallo inducido y recuperación

Con `PITHOS_CL_FAIL=3`, el motor detectó el error OpenCL, desactivó el uso posterior de GPU e informó que intentaría continuar en CPU; sin embargo, perdió el contexto, detuvo la respuesta y terminó con código 1. **No se acredita recuperación funcional CPU desde una sesión OpenCL fallida.** La ejecución interactiva CPU independiente sí funcionó (254 tokens; ≈5,09 tok/s), pero no demuestra handoff desde OpenCL.

### Pandora / interfaz web

Pithos documenta Pandora como interfaz web integrada y el modo servidor mediante `--server`, con apertura del navegador mediante `--open`; la receta propuesta para este entorno es usar el modelo Q4_K_M, OpenCL dispositivo 1 y `TMPDIR="$HOME/.cache/pithos-tmp"`, escuchando inicialmente solo en `127.0.0.1:8080`. **Estado: pendiente de ejecución y verificación por el usuario.** No afirmar todavía que Pandora 0.6.1 esté instalada, que el servidor esté operativo ni que exista un lanzador de escritorio/servicio persistente. No activar `--shell` por defecto, ya que habilita ejecución de comandos.

Comando de referencia, sujeto a validar las opciones exactas de `./pithos --help` de la build instalada:

```bash
cd ~/pithos-0.6.1-validation/pithos-0.6.1-linux-x64
mkdir -p "$HOME/.cache/pithos-tmp"
MODEL="$HOME/Pithos/models/LFM2.5-8B-A1B-Q4_K_M.gguf"
TMPDIR="$HOME/.cache/pithos-tmp" ./pithos \
  --model "$MODEL" --gpu opencl --gpu-device 1 --gpu-mem 2500 \
  --server --open --host 127.0.0.1 --port 8080
```

### Evidencia detallada

- [Informe Pithos 0.6.1 — LFM2.5-8B-A1B y validación OpenCL/Vulkan](https://github.com/robertosantosx2/LEONES/blob/docs/pithos-intel-opencl-validation-20261109/docs/subprojects/Pithos/validation/2026-11-10-pithos-0.6.1-lfm25-8b-a1b-validation.md)
- [CSV benchmark PP512/TG128](https://github.com/robertosantosx2/LEONES/blob/docs/pithos-intel-opencl-validation-20261109/docs/subprojects/Pithos/validation/evidence-2026-11-10-lfm25-8b-a1b/benchmark-512-128-2026-11-10.csv)
- [CSV eventos de validación y fault injection](https://github.com/robertosantosx2/LEONES/blob/docs/pithos-intel-opencl-validation-20261109/docs/subprojects/Pithos/validation/evidence-2026-11-10-lfm25-8b-a1b/followup-validation-events-2026-11-10.csv)
- [CSV mediciones originales](https://github.com/robertosantosx2/LEONES/blob/docs/pithos-intel-opencl-validation-20261109/docs/subprojects/Pithos/validation/evidence-2026-11-10-lfm25-8b-a1b/measurements.csv)
- [Script de reproducción Q4_K_M](https://github.com/robertosantosx2/LEONES/blob/docs/pithos-intel-opencl-validation-20261109/docs/subprojects/Pithos/validation/evidence-2026-11-10-lfm25-8b-a1b/reproduce-q4-k-m.sh)

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
- La ficha GGUF por sí sola no acredita compatibilidad universal. La compatibilidad con llama.cpp queda demostrada para el artefacto/configuración de la prueba registrada; no se da por demostrada para TensorFold, RustingStrata, Magnitude u otros runtimes.- No se ha registrado en este inventario una ejecución Ling-3.0-Tiny con TensorFold. Una eventual integración debe empezar por verificar el soporte de la arquitectura `bailing_hybrid` y del GGUF concreto, en una rama aislada.
- No reutilizar como hechos técnicos estimaciones genéricas de tamaños Q4/Q5/Q8 ni afirmaciones de una topología concreta de expertos/capas sin contrastarlas con los metadatos y el archivo exacto de la variante. El tamaño del fichero cuantizado tampoco equivale a la memoria RAM/VRAM total durante inferencia.

**Clasificación:** modelo ejecutado y medido en el MSI con llama.cpp CUDA (IQ2_M); análisis de portabilidad a otros motores pendiente. No es una nueva campaña ni una nueva medición.

| **Ling-3.0-Tiny** | GGUF Q4_K_M | llama.cpp CPU · GB-BXi7-5500 | PP 41,0 tok/s; generación 15,5 tok/s | Equipo distinto del MSI; mantener separado. |
| **Spark-X2.6-4B-abliterated** | GGUF Q4_K_M | llama.cpp CUDA · RTX 3050 | Prueba funcional: prefill 36,9 tok/s; generación 7,2 tok/s | Ejecución individual; faltan repeticiones y perfil de memoria normalizado. |
| **TwIL-8B** | GGUF Q4_K_M balanced | llama.cpp CUDA · RTX 3050 | Con FA ON + KV Q8_0, medianas de 3 ejecuciones: `ngl=24` prefill **73,30 tok/s**, generación **3,89 tok/s**, total llama.cpp **33,10 s**; `ngl=26` prefill **65,51 tok/s**, generación **5,11 tok/s**, total **25,18 s**. | Inferencia funcional medida. `ngl=26` genera un **31,4 %** más rápido frente a `ngl=24`; `ngl=24` deja 614 MiB libres de VRAM frente a 382 MiB con `ngl=26`. Sin swap en ambas campañas. Arquitectura Granite no declarada por TensorFold Native 1.2.0. Ver detalle reproducible más abajo y el [informe TwIL-8B](../TWIL-8B-Q4_K_M-RTX3050-2026-11-05.md). |
| **Qwen3.5-4B** | MLX-4bit | TensorFold PR #1879 · CUDA sm_86 · RTX 3050 4 GiB | 512 tokens: **55,7–56,3 tok/s**; TTFT 173–186 ms; arranque 2,5 s; asignación de modelo 2,81 GiB; tres generaciones con hash de tokens idéntico (`e076d64ff9db`). Con `main`, la misma configuración no superó la comprobación de presupuesto CUDA; la rama candidata sí cargó y sirvió. | Validación real del parche en GPU, no benchmark A/B de rendimiento: `main` no llegó a generar, por lo que no hay comparación de velocidad. Reserva CUDA 0,5 GiB; contexto 1024; salida 512. Build CUDA 124/124 pasos y suite host 133/133 tests. |
| **Open-dCoder-0.5B** | BF16 · snapshot HF `d0d86d5b99960c05258bb1f8265dd91564dbac67` | Open-dLLM / Transformers + PyTorch CUDA · RTX 3050 4 GiB | V2 batch 1 / 16 pasos: mediana 0,456 s y 140,30 posiciones/s, 3/3 funcionales. V3: batch 1/2/4 × 16/32/64 pasos; mejor throughput 198,22 posiciones/s agregadas en batch 4 / 16 pasos, 1,292 s por batch, 3,10 secuencias/s y 12/12 funcionales; VRAM 1,910 GiB asignada / 2,338 GiB reservada. | Inferencia y medición local acreditadas. Métrica de posiciones de difusión, no tok/s autoregresivos. Una sola tarea factorial; no equivale a evaluación general de inteligencia. V1 conserva cifras de tiempo, pero su validador tenía falsos negativos. Ver §3.3. |

## 2.1 Ripple-65B-Preview (Ricursive) — auditoría de motores y viabilidad (12-11-2026)

**Modelo y escala.** [ricursiveAI/Ripple-65B-Preview](https://huggingface.co/ricursiveAI/Ripple-65B-Preview) es un modelo denso de aproximadamente 65B parámetros, con arquitectura propia de la familia Ricursive y pesos BF16 distribuidos en shards que suman alrededor de 130 GB. La variante experimental [NVFP4](https://huggingface.co/ricursiveAI/Ripple-65B-Preview-NVFP4) se publica con un tamaño total aproximado de 57,2 GB. El tamaño del archivo/pesos no equivale a la memoria total de ejecución: faltan buffers, caché KV, contexto y memoria del runtime.

### Motores investigados

| Motor | Estado verificado | Evidencia / limitación |
|---|---|---|
| **TensorFold 1.2.0 CUDA (MSI)** | **No compatible en el binario local inspeccionado** | El 12-11-2026 se ejecutó `tensorfold-native 1.2.0`; `capabilities --json` informó engine Zig, chip `nvidia-sm86`, backend `cuda`, pero no incluyó familia `ricursive` ni `ripple`. El catálogo incluye otras familias (Qwen, Gemma, Nemotron, GLM, etc.). No es un fallo de instalación: la familia no está declarada por ese binario. |
| **TensorFold upstream — Metal** | **Implementación experimental en PR** | [PR #2231](https://github.com/ashhart/TensorFold/pull/2231) incorpora Ripple para backend Metal; [PR #2260](https://github.com/ashhart/TensorFold/pull/2260) agrega speculative decoding DFlash2 y depende de la implementación Ripple. Las cifras comunicadas por el autor en M5 Ultra son resultados de ese entorno Metal; no son mediciones CUDA ni resultados LEONES. |
| **llama.cpp — Ricursive** | **Port propuesto en upstream; sin validación local LEONES** | [PR #31692](https://github.com/ggml-org/llama.cpp/pull/31692) fue el port inicial; [PR #31715](https://github.com/ggml-org/llama.cpp/pull/31715) lo sustituye. El PR inicial describe conversor/arquitectura Ricursive y pruebas de equivalencia en modelo pequeño/capas iniciales, además de test de arquitectura CPU/CUDA. El PR sustituto advierte que no comprobó compatibilidad con GGUF existentes. No se ha compilado este PR en el MSI ni ejecutado un GGUF Ripple. |
| **Transformers / PyTorch** | Referencia de implementación upstream, no benchmark del MSI | La model card publica arquitectura y checkpoint BF16; no se ha realizado inferencia local ni se ha acreditado rendimiento en el hardware LEONES. |

### Métricas publicadas y estado de las pruebas

- La model card de Ricursive informa de **250 tok/s en 2× NVIDIA B200, batch 8**. Es una cifra del fabricante en hardware de centro de datos y carga concurrente; no es comparable con una conversación individual en una RTX 3050.
- Las mediciones publicadas en las PR de TensorFold corresponden a **M5 Ultra con Metal**. No deben trasladarse a CUDA ni a la GPU NVIDIA del MSI.
- **Métricas LEONES de Ripple: N/D.** No se han descargado pesos, compilado el port, cargado el modelo ni medido prefill, decode, TTFT, RAM o VRAM.
- El repositorio [AtomicChat Ripple GGUF](https://huggingface.co/AtomicChat/Ripple-65B-Preview-GGUF) ofrece cuantizaciones comunitarias. La existencia de un GGUF no garantiza compatibilidad con el PR de llama.cpp ni que todas las variantes sean válidas; comprobar conversor, metadatos y compatibilidad exacta antes de usarlo.

### Viabilidad en el MSI Thin 15 B12UC

El equipo de referencia es Intel Core i7-12650H, **14 GiB de RAM**, NVIDIA RTX 3050 Laptop **4 GiB VRAM**, Ubuntu, driver 580.178.04 y CUDA 13.0. En la captura aportada para esta auditoría, había 9,9 GiB de RAM disponibles y 439 GiB libres en disco.

- BF16 (~130 GB) y NVFP4 (~57,2 GB) superan ampliamente la memoria física disponible. La cuantización comunitaria más pequeña citada en la investigación ronda 18,5 GB de pesos, también por encima de la RAM física.
- El swap de 31 GiB no convierte el modelo en una carga práctica: no sustituye RAM y provocaría paginación extrema.
- Aunque el PR de llama.cpp compile y reconozca la arquitectura, eso solo validaría el código/conversor; no demostraría que el modelo pueda ejecutarse en este MSI.
- **Decisión:** no descargar Ripple ni intentar cargarlo en el MSI. Mantenerlo como investigación de compatibilidad upstream y reservar la ejecución integral para un host con memoria suficiente.

### Próxima validación segura

La siguiente prueba propuesta es clonar llama.cpp en un directorio independiente, traer la rama del [PR #31715](https://github.com/ggml-org/llama.cpp/pull/31715), compilar con `GGML_CUDA=ON` y ejecutar el test de arquitectura `ricursive`. Esta compilación aislada no debe modificar `~/llama.cpp-cuda` ni los servicios locales existentes. Solo después de compilar se evaluará el conversor GGUF con un artefacto pequeño/de prueba; no se descargará el checkpoint de 65B como parte del smoke test.

**Fuentes primarias:** [model card Ripple BF16](https://huggingface.co/ricursiveAI/Ripple-65B-Preview) · [Ripple NVFP4](https://huggingface.co/ricursiveAI/Ripple-65B-Preview-NVFP4) · [llama.cpp PR #31715](https://github.com/ggml-org/llama.cpp/pull/31715) · [TensorFold PR #2231](https://github.com/ashhart/TensorFold/pull/2231) · [TensorFold PR #2260](https://github.com/ashhart/TensorFold/pull/2260).


### TwIL-8B Q4_K_M — comparativa consolidada de offload GPU (12-11-2026)

Se consolidan seis ejecuciones de inferencia con el mismo prompt y los mismos parámetros, tres con 24 capas y tres con 26 capas descargadas a la GPU. Motor: llama.cpp CUDA; modelo `webAI-Official/TwIL-8B`, GGUF Q4_K_M balanced; contexto 1024; batch 128 / ubatch 64; 8 hilos CPU y batch; Flash Attention activado (`-fa on`); cachés K/V Q8_0 (`-ctk q8_0 -ctv q8_0)); 128 tokens de salida; temperatura 0,2 y seed 42.

| Capas GPU (`-ngl`) | Prefill mediano | Generación mediana | Tiempo total llama.cpp mediano | VRAM libre observada | RSS máximo aprox. |
|---:|---:|---:|---:|---:|---:|
| 24 | **73,30 tok/s** | **3,89 tok/s** | **33,10 s** | **614 MiB** | **5,33 GiB** |
| 26 | **65,51 tok/s** | **5,11 tok/s** | **25,18 s** | **382 MiB** | **5,33 GiB** |

**Muestras individuales (prefill / generación / total llama.cpp):**

- `ngl=24`: 57,19 / 4,39 tok/s / 29,64 s; 82,96 / 3,89 tok/s / 33,10 s; 73,30 / 3,85 tok/s / 33,53 s.
- `ngl=26`: 65,51 / 5,31 tok/s / 24,51 s; 64,02 / 4,24 tok/s / 30,55 s; 113,66 / 5,11 tok/s / 25,18 s. El prefill 113,66 tok/s es un valor atípico respecto a las otras dos muestras; la mediana evita que determine la comparación.

**Conclusión limitada al protocolo:** 26 capas ofrecen aproximadamente un **31,4 % más de velocidad de generación** que 24 capas (5,1148 frente a 3,8932 tok/s), con 232 MiB menos de VRAM libre. 24 capas presentan mayor mediana de prefill en estas muestras. Ambas configuraciones terminaron con código 0, sin swap y con 127 grafos reutilizados y cero reasignaciones de grafo en los registros aportados. No interpretar estos resultados como evaluación de calidad: las respuestas se limitaron a 128 tokens y terminaron por límite de generación (`finish_reason=length`), con el contenido principalmente en `reasoning_content`.

Las pruebas anteriores con Flash Attention desactivado y KV F16 se conservan como una campaña distinta; no se mezclan con estas medianas. El informe vinculado contiene la identificación del artefacto y los parámetros de reproducción. El hardware de referencia completo está descrito en la cabecera del inventario y en el perfil Ubuntu del MSI.

### Alternativas a llama.cpp para TwIL-8B — estado de compatibilidad

La arquitectura identificada para TwIL-8B es Granite. El hecho de que un motor admita GGUF o CUDA de forma general **no demuestra** que admita esta arquitectura ni este GGUF concreto.

| Motor | Ruta considerada | Estado LEONES |
|---|---|---|
| **TensorFold Native 1.2.0** | Carga del GGUF Granite | **No compatible según las capacidades observadas en el laboratorio:** el catálogo/capacidades consultados no declaran Granite. No se ha registrado una carga de TwIL-8B. |
| **vLLM** | Preferentemente pesos originales en formato compatible (p. ej., Safetensors), sujeto a soporte de arquitectura y cuantización | **No probado.** No dar por garantizada la carga directa del GGUF Q4_K_M. Los pesos BF16 completos rondan 16 GiB antes de memoria de ejecución, por encima de los 14 GiB de RAM del MSI; la RTX 3050 dispone de 4 GiB. No se ha demostrado una configuración viable en este equipo. |
| **Transformers + PyTorch** | Carga de pesos compatibles o lector GGUF, según arquitectura y ruta de ejecución | **No probado.** La carga GGUF mediante Transformers no equivale a un runtime GGUF optimizado ni acredita aceleración CUDA eficiente. La variante BF16 completa no cabe holgadamente en la memoria física disponible. |
| **DynaLM** | Candidato mencionado para explorar Granite/GGUF | **No verificado.** Antes de instalarlo hay que identificar el repositorio/proyecto exacto y comprobar en su documentación y código el soporte efectivo de Granite, GGUF Q4_K_M y CUDA en Linux. La afirmación previa de compatibilidad se conserva como hipótesis, no como hecho. |

**Decisión:** mantener llama.cpp como único motor con ejecución local de TwIL-8B acreditada en este MSI. Las alternativas anteriores quedan en investigación documental; no se han instalado, ejecutado ni comparado. No modificar servicios ODS/TensorFold ni sustituir el motor validado sin una prueba aislada y reproducible.

## 3. Intentos, estudios e investigación (no contar como benchmark)

### TensorFold CUDA — validación de PR #1879 en RTX 3050 (12-11-2026)

Se realizó una validación de la corrección de asignación diferida de scratch de Qwen3.5 CUDA en el MSI Thin 15 (RTX 3050 Laptop, 4 GiB VRAM, driver 580.178.04, CUDA Toolkit 13.4, Zig 0.17.0). El árbol candidato se compiló para `sm_86` y se ejecutó con los checkpoints MLX-4bit locales. Esta campaña es distinta de la integración TensorFold Web 1.2.0 descrita debajo.

| Modelo | Configuración | Resultado medido | Evidencia / cautela |
|---|---|---|---|
| **Qwen3.5-4B** | MLX-4bit; CUDA; contexto 1024; reserva 0,5 GiB; 512 tokens; no-thinking; sin drafts | **55,7–56,3 tok/s**; TTFT 173–186 ms; startup 2,5 s; asignación 2,81 GiB | Tres generaciones produjeron el mismo prefijo SHA-256 de tokens: `e076d64ff9db`. La rama candidata cargó y sirvió; el binario `main` usado como control rechazó el arranque por presupuesto de memoria CUDA insuficiente con los mismos parámetros. Esto acredita la diferencia de carga observada, no una mejora de velocidad A/B. |
| **Qwen3.5-2B** | MLX-4bit; CUDA; contexto 1024; reserva predeterminada 1 GiB; 512 tokens | **112,2–116,5 tok/s**; TTFT aprox. 76 ms; startup 1,8 s; asignación 1,44 GiB | Dos generaciones produjeron el mismo prefijo SHA-256 de tokens: `ea070ff2b735`. Ejecución funcional en el mismo candidato. |

**Compilación y tests:** build CUDA `124/124` pasos correctos; suite `test-cuda-host` `369/369` pasos y `133/133` tests correctos. Los binarios se construyeron para `sm_86`. SHA-256 del binario candidato: `2fd5337cdc2c801ebfcccdfb429d26d3673efe2b1f6dfdd76f330bb43463436d`.

**Estado upstream separado de la validación local:** [PR #1879](https://github.com/ashhart/TensorFold/pull/1879) contiene la corrección propuesta. En la comprobación del 12-11-2026 seguía abierto y sin merge. [TensorFold v1.2.7](https://github.com/ashhart/TensorFold/releases/tag/v1.2.7), publicada el 11-11-2026, no mencionaba el cambio; la comparación del historial tampoco mostró el commit del PR dentro de la etiqueta. Por tanto, **no registrar el arreglo como incorporado en 1.2.7**. La prueba local acredita el comportamiento del árbol candidato, no el de la release 1.2.7.

**Alcance:** se valida la ruta de carga/generación de estos dos checkpoints y esta configuración de memoria/contexto en la RTX 3050. No se acredita compatibilidad universal de Qwen3.5, todas las longitudes de contexto, múltiples streams, ni rendimiento de modelos 9B/35B con TensorFold. La advertencia `libtfgrammar.so` afecta structured output/required tool calls; no invalida la generación ordinaria ensayada.
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

## 3.3 Open-dCoder-0.5B — dLLM medido localmente en la RTX 3050

**Clasificación:** modelo de difusión de lenguaje (dLLM), ejecutado y medido en Ubuntu con PyTorch/Transformers y la ruta `model.diffusion_generate`. No confundir con un modelo causal autoregresivo ni comparar sus posiciones/s directamente con tok/s de llama.cpp, TensorFold u otros motores autoregresivos.

**Modelo y entorno**
- Modelo: [`fredzzp/open-dcoder-0.5B`](https://huggingface.co/fredzzp/open-dcoder-0.5B), 494.032.768 parámetros, BF16.
- Snapshot Hugging Face: `d0d86d5b99960c05258bb1f8265dd91564dbac67`.
- Equipo: MSI Thin 15 B12UC, Intel Core i7-12650H (16 hilos), 14,8 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB, Ubuntu, driver 580.178.04, CUDA 13.0.
- Software medido: Python 3.12.15, PyTorch 2.11.0+cu128, Transformers 4.54.1, huggingface-hub 0.36.2, psutil 7.2.2.
- Tarea común: generar una función recursiva Python `factorial(n)`, producir `ValueError` para negativos e incluir `print(factorial(5))`. El validador evalúa sintaxis y los dos casos funcionales de factorial; no es un sandbox general ni comprueba por separado el print.
### Evolución de las campañas

| Campaña | Diseño | Resultado principal | Interpretación |
|---|---|---|---|
| **V1** | Secuencia única; 16/32/64/128 pasos; 3 repeticiones | 143,34 / 71,80 / 36,08 / 18,17 posiciones/s; VRAM asignada 1,184 GiB | El extractor/validador inicial produjo falsos negativos (0/3 válidas en todas las configuraciones). Conservar como histórico de rendimiento, no usar sus etiquetas de calidad. |
| **V2** | Secuencia única; validador corregido; warmup excluido; 3 repeticiones | 16 pasos: 0,456 s mediana, 140,30 posiciones/s, 3/3 funcionales, 1,184 GiB VRAM. 32 pasos: 70,66 posiciones/s y 0/3 funcionales. 64: 35,37 posiciones/s y 3/3. 128: 17,86 posiciones/s y 3/3. | Baseline de una secuencia. En esta tarea, 16 pasos fue la opción más rápida entre las que superaron la validación funcional. |
| **V3** | Batch real 1/2/4 × 16/32/64 pasos; 1 warmup y 3 repeticiones por configuración | Nueve configuraciones, 27 batches medidos; mejor resultado: batch 4 / 16 pasos, 198,22 posiciones/s agregadas, 3,10 secuencias/s, 1,292 s por batch, 12/12 funcionales, 1,910 GiB asignados y 2,338 GiB reservados. | El batch aumenta el throughput agregado, no linealmente, a costa de latencia de batch y memoria mayores. No hubo OOM en las nueve configuraciones. |

### Matriz completa V3

| Batch | Pasos | Mediana batch (s) | Secuencias/s | Posiciones/s agregadas | Sintaxis | Funcional | VRAM asignada (GiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 0,460 | 2,17 | 139,15 | 100 % | 100 % | 1,184 |
| 1 | 32 | 0,949 | 1,05 | 67,45 | 100 % | 33,3 % | 1,184 |
| 1 | 64 | 1,811 | 0,55 | 35,33 | 100 % | 100 % | 1,184 |
| 2 | 16 | 0,765 | 2,62 | 167,37 | 100 % | 100 % | 1,427 |
| 2 | 32 | 1,532 | 1,31 | 83,53 | 100 % | 100 % | 1,427 |
| 2 | 64 | 3,064 | 0,65 | 41,78 | 100 % | 100 % | 1,427 |
| 4 | 16 | 1,292 | 3,10 | **198,22** | 100 % | 100 % | 1,910 |
| 4 | 32 | 2,583 | 1,55 | 99,12 | 91,7 % | 66,7 % | 1,910 |
| 4 | 64 | 5,167 | 0,77 | 49,55 | 100 % | 100 % | 1,910 |

En batch 4 / 32 pasos se contrastaron los registros CSV y JSONL locales: 11/12 salidas sintácticas (91,7 %) y 8/12 funcionales (66,7 %). El detalle por repetición fue 3/4 y 3/4; 4/4 y 2/4; 4/4 y 3/4, respectivamente. Se conserva esta auditoría frente a la discrepancia del resumen mostrado en consola.

### Lectura operativa

- **Menor latencia de una petición:** V3 batch 1 / 16 pasos, mediana 0,460 s.
- **Equilibrio batch:** batch 2 / 16 pasos, 0,765 s por batch y 167,37 posiciones/s agregadas.
- **Máximo throughput agregado medido:** batch 4 / 16 pasos, 198,22 posiciones/s.
- 32 pasos no fue estable en calidad funcional para esta tarea; no recomendarlo como configuración por defecto con esta evidencia.
- La comparación V2→V3 en batch 1 / 16 pasos (140,30 frente a 139,15 posiciones/s) difiere aproximadamente -0,8 %, por lo que V3 conserva el baseline single-sequence.
- El warning de Transformers sobre `temperature`/`top_k` se mantuvo. La inspección del código encontró rutas que consumen esos parámetros, pero falta una ablación A/B que confirme su efecto experimental.
- La evidencia cubre una sola tarea factorial. No es un benchmark general de programación ni una puntuación de inteligencia.

### Documentación primaria vinculada

1. [Resumen ejecutivo y mapa V1/V2/V3](../subprojects/Open-dCoder/EXECUTIVE-SUMMARY.md)
2. [README del subproyecto Open-dCoder](../subprojects/Open-dCoder/README.md)
3. [Cuaderno V1/V2: protocolo, validador, resultados y auditoría](../subprojects/Open-dCoder/EXPERIMENT-2026-10-31.md)
4. [Informe V3: batching real, matriz completa y auditoría](../subprojects/Open-dCoder/EXPERIMENT-V3-BATCH-2026-10-31.md)
5. [Repositorio upstream Open-dLLM](https://github.com/zhangsheng93/Open-dLLM)
6. [Checkpoint en Hugging Face](https://huggingface.co/fredzzp/open-dcoder-0.5B)

**Artefactos originales V3 pendientes de incorporación íntegra:** runner `benchmark_opendcoder_v3_batch.py`, CSV `opendcoder_v3_20261031T110532Z.csv`, JSONL `opendcoder_v3_20261031T110532Z_outputs.jsonl`, JSON `opendcoder_v3_20261031T110532Z_summary.json` y `benchmark-v3-console.log`. Sus rutas locales constan en el informe V3; esta ficha no afirma que los ficheros originales estén ya versionados en GitHub.

### 3.4 LocalAI y Parakeet.cpp — evaluación de arquitectura de audio (12-11-2026)

**Clasificación:** investigación documental; no instalado ni ejecutado en el MSI. No contabilizar como benchmark ni como compatibilidad local validada.

**LocalAI** se evalúa como servidor/proveedor opcional de inferencia con API HTTP compatible con OpenAI, especialmente útil para prototipar capacidades de audio y desacoplar motores especializados. No se propone sustituir ODS, Hermes, TensorFold ni el router de LEONES. ODS debe conservar routing, políticas, selección de proveedor y observabilidad; LocalAI quedaría detrás de una interfaz intercambiable.

**Parakeet.cpp** ([repositorio](https://github.com/mudler/parakeet.cpp)) es el candidato prioritario para ASR local: implementación C++ basada en ggml de modelos NVIDIA NeMo Parakeet. La investigación identifica como candidatos una variante compacta TDT/CTC (~110M) para primera prueba y Parakeet TDT v3 (~0.6B) para evaluar calidad y multilingüismo. El soporte exacto depende del checkpoint, formato, versión y pipeline; no asumir que streaming, VAD, diarización, embeddings y clasificación de sonidos están disponibles en todos los modelos o en una sola ruta.

| Componente/capacidad | Uso potencial en LEONES | Estado |
|---|---|---|
| Parakeet.cpp ASR | Transcripción, dictado y audio para Hermes/ODS | Candidato; no probado localmente |
| Timestamps | Subtítulos SRT/VTT y sincronización | Verificar granularidad y API |
| Streaming | Transcripción incremental y voz conversacional | Medir latencia extremo a extremo |
| VAD | Detección de inicio/fin de voz | Validar pipeline |
| Diarización | Separación de hablantes | Validar modelo/pipeline; no equivale a identificar personas |
| Sound-event detection | Alarmas y eventos acústicos | Evaluar backend/modelo específico |
| LocalAI API | Exponer transcripción mediante endpoint de audio | Integración propuesta, no configurada en ODS |
| TTS complementario | Respuesta hablada en LEONES Voice | Revisar proyectos, pesos, calidad y licencias por separado |

**Arquitectura propuesta:** LEONES UI/Voice → ODS Router → proveedor de audio → Parakeet.cpp directo o LocalAI experimental. La aplicación cliente no debería depender de un backend concreto. LocalAI puede acelerar el prototipado; debe compararse con Parakeet.cpp como servicio independiente antes de adoptar un wrapper permanente.

Ejemplo de endpoint documentado por LocalAI (la ruta y el identificador del modelo deben ajustarse a la configuración real desplegada):

```bash
curl http://localhost:8080/v1/audio/transcriptions \
  -F file="@audio.wav" \
  -F model="parakeet-110m"
```

Configuración conceptual, **no existente ni validada en ODS**:

```yaml
audio:
  transcription:
    provider: localai
    base_url: http://local-ai:8080/v1
    model: parakeet-110m
  capabilities:
    timestamps: true
    streaming: experimental
    vad: optional
    diarization: optional
```

**Viabilidad en el equipo de referencia:** MSI Thin 15 B12UC, i7-12650H, 14 GiB RAM y RTX 3050 Laptop de 4 GiB. Hipótesis por verificar: el modelo compacto podría ser un servicio auxiliar; la ruta CPU permitiría evitar competencia de VRAM con TensorFold. No se ha medido footprint, coexistencia, temperatura, RTF ni precisión. No reservar VRAM ni modificar ODS/llama-server por defecto durante la prueba.

**Plan de validación:**
1. Smoke test CPU con Parakeet.cpp; registrar commit, build, modelo, cuantización y hashes.
2. Repetir en CUDA si el backend y la compilación lo permiten.
3. Comparar Parakeet.cpp directo y Parakeet vía LocalAI.
4. Comparar con Whisper.cpp y Moonshine usando el mismo corpus español/inglés.
5. Medir WER/CER, RTF, latencia de primera respuesta, tiempo de carga, RAM/VRAM pico, temperatura, consumo y estabilidad.
6. Probar concurrencia con TensorFold activo y modo CPU alternativo.
7. Si supera criterios, crear proveedor `audio.transcription` para ODS con health check, timeout, cancelación, límites de tamaño/duración y telemetría que no almacene audio ni transcripciones sensibles por defecto.
**Decisión preliminar:** GO para benchmark e integración experimental; NO-GO para dependencia de producción o cambio de arquitectura por defecto hasta validar calidad, rendimiento, footprint, API, mantenimiento y licencias de código/pesos por separado.

**Fuentes primarias:**
- [LocalAI](https://localai.io/) · [Documentación](https://localai.io/docs/) · [Audio to Text](https://localai.io/docs/features/audio-to-text/) · [Repositorio](https://github.com/mudler/LocalAI)
- [Parakeet.cpp](https://github.com/mudler/parakeet.cpp) · [NVIDIA NeMo](https://github.com/NVIDIA/NeMo)
- [Whisper.cpp](https://github.com/ggml-org/whisper.cpp) · [Moonshine](https://github.com/usefulsensors/moonshine)
- [Investigación ampliada LocalAI/Parakeet en LEONES](../../research/localai-parakeet-integration.md)

### 3.5 Infernix — motor CUDA orientado a RTX 50 / Blackwell (12-11-2026)

**Clasificación:** investigación documental; no instalado, compilado ni ejecutado en el MSI. No contabilizar como motor compatible ni como benchmark local.

[Infernix](https://github.com/Wallawalla47/Infernix) es un motor C++/CUDA derivado de NInfer, diseñado para servir modelos Qwen mediante artefactos propios .ninfer y .infernix. El proyecto está enfocado en GPUs NVIDIA Blackwell y el README indica expresamente que otro PC necesita una GPU **RTX serie 50** y driver NVIDIA 580 o posterior. La guía de compilación Linux documenta Ubuntu 24.04, CUDA Toolkit **13.4 o posterior**, CMake 3.28+, Ninja y C++20.

| Modelo / ruta publicada | Requisitos publicados relevantes | Evaluación en MSI RTX 3050 4 GiB (sm_86) |
|---|---|---|
| Qwen3.8-Flash-Next | Ruta Blackwell; documentación de despliegue con RTX 5090 sm_120a, gran memoria de sistema y artefactos auxiliares voluminosos | **No viable**: arquitectura GPU, memoria y requisitos de la ruta exceden el equipo |
| Qwen3.8-27B NVFP4 | Requisito de RTX 50-series; pesos publicados en torno a 20 GB de VRAM | **No viable**: capacidad de VRAM y generación de GPU incompatibles |
| Qwen3.6-27B / 35B-A3B | Catálogo del proyecto orientado a la plataforma RTX 50; no se ha encontrado una ruta compacta sm_86 documentada | **No validado**: no inferir compatibilidad por el nombre Qwen ni por ser MoE |
| Qwen3.5-122B-A10B NVFP4 | Ruta Blackwell/RTX 5090 y memoria muy superior a la disponible | **No viable** |
| Modelo pequeño alternativo | No se ha identificado en el catálogo/documentación consultados un checkpoint pequeño preparado para RTX 3050 | **Sin candidato acreditado** |

**Comparación con el entorno del laboratorio:** MSI Thin 15 B12UC, Intel Core i7-12650H, 14 GiB RAM, RTX 3050 Laptop de 4 GiB (sm_86), driver 580.178.04 y CUDA Toolkit local 13.0. El driver satisface el mínimo 580 citado por el README, pero eso no convierte la GPU Ampere sm_86 en Blackwell ni resuelve los requisitos de memoria. Además, el toolkit instalado (13.0) es inferior al mínimo 13.4 indicado por la guía de compilación. No actualizar el CUDA del sistema ni alterar los runtimes existentes para intentar esta compilación.

**Conclusión técnica:** **NO-GO para instalación/compilación en el MSI en su estado actual.** No hay evidencia de que los kernels o artefactos publicados funcionen en sm_86. Cambiar únicamente la arquitectura de compilación a sm_86 no demuestra portabilidad: habría que auditar los kernels CUDA, instrucciones Tensor Core/PTX, dependencias y formatos de cuantización, y determinar si existe una ruta alternativa para Ampere. Los requisitos RTX 50 del README y las rutas NVFP4/Flash-Next documentadas no deben presentarse como compatibles con RTX 3050.

**Siguiente paso admisible:** auditoría estática del código fuente (CMake, flags de arquitectura, archivos .cu/.cuh, intrinsics, PTX y dependencias) para separar componentes genéricos de kernels Blackwell-only. Si se justifica una prueba posterior, hacerla en un checkout/contendor aislado con CUDA Toolkit 13.4, sin modificar TensorFold, llama.cpp, ODS ni el CUDA del sistema. Solo promover a “compilado” o “ejecutado” tras conservar commit, comando, logs, arquitectura efectiva y prueba de inferencia.

**Fuentes primarias y documentación técnica consultada:**
- [Repositorio Infernix](https://github.com/Wallawalla47/Infernix) · [README y requisitos de compilación](https://github.com/Wallawalla47/Infernix/blob/main/README.md)
- [Guía Qwen3.8-Flash-Next](https://github.com/Wallawalla47/Infernix/blob/main/docs/qwen3_8-flash-next.md)
- [Qwen3.8-27B NVFP4](https://huggingface.co/Wallawalla47)
- [Especificación CUDA de arquitecturas NVIDIA](https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/)

### 3.6 TensorFold como backend nativo de Atomic Chat — propuesta de integración (12-11-2026)

**Clasificación:** investigación de arquitectura y propuesta de feature; no es una integración implementada ni una prueba de Atomic Chat. Se prepara una solicitud para el repositorio [Atomic Chat Core](https://github.com/AtomicBot-ai/atomic-chat-core), tomando como base la evidencia local de TensorFold y el trabajo de integración documentado en LEONES.

**Motivación basada en resultados del laboratorio:** TensorFold ya ha demostrado inferencia CUDA funcional en el MSI Thin 15 B12UC (RTX 3050 Laptop, 4 GiB VRAM) con checkpoints Qwen3.5 MLX-4bit. En las campañas registradas se han observado aproximadamente 112,2–116,5 tok/s con Qwen3.5-2B y 55,7–56,3 tok/s con Qwen3.5-4B, además de TTFT bajo y carga funcional del 4B con la corrección experimental de scratch diferido. Son resultados de configuraciones concretas; no garantizan el mismo rendimiento dentro de Atomic Chat ni demuestran que el arreglo de PR #1879 esté incluido en una release publicada.

**Propuesta técnica:** incorporar TensorFold como proveedor local seleccionable, junto a los backends existentes, mediante un adaptador nativo en `atomic-chat-core`. La primera entrega debería limitarse a Linux x86_64 con NVIDIA CUDA y a una única instancia/modelo gestionado. El objetivo es que Atomic Chat descubra, arranque, supervise, consulte y detenga `tensorfold-native` como proceso local, sin convertir TensorFold en un proveedor remoto OpenAI ni exigir Docker.

| Área | Propuesta | Criterio de implementación |
|---|---|---|
| Registro del proveedor | Añadir `tensorfold` al identificador/lista de proveedores locales y al registro de runtimes | Mantener la selección coherente con el contrato actual de `atomic-chat-core`; no crear un segundo gestor de procesos |
| Proceso y ciclo de vida | Lanzar y supervisar `tensorfold-native` como proceso hijo gestionado | Reutilizar el runtime local, la tabla de sidecars, readiness, cancelación, apagado y limpieza existentes |
| Detección de capacidad | Consultar versión, `capabilities --json` e información del checkpoint | Validar familia, formato y cuantización reales; no inferir compatibilidad solo por el nombre del modelo |
| API local | Integrar descubrimiento de modelos y chat, inicialmente `/v1/models` y `/v1/chat/completions` | Probar respuestas JSON y streaming SSE de extremo a extremo antes de declarar compatibilidad |
| Red y seguridad | Escuchar en loopback, puerto asignado/controlado por el runtime y acceso a través del gateway gestionado | Reutilizar validación de Host, autenticación y allowlist del gateway; no exponer el servidor de inferencia directamente |
| GPU y memoria | Registrar ocupación antes del arranque y liberarla solo tras confirmar la salida del proceso | Separar memoria de pesos, KV cache y scratch/workspace; no terminar procesos GPU ajenos para liberar VRAM |
| Modelos | Empezar con checkpoints locales compatibles y rutas ya disponibles | No añadir descargas de pesos al core ni asumir que TensorFold acepta GGUF genérico |
| Plataforma | Primera fase: Linux x86_64 + NVIDIA CUDA | Dejar Windows, macOS, Docker y otras aceleraciones para fases posteriores |

**Reutilización de arquitectura:** la implementación debe encajar en los mecanismos que ya utiliza Atomic Chat Core para proveedores locales —identificadores, runtime local, supervisión de sidecars, gateway de sesiones y registro/ocupación GPU— en vez de introducir otro subsistema paralelo. Los nombres concretos de módulos y puntos de extensión deben confirmarse contra la versión actual del repositorio durante la implementación.

**Alcance recomendado para una primera versión:**
1. Detección del binario y comprobación de versión/capacidades.
2. Selección de un checkpoint local que TensorFold declare compatible.
3. Arranque supervisado con CUDA, contexto acotado, paralelismo 1 y puerto loopback.
4. Readiness mediante health check y registro del modelo servido.
5. Chat JSON y streaming SSE a través del gateway de Atomic Chat.
6. Cancelación, descarga/parada, cierre de sesión y limpieza de procesos/ocupación GPU.
7. Tests unitarios y de ciclo de vida sin GPU; prueba de aceptación opcional en hardware CUDA con modelo pequeño.

**Límites y riesgos que deben figurar en el diseño:**
- La estimación genérica de memoria que devuelva la herramienta de inspección no equivale al pico real de VRAM. La elegibilidad debe combinar perfil de modelo/configuración, memoria disponible y margen de seguridad.
- La reserva de GPU debe ser transaccional: adquirir antes de arrancar y liberar solo cuando el proceso haya terminado de verdad. Un timeout o una cancelación de petición no demuestra que el proceso haya liberado memoria.
- Atomic Chat no debe matar ni reiniciar procesos CUDA que no haya creado y registrado.
- La compatibilidad debe evaluarse por combinación de versión de TensorFold, familia, formato, cuantización, contexto y backend; no por extensión de archivo ni por etiqueta genérica “Qwen”.
- La compatibilidad de structured output/tool calling, visión, audio, embeddings y múltiples modelos simultáneos queda fuera de la primera fase hasta disponer de pruebas específicas.
- La integración TensorFold Web de LEONES es una experiencia de UI/bridge independiente; no debe presentarse como implementación del proveedor en Atomic Chat.

**Estado de la propuesta:** issue preparado para presentar en [Atomic Chat Core — Issues](https://github.com/AtomicBot-ai/atomic-chat-core/issues), pero no publicado desde esta actualización. La rama de investigación de LEONES [PR #139](https://github.com/robertosantosx2/LEONES/pull/139) conserva el trabajo previo del PoC y sus comprobaciones; no equivale a un merge en Atomic Chat Core.

**Evidencia y documentación relacionada:**
- [Validación CUDA de Qwen3.5-2B/4B y PR #1879 en RTX 3050](../subprojects/TensorFold/CUDA-LAZY-SCRATCH-FIX-PR1879-2026-11-02.md).
- [TensorFold upstream — PR #1879](https://github.com/ashhart/TensorFold/pull/1879) y [release v1.2.7](https://github.com/ashhart/TensorFold/releases/tag/v1.2.7). La release v1.2.7 no debe considerarse prueba de que el cambio de PR #1879 esté incorporado.
- [LEONES PR #139 — investigación de integración TensorFold/Atomic Chat](https://github.com/robertosantosx2/LEONES/pull/139).
- [Plan de pruebas del runtime Atomic Chat Core](https://github.com/robertosantosx2/LEONES/blob/research/atomic-chat-tensorfold-linux-cuda/research/atomic-chat-tensorfold-core-runtime-test-plan-2026-11-06.md).
- [Elegibilidad de checkpoints TensorFold](https://github.com/robertosantosx2/LEONES/blob/research/atomic-chat-tensorfold-linux-cuda/research/atomic-chat-tensorfold-checkpoint-eligibility-2026-11-06.md).
- [PoC de TensorFold para Atomic Chat en LEONES](https://github.com/robertosantosx2/LEONES/tree/research/atomic-chat-tensorfold-linux-cuda/experiments/atomic-chat-tensorfold).
- [Repositorio Atomic Chat Core](https://github.com/AtomicBot-ai/atomic-chat-core).

**Decisión:** GO para abrir y discutir el feature request e implementar un adaptador experimental en Linux/CUDA; NO-GO para marcarlo como backend disponible o recomendarlo como integración de producción hasta completar pruebas reales de API/streaming, gateway, ciclo de vida, gestión de GPU y apagado sin procesos huérfanos.

### 3.5 RustingStrata 1.2.1 — evaluación ampliada de Qwen en el MSI (12-11-2026)

**Clasificación:** evaluación documental del catálogo y de las pruebas upstream, complementaria a las ejecuciones locales ya registradas. No se ha instalado ni ejecutado RustingStrata 1.2.1 en esta nueva campaña ni se han descargado los modelos grandes mencionados aquí. No promover estos modelos a «ejecutados» o «medidos en el MSI».

**Proyecto:** [RustingStrata](https://github.com/RustingStudio/RustingStrata), motor de inferencia escrito en Rust para modelos GGUF. La versión declarada en su README consultado es **1.2.1**. Incluye kernels CUDA compilados en tiempo de ejecución mediante NVRTC y backend Vulkan; los expertos que no caben en VRAM pueden ejecutarse en CPU mientras la GPU trabaja. La colocación de expertos se adapta al enrutamiento observado. No depende de llama.cpp/ggml para el motor de inferencia.

**Familias declaradas upstream:** Qwen3.5/3.6 (`qwen35moe`, `qwen35`), Qwen3-Next (`qwen3next`), Qwen3.8-Flash-Next (`qwen4exp`), Qwen3 (`qwen3`, `qwen3moe`), además de DeepSeek-V4.1-Flash y GLM-5.3-Flash. La presencia en el catálogo no garantiza que cada cuantización, modalidad o variante pueda ejecutarse con la memoria disponible en el MSI.

**Compatibilidad de GPU:** el proyecto declara CUDA para Volta (sm_70), Turing (sm_75) y Ampere o posterior (sm_80+). La RTX 3050 Laptop del MSI es Ampere sm_86 y cumple ese nivel de arquitectura; sin embargo, la tabla upstream de tarjetas realmente probadas identifica una RTX 3060 12 GB como referencia Ampere, no una RTX 3050 4 GB. Por tanto, sm_86 es una compatibilidad arquitectónica declarada, no una validación de rendimiento ni de memoria para este portátil. CUDA NVRTC se carga en tiempo de ejecución. Vulkan requiere Vulkan 1.3 y capacidades adicionales del controlador.

#### Modelos Qwen: catálogo upstream y viabilidad estimada en el MSI

| Modelo / archivo upstream | Evidencia publicada por RustingStrata | Situación estimada en MSI: 14 GiB RAM + RTX 3050 4 GiB |
|---|---|---|
| **Qwen3.5-2B Q4_K_M** | 208 tok/s de decode en RTX 3060 12 GB (CUDA/Vulkan, prueba breve) | **Candidato prioritario.** Ya existe ejecución local anterior con TensorFold; RustingStrata requiere benchmark propio para comparar motores. || **Qwen3-4B-Instruct-2507 Q4_K_M** | 104/110 tok/s CUDA/Vulkan en RTX 3060 12 GB | **Candidato prioritario.** Tamaño más razonable para probar con contexto moderado; rendimiento MSI desconocido. |
| **Qwen3.5-9B Q5_K_S** | 51/53 tok/s CUDA/Vulkan en RTX 3060 12 GB | **Prueba condicionada.** Con 14 GiB RAM y 4 GiB VRAM puede haber presión de memoria; empezar con cuantización más pequeña y contexto bajo si existe artefacto compatible. |
| **Qwen3-30B-A3B UD-Q2_K_XL** | 114/123 tok/s CUDA/Vulkan en RTX 3060 12 GB | **Experimental y muy ajustado.** Ya hay ejecución local previa de Qwen3-30B-A3B IQ3_XXS con RustingStrata registrada en este inventario, pero no extrapolar sus resultados a este archivo ni a Qwen3.6. |
| **Qwen3.6-35B-A3B UD-Q2_K_XL** | Archivo de 11,7 GiB; 118,2 tok/s decode corto y 113,4 tras prompt de 4K en RTX 3060 12 GB / Ryzen 5 7600X / 32 GB RAM | **No recomendado con la configuración actual.** El archivo por sí solo consume casi toda la RAM física nominal; además hacen falta SO, caché, KV y buffers. Solo tendría sentido como experimento con RAM ampliada y contexto limitado. |
| **Qwen3.6-35B-A3B UD-Q4_XS** | 94/96 tok/s CUDA/Vulkan en RTX 3060 12 GB; el upstream indica que cabía el 57% de los expertos en VRAM | **No viable como primera prueba en 4 GiB VRAM / 14 GiB RAM.** La referencia dispone de tres veces la VRAM y más del doble de RAM. |
| **Qwen3.8-27B UD-IQ3_XXS** | 20,6/20,5 tok/s CUDA/Vulkan en RTX 3060 12 GB; se indica una ocupación GPU de 10,8 GB | **No recomendado.** La huella GPU de referencia ya excede ampliamente los 4 GiB disponibles. El offload CPU no elimina la necesidad de memoria host suficiente. |
| **Qwen3.8-Flash-Next GSQ-RCO IQ2_XS** | GGUF de dos shards, aproximadamente 64 GB; 33,0 tok/s decode y 109,3 tok/s prefill en RustingStrata sobre RTX 3060 12 GB y 30 GiB RAM. Los expertos que no cabían en GPU se leían parcialmente desde NVMe. | **No viable en el MSI actual.** La referencia utilizó más del doble de RAM física y tres veces la VRAM. El propio informe advierte de streaming desde NVMe; con 14 GiB RAM la presión de memoria y el tráfico de disco serían extremos. |

Las velocidades upstream son cifras del mantenedor y no se deben presentar como resultados independientes ni como predicción de rendimiento para el MSI. En particular, el dato Qwen3.8-Flash-Next de 33 tok/s no implica que el modelo pueda alcanzar esa velocidad con 4 GiB VRAM y 14 GiB RAM.

#### Orden recomendado para una campaña local

1. Qwen3.5-2B Q4_K_M: smoke test y comparación directa con TensorFold.
2. Qwen3-4B-Instruct-2507 Q4_K_M: medir prefill, decode, TTFT, RAM y VRAM.
3. Qwen3.5-9B con cuantización conservadora: solo si los dos anteriores terminan sin swap excesivo.
4. Qwen3.6-35B-A3B IQ2: aplazar hasta ampliar RAM; no descargar el Qwen3.8-Flash-Next de ~64 GB en la configuración actual.

Para que la comparación sea válida, fijar GGUF exacto y SHA-256, contexto, prompt, longitud de salida, backend, versión, temperatura, número de repeticiones y estado de page cache. Registrar por separado prefill, decode, TTFT, RAM pico, swap, VRAM pico, temperatura y tiempo de carga. No comparar el benchmark de referencia RTX 3060 con el MSI como si fueran máquinas equivalentes.

**Comandos de referencia (no ejecutados en esta actualización):**

```bash
rustingstrata --version
rustingstrata check --backend cuda --model /ruta/al/modelo.gguf
rustingstrata calibrate --model /ruta/al/modelo.gguf
rustingstrata bench --model /ruta/al/modelo.gguf --gpu --mtp 0 --pp 512,4096 --tg 128 --reps 3 --ctx 4096
```

La calibración se realiza una vez por modelo y máquina. Para las primeras pruebas conviene mantener el contexto en 2048–4096 y dejar margen de VRAM; no aumentar el contexto hasta comprobar el consumo real. RustingStrata lee expertos que no caben en GPU desde el GGUF mediante la caché de páginas del sistema, por lo que la ubicación del modelo en un sistema de archivos que cachee datos y el estado de page cache pueden cambiar sustancialmente los resultados.

**Fuentes upstream consultadas (12-11-2026):**
- [RustingStrata — README, familias, cuantizaciones y resultados resumidos](https://github.com/RustingStudio/RustingStrata)
- [Uso, CLI, contexto, KV y API](https://github.com/RustingStudio/RustingStrata/blob/main/docs/USAGE.md)
- [Benchmarks detallados Qwen3.6 y Qwen3.8](https://github.com/RustingStudio/RustingStrata/blob/main/docs/BENCHMARKS.md)
- [Matriz de GPUs probadas y clases CUDA admitidas](https://github.com/RustingStudio/RustingStrata/blob/main/docs/SUPPORTED_GPUS.md)


### 3.6 Qwen3.6-35B-A3B con RustingStrata — evaluación para MSI RTX 3050 (12-11-2026)

**Clasificación LEONES:** compatibilidad de arquitectura plausible; viabilidad de memoria **no demostrada**; no instalado ni ejecutado con este modelo en el MSI. No registrar como benchmark local ni atribuirle velocidades estimadas.

**Motor y soporte upstream.** [RustingStrata](https://github.com/RustingStudio/RustingStrata) es un motor de inferencia en Rust para modelos Qwen GGUF. La versión declarada en el README consultado es **v1.2.1**. La familia Qwen3.6-35B-A3B se identifica mediante la arquitectura GGUF `qwen35moe`. El backend CUDA compila kernels en tiempo de ejecución mediante NVRTC/cudarc; no requiere compilar llama.cpp ni ggml. Los expertos que no caben en VRAM pueden ejecutarse en CPU mientras la GPU procesa su parte, con colocación adaptativa según el enrutamiento.

**Modelo candidato:** `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf`, tamaño publicado **11,7 GiB**. Es la variante concreta utilizada por el mantenedor en la prueba de referencia. No confundir los aproximadamente 3B parámetros activos por token con el tamaño de los pesos que deben estar disponibles: el modelo es MoE, pero sus expertos siguen ocupando almacenamiento y memoria de trabajo.

| Parámetro | Referencia upstream | MSI LEONES |
|---|---:|---:|
| GPU | RTX 3060 12 GiB, Ampere sm_86 | RTX 3050 Laptop 4 GiB, Ampere sm_86 |
| CPU | Ryzen 5 7600X | Intel Core i7-12650H |
| RAM | 32 GiB | 14 GiB |
| Modelo | UD-Q2_K_XL, 11,7 GiB | Mismo archivo, si se confirma integridad y disponibilidad |
| Backend | CUDA/NVRTC | CUDA/NVRTC previsto; no probado con este modelo |
| Estado | Benchmark del mantenedor | **Pendiente; sin inferencia local** |

**Compatibilidad GPU:** el README declara NVIDIA Ampere o posterior (`sm_80+`) para CUDA. La RTX 3050 Laptop `sm_86` cumple ese requisito de arquitectura. Sin embargo, `docs/SUPPORTED_GPUS.md` marca como referencia probada para Qwen3.6-35B-A3B una RTX 3060 12 GiB; no incluye la RTX 3050. Por tanto, el umbral de arquitectura permite investigar la ruta, pero no acredita compatibilidad funcional ni rendimiento en esta GPU concreta. El driver local 580.178.04 y NVRTC/CUDA deben verificarse con el binario/compilación usados; el toolkit CUDA 13.4 del sistema no debe confundirse con la biblioteca NVRTC que el motor carga en tiempo de ejecución.

**Resultados upstream — no son resultados del MSI.** En RTX 3060 12 GiB + Ryzen 5 7600X + 32 GiB RAM, RustingStrata publica para el archivo Q2:
- Prefill 4K: **2216 tok/s** (rango 2169–2252).
- Decode tras prompt 4K: **113,4 tok/s** (110,9–114,8).
- Decode con prompt corto: **118,2 tok/s** (117,0–118,8).
- MTP greedy: hasta **160 tok/s** con prompt corto y **152 tok/s** después de 4K.
- A 32K: prefill 1800 tok/s y decode 91,9 tok/s.

El protocolo publicado utiliza `rustingstrata bench --gpu --mtp 0 --pp 512,4096,32768 --tg 128 --reps 3 --ctx 32896`. El mantenedor también publica una simulación de margen de VRAM de aproximadamente 8/6 GiB en la RTX 3060; **no es una prueba en tarjetas reales de 8/6 GiB y no permite extrapolar a 4 GiB**. Las cifras de MTP dependen del texto. No copiar ninguna de estas velocidades a las tablas de rendimiento del MSI.

**Riesgo principal: memoria host.** El modelo pesa 11,7 GiB, la VRAM local es de solo 4 GiB y la RAM física total es 14 GiB, compartida con Ubuntu, procesos, buffers y cachés. El offload híbrido hace técnicamente interesante el ensayo, pero puede dejar una cantidad muy ajustada para expertos residentes/accedidos desde CPU y estructuras auxiliares. La swap de 31 GiB puede evitar un OOM inmediato, pero no equivale a RAM: si el working set cae continuamente en swap o provoca lecturas de disco, la latencia puede degradarse gravemente. No afirmar que el modelo cabe de forma holgada ni que el rendimiento será proporcional al de la RTX 3060.

**Decisión:** **GO condicionado para una prueba controlada; NO-GO para considerarlo ya operativo o recomendado como modelo diario.** Antes de descargar/ejecutar, confirmar espacio libre, versión exacta del motor, NVRTC disponible y tamaño/hash del GGUF. Realizar primero una carga con contexto pequeño y monitorizar RAM, swap, VRAM, temperatura y logs. Interrumpir si aparece swapping sostenido, OOM o inestabilidad del escritorio.

**Receta de validación propuesta (no ejecutada):**

```bash
# 1) Entorno y recursos
nvidia-smi
free -h
df -h "$HOME"
ldconfig -p | grep -i nvrtc

# 2) Obtener/compilar RustingStrata en un checkout aislado
git clone https://github.com/RustingStudio/RustingStrata.git
cd RustingStrata
git rev-parse HEAD
cargo build --release

# 3) Fijar la ruta real al GGUF Q2 y verificar su hash
M="$HOME/models/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf"
stat -c '%n %s bytes' "$M"
sha256sum "$M"

# 4) Consultar flags de la versión compilada antes de cargar el modelo
target/release/rustingstrata bench --help
target/release/rustingstrata calibrate --help
```

Una vez verificados los flags de la versión fijada, comenzar con calibración y benchmark corto/contexto pequeño, guardar stdout/stderr y una captura de `nvidia-smi`/RAM durante carga e inferencia. Para una comparación válida, registrar contexto, prompt, tokens generados, `--mtp 0` y `--mtp 1` en campañas separadas, repeticiones, versión/commit, hash del GGUF, consumo máximo de RAM/swap/VRAM y cualquier error. No asumir que la receta de referencia se ejecuta sin ajustes en 4 GiB.

**Fuentes primarias:**
- [RustingStrata — repositorio y README v1.2.1](https://github.com/RustingStudio/RustingStrata)
- [GPU soportadas y distinción entre probadas y solo compilables](https://github.com/RustingStudio/RustingStrata/blob/main/docs/SUPPORTED_GPUS.md)
- [Uso, flags, KV cache, calibración y page cache](https://github.com/RustingStudio/RustingStrata/blob/main/docs/USAGE.md)- [Benchmarks y protocolo upstream](https://github.com/RustingStudio/RustingStrata/blob/main/docs/BENCHMARKS.md)
- [Resultados de referencia Qwen3.6-35B-A3B](https://rustingstudio.com/strata/docs/v1-results/)
- [Ficha del motor y resultados publicados](https://rustingstudio.com/strata/)

## 3.7 Phi-4-mini-instruct — evaluación de viabilidad y plan de prueba en MSI (12-11-2026)

**Estado LEONES:** `RESEARCH_ONLY / CANDIDATE / NOT_DOWNLOADED / NOT_RUN_ON_MSI`. Esta actualización documenta la selección y el procedimiento propuesto; no acredita descarga, carga, generación ni benchmark local.

**Modelo seleccionado:** [Microsoft Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct), modelo denso decoder-only de **3,8B parámetros**. La ficha oficial declara ventana de contexto de hasta **128K tokens**, soporte de español y otras lenguas, chat-completion y licencia MIT. Microsoft advierte que el rendimiento puede variar entre idiomas y que el modelo puede presentar limitaciones en idiomas distintos del inglés. El checkpoint oficial de Microsoft está publicado en Safetensors; para esta prueba se propone un GGUF comunitario, que debe identificarse como tal y no atribuirse como conversión oficial de Microsoft.

**Artefacto GGUF recomendado:** [unsloth/Phi-4-mini-instruct-GGUF](https://huggingface.co/unsloth/Phi-4-mini-instruct-GGUF), archivo `Phi-4-mini-instruct-Q4_K_M.gguf`, tamaño publicado **2,49 GB**. La ficha del repositorio describe su uso con llama.cpp y el archivo incluye el formato de chat de Phi. La cuantización Q4_K_M es el punto de partida recomendado por equilibrio entre tamaño y calidad; el tamaño del archivo no equivale al consumo total de RAM/VRAM durante inferencia.

**Viabilidad para el MSI Thin 15 B12UC:**
- Hardware: Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB (sm_86), Ubuntu, driver 580.178.04, CUDA runtime 13.0 y swap de 31 GiB.
- **Candidato viable para una prueba controlada**, especialmente con llama.cpp GGUF. El archivo Q4_K_M de 2,49 GB cabe en almacenamiento y su huella de pesos es compatible con una prueba en este equipo; aún hay que reservar memoria para el proceso, buffers, contexto/KV y el sistema.
- No asumir que todo el modelo cabe en los 4 GiB de VRAM. Comenzar en CPU y después probar offload parcial; vigilar VRAM y RAM pico. El offload no debe fijarse por anticipado como óptimo.
- Aunque Microsoft anuncia 128K de contexto, no intentar ese contexto en el MSI. Empezar con 2.048 tokens y subir a 4.096 solo si el consumo real deja margen. La memoria KV y los buffers crecen con el contexto.
- No confundir Phi-4-mini-instruct (3,8B) con Phi-4 (14B), Phi-4-multimodal (5,6B) ni Phi-4-reasoning (14B); esta campaña se limita al modelo mini de texto.

**Descarga propuesta (no ejecutada en esta actualización):**

```bash
mkdir -p ~/phi-lab/models ~/phi-lab/results
cd ~/phi-lab/models
wget -c -O Phi-4-mini-instruct-Q4_K_M.gguf \
  "https://huggingface.co/unsloth/Phi-4-mini-instruct-GGUF/resolve/main/Phi-4-mini-instruct-Q4_K_M.gguf"
sha256sum Phi-4-mini-instruct-Q4_K_M.gguf | tee ../results/model.sha256
```

**Primera prueba funcional con llama.cpp CUDA local (no ejecutada):**

Usar el binario CUDA ya disponible en `~/llama-cpp-cuda/build/bin/llama-cli`, verificando primero su versión. La primera pasada será CPU-only para separar compatibilidad del modelo de la asignación CUDA:

```bash
cd ~/phi-lab
LLAMA="$HOME/llama-cpp-cuda/build/bin/llama-cli"
MODEL="$HOME/phi-lab/models/Phi-4-mini-instruct-Q4_K_M.gguf"
"$LLAMA" --version
"$LLAMA" -m "$MODEL" -c 2048 -ngl 0 -n 128 -cnv \
  2>&1 | tee results/phi4-mini-cpu.log
```

Si la carga CPU funciona, repetir con offload parcial conservador (por ejemplo `-ngl 8`), registrar `nvidia-smi` antes/durante/después y detener la prueba si aparece OOM o presión severa de memoria. Ajustar el número de capas solo a partir de la telemetría observada; no dar por supuesto que `-ngl 8` es la configuración óptima.

**Matriz mínima de benchmark:**

| Variante | Backend | Contexto inicial | Estado |
|---|---|---:|---|
| CPU baseline | llama.cpp, `-ngl 0` | 2.048 | Pendiente |
| CUDA parcial | llama.cpp, `-ngl 8` inicial; ajustar según VRAM | 2.048 | Pendiente |
| CUDA ajustado | Offload máximo estable, medido y documentado | 2.048; después 4.096 si hay margen | Pendiente |

Para cada variante registrar modelo/archivo exacto, SHA-256, versión y commit de llama.cpp, comando completo, prompt, seed, tokens de entrada/salida, prefill (tok/s), decode (tok/s), TTFT, latencia total, RAM pico, swap, VRAM pico, temperatura y resultado funcional. Ejecutar al menos tres repeticiones por configuración y mantener separadas las métricas CLI y API. No comparar resultados con otros modelos si cambian prompt, contexto o protocolo.

**Criterio de promoción:** Phi-4-mini-instruct solo pasa a «ejecutado» cuando exista un log de carga y generación real en el MSI; solo pasa a «medido» cuando se archiven las métricas y la configuración reproducible. Hasta entonces, todas las velocidades y consumos locales son N/D.

**Fuentes primarias y artefactos:**
- [Microsoft — ficha oficial Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct)
- [Microsoft Foundry — ficha del modelo, 3,8B y 128K](https://ai.azure.com/catalog/models/Phi-4-mini-instruct)
- [Unsloth — GGUF Q4_K_M (2,49 GB) y guía llama.cpp](https://huggingface.co/unsloth/Phi-4-mini-instruct-GGUF)
- [Archivo Q4_K_M](https://huggingface.co/unsloth/Phi-4-mini-instruct-GGUF/blob/main/Phi-4-mini-instruct-Q4_K_M.gguf)

## 3.8 Colibri — Qwen3.6 CUDA: presupuesto, colocación de cadena y limpieza de setup (12-11-2026)

**Estado:** desarrollo de código en el fork; revisión estática y preparación de pruebas. **No ejecutado, no compilado y no validado en el MSI** a fecha de esta actualización. No hay velocidades, prefill, decode, TTFT ni consumo medidos que registrar.

**Repositorio y propuesta:**
- Fork y rama: [robertosantosx2/colibri — research/qwen36-cuda-chain-planner](https://github.com/robertosantosx2/colibri/tree/research/qwen36-cuda-chain-planner).
- Revisión: [PR draft #1](https://github.com/robertosantosx2/colibri/pull/1), base `main`; último SHA conocido al consolidar: `3cbc2326345fa8c25097ae60ef07e5cb67019663`.
- El intento de abrir el PR contra el repositorio upstream [JustVugg/colibri](https://github.com/JustVugg/colibri) no prosperó por un error HTTP 403 de permisos del conector. Por tanto, **no existe PR upstream**; el único PR abierto es el borrador en el fork.

**Cambios incluidos en el borrador:**
1. **Presupuesto CUDA:** el valor numérico de `CUDA_EXPERT_GB` queda limitado por la memoria libre después de reservar 1 GiB de headroom, `G_reserve` y el trunk. Si la petición excede el presupuesto disponible, se recorta y se informa.
2. **Admisión automática de la cadena:** la planificación intenta colocar todos los tensores ofrecidos de la cadena en un mismo dispositivo; si el conjunto no cabe, la decisión automática es mantener la cadena completa en CPU, evitando una colocación parcial por este planificador. Es una política de admisión por tamaño, no un cargador transaccional.
3. **Ciclo de vida de setup:** se centraliza la liberación de recursos propios tras fallos de inicialización parcial, se limpia `m->cchain` y se registra el apagado del backend inmediatamente después de inicializarlo correctamente. Los handles prestados a la capa de tiers no se liberan desde el cleanup de la cadena.
4. **Regresiones fake-CUDA añadidas:** prueba del clamp de presupuesto, colocación completa/fallback y fallo de setup parcial tras reservar el arena de parámetros. Estas pruebas están en el código, pero **todavía no se han ejecutado**.

**Límites y riesgos pendientes:** la ruta de uploads de la capa tier, los fallos asíncronos de subida y la interacción real con el backend CUDA requieren validación. La limpieza de tablas auxiliares host se ha revisado estáticamente, pero la prueba añadida comprueba el puntero de cadena y el contador de bytes del backend falso; no mide directamente fugas de malloc. La seguridad de apagados repetidos tampoco debe considerarse demostrada solo por revisión de código.

**Validación pendiente en el MSI (RTX 3050 4 GiB, sm_86):** seguir el [runbook de validación Qwen3.6 CUDA](../subprojects/Colibri/research/msi-qwen36-cuda-validation-runbook-2026-11-10.md). La secuencia inicial es compilar y ejecutar `tests/test_qwen36_cuda_chain`, después ejecutar `make test-c CUDA=1` y finalmente compilar el objetivo CUDA con `CUDA_HOME=/usr/local/cuda-13.4 CUDA_ARCH=sm_86`. Solo si esas etapas pasan se debe continuar con una carga/inferencia corta, registrando logs y telemetría. La prueba fake-CUDA no sustituye la validación en GPU.

**Auditoría y evidencia de trabajo:**
- [Auditoría del ciclo de vida de setup y regresión parcial](../subprojects/Colibri/research/qwen36-chain-setup-lifecycle-audit-2026-11-10.md).
- [Runbook de validación en MSI](../subprojects/Colibri/research/msi-qwen36-cuda-validation-runbook-2026-11-10.md).
- [Documentación del análisis de integración tandem.cpp](https://github.com/robertosantosx2/colibri/blob/research/qwen36-cuda-chain-planner/docs/research/tandem-cpp-moe-integration.md).

**Criterio de promoción:** Colibri solo pasa a «compilado» cuando se conserve la salida de compilación; a «validado» cuando pasen las pruebas automatizadas y la compilación CUDA en el MSI; y a «ejecutado/medido» cuando exista una inferencia Qwen3.6 reproducible con modelo, hash, contexto, parámetros, logs y métricas PP/TG/TTFT y memoria. Hasta entonces, rendimiento local = N/D.

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
- [MiniCPM5-2B Q4_K_M — llama.cpp CUDA y cierre DSpark en RTX 3050](../MINICPM5-2B-RTX3050-2026-11-11.md)
- [LocalAI y Parakeet.cpp — investigación de integración y benchmark propuesto](../../research/localai-parakeet-integration.md)
- [Open-dCoder — resumen ejecutivo y mapa V1/V2/V3](../subprojects/Open-dCoder/EXECUTIVE-SUMMARY.md)
- [Open-dCoder — informe V1/V2](../subprojects/Open-dCoder/EXPERIMENT-2026-10-31.md)
- [Open-dCoder — informe V3 batch real](../subprojects/Open-dCoder/EXPERIMENT-V3-BATCH-2026-10-31.md)
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
- [TensorFold upstream — PR #1879](https://github.com/ashhart/TensorFold/pull/1879)
- [TensorFold upstream — release v1.2.7 (contraste de incorporación)](https://github.com/ashhart/TensorFold/releases/tag/v1.2.7)
- [Propuesta de backend nativo TensorFold para Atomic Chat — investigación y alcance](../../research/atomic-chat-tensorfold-core-runtime-test-plan-2026-11-06.md)
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
6. No rellenar N/D con estimaciones. Las estimaciones pertenecen a informes de viabilidad.7. Actualizar la tabla al cerrar cada campaña; una prueba solo pasa a “medida” con evidencia reproducible.
8. Usar el manifiesto de evidencia LEONES para nuevos benchmarks y mantener esta página como índice humano.

## 6. Pendientes de consolidación

- Archivar en LEONES los logs, JSONL, manifiesto y configuración íntegra de Tandem Qwen3.5-35B-A3B IQ2_XXS si no están ya completos.
- Clonar y auditar el código fuente de ThumbLLM en Ubuntu, compilar el runtime CPU fijado, verificar el GGUF y portar/validar el frontend Linux; registrar una campaña reproducible antes de marcarlo como ejecutado.\n- Consolidar los resultados finales de Kinetic por modelo, cuantización, backend y versión.
- **YASAKANI:** localizar/confirmar el repositorio y su versión; auditar README, licencia, dependencias, requisitos de CPU/GPU/CUDA, modelos y formatos admitidos; preparar instalación aislada; ejecutar primero comprobaciones no destructivas y después una inferencia mínima en el MSI. Archivar comandos, commits, logs, configuración, consumo RAM/VRAM y métricas de prefill/decode/latencia si aplica. Hasta entonces, mantener `PENDIENTE DE IDENTIFICACIÓN / NO EJECUTADO`; no inferir compatibilidad ni rendimiento.
- Ejecutar y archivar la reproducción Ubuntu de ThumbLLM/Ornith 1.5 9B: log de descarga y SHA-256, commit/flags de compilación, versión resultante de llama.cpp, configuración efectiva, log de carga/inferencia y métricas PP/TG; solo entonces promoverla a ejecución medida.- Mantener Colibri como auditoría/compilación hasta disponer de inferencia reproducible.
- Incorporar futuras pruebas como campañas fechadas, sin sobrescribir resultados históricos.

---
**Nota de precisión:** este inventario combina informes versionados de LEONES con resultados de laboratorio comunicados durante las sesiones. Los registros que todavía no tienen artefacto bruto versionado quedan identificados como pendientes de archivo; no se presentan como evidencia independiente auditada.

## 3.7 Project Maya — catálogo vigente y viabilidad en el MSI Ubuntu (12-11-2026)

**Clasificación LEONES:** investigación documental de upstream; **no instalado, no descargado y no ejecutado** en el MSI. No hay mediciones locales de prefill, decode, TTFT, VRAM, RAM ni estabilidad. La presencia de un modelo en el catálogo de Maya no equivale a que sea ejecutable en el hardware de referencia.

**Proyecto y arquitectura.** [Project Maya](https://github.com/mw00/project-maya) es un runtime MoE especializado, no un cargador universal de GGUF. Mantiene los expertos más usados en VRAM, otros en RAM y los restantes en NVMe, moviéndolos según el enrutamiento. Tiene motores/rutas específicas para familias de modelos y expone API compatibles con OpenAI y Anthropic, interfaz web y monitor. La compatibilidad declarada upstream incluye NVIDIA desde Volta / RTX 20, por lo que la RTX 3050 Ampere sm_86 cumple el umbral arquitectónico de GPU; eso no resuelve el déficit de memoria del equipo.

**Catálogo upstream observado el 12-11-2026.** Los cuatro modelos principales y Qwen aparecen en la documentación actual del repositorio:

| Modelo / variante | Cuantización o pack documentado | Descarga aproximada | Memoria total recomendada (VRAM + RAM) | Evaluación en el MSI |
|---|---|---:|---:|---|
| **GLM-5.3-Flash (321B; 18B activos)** | Maya-XS / Maya-S24 / Maya-S / Maya-M / Maya-L; también EXL3 comunitarios | 73–156 GB (según pack) | 88–192 GB | No viable con 18 GiB combinados y 14 GiB RAM física |
| **GLM-5.3 (744B; ~40B activos)** | Maya-XS GGUF o UD-IQ2_M | 170–239 GB | 192–256 GB | No viable |
| **DeepSeek-V4.1-Flash-1017 (748B)** | Maya-XS / Maya-S, GGUF comunitarios y EXL3 | 277–467 GB según variante | 128–384 GB | No viable |
| **MiniMax-M3.1-Flash (428B; 23B activos)** | Maya-XS / Maya-S GGUF o EXL3 3.5 bpw | 93–197 GB | 128–256 GB | No viable |
| **Qwen-3.8-Flash-Next** | Unsloth UD-IQ2_XS GGUF o CYBER-FROST Q5_K_M GGUF | 80–113 GB según variante | 64 GB (UD-IQ2_XS) / 96 GB (CYBER-FROST) | Es el menos exigente, pero no cumple el mínimo de RAM física |

Los tamaños de descarga y los requisitos de memoria no son magnitudes intercambiables. En DeepSeek las tablas Engram/n-gram permanecen en SSD; en Qwen la tabla n-gram de 52 GB también permanece en SSD. El tamaño de pesos/descarga no es el total de RAM+VRAM necesario para mantener los expertos residentes.

**Requisitos mínimos frente al hardware del MSI.** La guía oficial de memoria indica que, incluso por debajo de la memoria recomendada y leyendo expertos desde SSD, cada modelo necesita como mínimo:
- GPU compatible (NVIDIA desde V100 / RTX 20 en adelante).
- **32 GB de RAM física**.
- SSD NVMe rápido con espacio suficiente para el modelo y sus índices/archivos auxiliares.

| Recurso | Requisito / recomendación Maya | MSI Thin 15 B12UC | Resultado |
|---|---:|---:|---|
| GPU NVIDIA | V100 / RTX 20 o posterior | RTX 3050 Laptop, Ampere sm_86, 4 GiB | Arquitectura compatible |
| RAM física | **32 GB mínimo** | **14 GiB** | **No cumple** |
| VRAM + RAM | Qwen UD-IQ2_XS: 64 GB recomendados; CYBER-FROST Q5_K_M: 96 GB | ≈18 GiB combinados | Muy por debajo |
| Almacenamiento | NVMe rápido | NVMe presente; espacio libre a comprobar | No compensa el déficit de RAM |
| Swap | No cuenta como RAM física | 32 GiB configurados | No sustituye el mínimo |

**Conclusión por modelo y decisión de compra.**
1. **No descargar ni lanzar ningún pack de Maya en la configuración actual.** Los 14 GiB de RAM incumplen el mínimo explícito de upstream. La swap no transforma ese límite en memoria física; forzar la carga puede provocar paginación extrema, OOM o una experiencia inutilizable.
2. **Qwen-3.8-Flash-Next UD-IQ2_XS es el primer candidato solo después de ampliar RAM.** El objetivo mínimo para experimentar sería 32 GB de RAM física y NVMe con espacio suficiente; para aproximarse al perfil recomendado, unos 60 GB de RAM con la RTX 3050 (≈64 GB combinados). No se ha demostrado rendimiento en esta GPU.
3. **CYBER-FROST Q5_K_M** requiere alrededor de 84 GB de memoria para el modelo y 96 GB recomendados; con 4 GiB de VRAM, apuntar a unos 92 GB de RAM para alcanzar la recomendación. No es una opción realista para el MSI sin una ampliación extraordinaria y debe seguir como investigación.
4. GLM-5.3-Flash, GLM-5.3, DeepSeek-V4.1-Flash y MiniMax-M3.1-Flash quedan fuera del alcance práctico de este portátil; sus tamaños y perfiles de memoria son de estaciones de trabajo/servidores con mucha más RAM y/o VRAM.

**Prueba no destructiva disponible, cuando se cumpla el mínimo de memoria:** clonar el repositorio y ejecutar `./maya.sh --check` para revisar GPU, driver, CUDA toolkit, compilador, CPU, RAM y condiciones del sistema. No ejecutar `--setup` ni seleccionar/descargar un modelo en el MSI actual. La documentación upstream advierte además que `systemd-oomd` en Ubuntu puede terminar la sesión de usuario durante cargas con presión de memoria; no se recomienda desactivarlo como atajo para eludir requisitos insuficientes.

**Implicación para LEONES:** mantener Maya en Experimental/Research como motor MoE externo opcional, con adaptador deshabilitado. No incluirlo en el conjunto de motores disponibles para el MSI ni en rankings de rendimiento. Una futura integración debe comprobar versión, familia, cuantización, formato, memoria física, VRAM, NVMe y disponibilidad de API por separado; no inferir soporte universal por ser GGUF. El código upstream vendorizado para la propuesta de integración está fijado en PR #142 a v1.1.58 (`a3582528bfb73175fed1757b485bfcaaf01aaeaa`); esa versión integrada en la rama de trabajo no debe confundirse con una ejecución local ni con una release instalada.

**Fuentes primarias (consulta 12-11-2026):**
- [Project Maya — repositorio y catálogo](https://github.com/mw00/project-maya)
- [Project Maya — requisitos y procedimiento de instalación](https://github.com/mw00/project-maya/blob/main/docs/SETUP.md)
- [Project Maya — tabla de memoria por modelo y mínimo de sistema](https://github.com/mw00/project-maya/blob/main/docs/MEMORY.md)
- [Project Maya — modelos, formatos y cuantizaciones](https://github.com/mw00/project-maya/blob/main/docs/MODELS.md)
- [Project Maya — parámetros y configuración Qwen-3.8-Flash-Next](https://github.com/mw00/project-maya/blob/main/docs/SETTINGS.md#qwen-38-flash-next-cyber-frost)
- [LEONES — propuesta de integración Project Maya, PR #142](https://github.com/robertosantosx2/LEONES/pull/142)


## 3.8 MiniCPM5-2B Q4_K_M — llama.cpp CUDA y evaluación DSpark cerrada (11-11-2026)

**Clasificación:** inferencia local medida con llama.cpp CUDA en el MSI; DSpark evaluado documentalmente y descartado para la configuración oficial en este equipo. El informe reproducible completo está en [MINICPM5-2B-RTX3050-2026-11-11.md](../MINICPM5-2B-RTX3050-2026-11-11.md).

**Artefacto ejecutado:** `openbmb/MiniCPM5-2B-GGUF`, archivo `MiniCPM5-2B-Q4_K_M.gguf`, tamaño aproximado 1,5 GiB, SHA-256 `ec2d5801640099e97d8d7e8003ad4d81f336e757811f03a26173dddf386602fd`. Motor local `llama.cpp 0.8.0-dev build 1`, commit `c3df4b7`.

| Backend / contexto | Prefill | Generación | Parámetros y observaciones |
|---|---:|---:|---|
| CPU / 512 | 54,3 tok/s | 21,5 tok/s | `-ngl 0`; 24 tokens de salida |
| CUDA / 512 | 755,3 tok/s | 86,5 tok/s | `-ngl 99`; batch 128, ubatch 64; 128 tokens solicitados |
| CUDA / 2.048 | 817,40 tok/s | 85,50 tok/s | Prompt 31 tokens; 256 generados; 3.020,39 ms total; salida detenida por límite de longitud |

La comparación de generación CUDA ctx 2048 frente a CPU da aproximadamente 3,98×, pero es orientativa: no se usaron exactamente el mismo prompt, contexto y límite de generación. En contexto 2048, el log confirmó 43/43 capas asignadas a CUDA (41 repetitivas y capa de salida), buffer modelo CUDA 1.340,64 MiB, buffer CPU mapeado 143,44 MiB, KV CUDA 84 MiB (K/V F16, 42 MiB cada uno) y compute buffer CUDA 6,75 MiB. Una lectura posterior registró 1.545 MiB de VRAM total ocupada, de los cuales 1.522 MiB correspondían al proceso llama-cli.

**Evaluación DSpark / SGLang.** La receta upstream consultada usa el modelo objetivo MiniCPM5-2B BF16 junto al borrador MiniCPM5-2B-DSpark BF16. El objetivo BF16 publicado ocupa aproximadamente 5,03 GB (4,69 GiB), ya por encima de los 4 GiB físicos de la RTX 3050 Laptop, antes de reservar memoria para el borrador, KV cache y runtime. La matriz/receta de SGLang consultada no valida RTX 3050 sm_86. Aunque existe un checkpoint GPTQ, la combinación GPTQ + DSPARK no está documentada en la receta actual y no se considera una ruta soportada. No se descargaron esos checkpoints ni se instaló SGLang.

**Auditoría de entorno (11-11-2026, 09:13):** Python 3.14.4; pip 25.1.1; PyTorch, SGLang, Triton y FlashInfer ausentes; CUDA Toolkit 13.4.92; driver NVIDIA 580.178.04 (nvidia-smi informa CUDA 13.0); 14 GiB RAM, 31 GiB swap, 309 GiB disponibles en la raíz. La GPU tenía 1.545 MiB ocupados en esa captura y llama-cli seguía activo con 1.522 MiB. No se modificó ni instaló ningún paquete durante la auditoría.

**Decisión final:** evaluación cerrada. MiniCPM5-2B queda como modelo ejecutado y medido con llama.cpp CUDA. SGLang + DSpark BF16 queda como **NO VIABLE en la configuración oficial para este MSI de 4 GiB**; GPTQ + DSpark como **NO DOCUMENTADO/NO SOPORTADO por la receta consultada**. No se ha probado una ejecución DSpark real y no debe etiquetarse como benchmark. Reabrir solo si aparece una ruta upstream explícita para objetivo cuantizado + DSpark y una estrategia de memoria que quepa, o si se dispone de hardware con VRAM suficiente.


## DSpine en llama.cpp — speculative decoding con DFlash (12-11-2026)

**Estado LEONES:** integración de código auditada y build CPU del fork completados en CI; GGUF del drafter Qwen3.8-27B verificado por CI. **Pendiente de preflight, compilación CUDA SM86 e inferencia en el MSI.** No se contabiliza como motor ejecutado ni como benchmark local.

DSpine (*Draft in Parallel, Condition Through Depth: Adjacent Causal Injection for Speculative Decoding*) es una arquitectura de speculative decoding que construye candidatos en paralelo e inyecta información del token predecesor a través de capas, con refinamiento serial de la última escritura y una tabla de transición. En el fork investigado no aparece como un tipo de speculative decoding separado: está integrado en el modelo DFlash y se selecciona mediante `--spec-type draft-dflash`.

### Implementación auditada

- **Fork:** [Ajay9o9/llama.cpp, rama dspine](https://github.com/Ajay9o9/llama.cpp/tree/dspine).
- **Commit fijado:** [`d493f841b20241606c47a4e0537d3c786b5cf50b`](https://github.com/Ajay9o9/llama.cpp/commit/d493f841b20241606c47a4e0537d3c786b5cf50b), evitando depender de una rama móvil.
- Se localizaron y auditaron el esquema GGUF `DSPINE_*`, el mapeo `selected_prefix_bridge.*`, la conversión HF→GGUF en `conversion/qwen.py`, el loader C++ en `src/models/dflash.cpp`, los grafos `build_dspine_write` / `build_dspine_lattice` y la ruta de speculative decoding `draft-dflash`.
- La integración requiere la ruta DFlash compatible; no basta con que un modelo sea Qwen ni con renombrar un checkpoint.

### Compatibilidad de checkpoints

El checkpoint oficial [`tencent/Qwen3-8B-DSpine-b16`](https://huggingface.co/tencent/Qwen3-8B-DSpine-b16) **no es compatible con la implementación actual de este fork**. Su configuración no declara `code_bridge_second_pass.mode=serial_table` ni el `head_topk` requerido por el refinamiento de última escritura. El conversor lo rechaza explícitamente. LEONES retiró la receta de conversión para este checkpoint; no se inventan metadatos ni se fuerza su carga.

La pareja investigada para la validación actual es:

| Componente | Artefacto | Tamaño aproximado | Estado |
|---|---|---:|---|
| Target | [Qwen3.8-27B IQ2_XXS GGUF](https://huggingface.co/bartowski/Qwen3.8-27B-GGUF) | 8,88 GB | Candidato experimental para el MSI; cuantización muy agresiva |
| Drafter DSpine | [Qwen3.8-27B-DSpine-b16 Q4_K_M GGUF](https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF) | 1,26 GB | Verificado por CI; pesos del code bridge conservados en BF16 |

El total de pesos estimado es **10,14 GB**, antes de KV cache, buffers y memoria del runtime. No cabe íntegramente en los 4 GiB de VRAM de la RTX 3050; cualquier ensayo requiere offload híbrido CPU/GPU, contexto corto y selección explícita de capas GPU. La cuantización IQ2_XXS del target puede degradar sustancialmente la calidad: esta pareja se plantea como *smoke test* de viabilidad, no como recomendación de calidad o producción.

### Evidencia reproducible y estado de validación

Workflow [LEONES DSpine CI #42991023838](https://github.com/robertosantosx2/LEONES/actions/runs/42991023838), completado con éxito:

- **Auditoría estática:** 7/7 comprobaciones de integración detectadas.
- **Tests del auditor:** PASS.
- **Sintaxis:** comprobaciones `bash -n` y `py_compile` PASS.
- **Build CPU:** `llama-cli` compilado desde el commit fijado del fork; GCC 13.3.0, llama.cpp 0.9.0-dev.
- **GGUF DSpine Qwen3.8-27B:** descarga, inventario de tensores y validación de metadatos completados; se publicó un artefacto CI con informe y SHA-256.
- **Qwen3-8B:** rechazo de conversión esperado por incompatibilidad de `serial_table`; no se declara soportado.
- **CUDA SM86 / MSI:** todavía no ejecutado. No hay velocidad de prefill, decode, aceptación especulativa ni comparación greedy/DSpine medida en el equipo.

El desarrollo y las recetas están aislados en [PR #143](https://github.com/robertosantosx2/LEONES/pull/143), rama `research/dspine-llama-cpp`; no modifican el llama.cpp instalado ni acreditan todavía una integración en el upstream oficial de ggml-org.

### Próxima validación en el MSI

1. Ejecutar primero `scripts/dspine-msi-preflight.sh` desde el worktree de la rama para confirmar driver, CUDA, compilador, RAM y espacio disponible. El preflight es de solo lectura.
2. Si el preflight es correcto, compilar en un directorio aislado con `scripts/build_dspine_llama_cpp_cuda_msi.sh`, fijado al commit auditado y a CUDA SM86. No sustituir el llama.cpp instalado.
3. Empezar con contexto 512, `--spec-draft-n-max 3`, `-np 1`, KV Q8_0 y offload GPU conservador explícito tanto para target como para drafter. Ajustar capas solo tras comprobar VRAM real; no copiar configuraciones `-ngl 999` de GPUs de 24 GiB.
4. Comparar target greedy y DSpine con el mismo prompt, contexto y condiciones. Registrar tokens/s de prompt y generación, latencia, tokens aceptados/rechazados, RAM, swap, VRAM, SHA de ambos GGUF y logs completos.
5. Detener la prueba ante OOM, avisos de tensores/metadatos, salida inestable o presión sostenida de swap.

**Conclusión:** DSpine ya tiene una ruta de código identificada, auditada y compilada en CPU, y un drafter Qwen3.8-27B GGUF validado en CI. El siguiente hito no es otro análisis documental: es superar el preflight del MSI y demostrar una inferencia CUDA SM86 reproducible. Hasta entonces, el soporte local permanece en estado *experimental / no ejecutado*.
