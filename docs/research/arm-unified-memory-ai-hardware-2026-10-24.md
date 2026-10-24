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

## 0. Metodología permanente del estudio: fuentes públicas, Artificial Analysis y coste por tokens/s

> **Regla de alcance:** este trabajo es una comparativa de investigación documental. No se comprarán placas, no se harán pruebas físicas y no se presentarán pruebas de laboratorio como siguiente paso requerido. Toda actualización del informe debe respetar esta regla, salvo que el usuario cambie explícitamente el alcance.

### Preguntas que debe responder el resultado final

1. **¿Qué tasa de generación (decode tokens/s) se publica para los mejores modelos que pueden ejecutarse razonablemente en cada plataforma?**
2. **¿Cuál es el coste de capital por unidad de rendimiento publicado?** Métrica principal: **coste de hardware en EUR por token/s** (EUR/(tokens/s)); cuanto menor, mejor. Presentar también la inversa, **tokens/s por 1.000 € de hardware**, que resulta más intuitiva.
3. **¿Qué modelo es el mejor candidato según Artificial Analysis (AA)** para la tarea y las restricciones del hardware, y qué evidencia pública hay de su velocidad en el runtime/plataforma concretos?
4. **¿Cuánta incertidumbre hay?** Diferenciar una puntuación/ranking de modelo en AA, un throughput de proveedor/servicio en AA y un benchmark de inferencia local publicado por terceros: son medidas distintas y no intercambiables.

### Selección de modelos: Artificial Analysis como referencia de calidad/capacidad

- Consultar las páginas y tablas públicas actuales de Artificial Analysis para identificar modelos líderes, usando el índice o ranking pertinente a la tarea (p. ej., Intelligence Index y, cuando proceda, coding/agentic u otras categorías publicadas).
- No elegir un modelo solo por su puesto global: conservar nombre y versión exactos, categoría/índice, fecha de consulta, contexto, modalidad, licencia cuando esté publicada y cualquier configuración relevante.
- Aplicar después un filtro de viabilidad por plataforma: memoria física realmente utilizable (no contar swap como RAM), tamaño del modelo/archivo y cuantización disponible, arquitectura soportada por el runtime, formatos, backend, límites de contexto y evidencia pública de ejecución.
- El resultado debe presentar el **mejor modelo elegible documentado por plataforma**, no afirmar que es el mejor modelo absoluto si no hay evidencia de que sea ejecutable en esa plataforma.
- Si AA no publica velocidad para la combinación exacta modelo + hardware + runtime, marcarla como **“sin dato comparable”**. No convertir throughput de API/cloud en velocidad local ni inferir tokens/s a partir de TOPS, ancho de banda o número de parámetros.
- Mantener por separado el modelo líder por calidad AA y el modelo con throughput local publicado. Si son distintos, explicar el compromiso; no ocultar la diferencia para producir una clasificación artificial.

### Fuentes públicas admisibles y trazabilidad

Prioridad recomendada:
1. Artificial Analysis: páginas de modelos, rankings/índices y benchmarks de velocidad cuando sean accesibles públicamente.
2. Fabricantes: especificaciones, precios oficiales, límites de potencia y documentación de software.
3. Repositorios primarios de runtimes y sus issues/releases, con commit o versión identificable.
4. Benchmarks públicos de terceros con configuración, modelo/quant, hardware y métricas suficientemente detallados.
5. Distribuidores para precio actual del SKU exacto, stock, IVA y envío; conservar URL y fecha de consulta.

Cada fila de evidencia debe registrar como mínimo: URL, título/autor, fecha de publicación o consulta, hardware/SKU, modelo y revisión, cuantización, runtime/versión/commit, backend, contexto y tipo de workload, definición de tokens/s (prefill o decode), potencia si se publica, precio/IVA/envío, moneda y estado **PUBLISHED** o **ESTIMATED**. Si faltan datos esenciales, no ocultarlos: usar “no publicado” o “no comparable”.

### Métricas de comparación

**A. Rendimiento publicado**
- Métrica primaria de generación: **decode/output tokens/s**, con contexto y longitud de salida indicados.
- Mantener **prefill tokens/s**, TTFT, latencia, contexto máximo y consumo como columnas independientes; no mezclarlos con decode.
- Para cifras de rangos o varias pruebas, conservar rango/mediana y condiciones originales; no elegir el máximo aislado sin explicarlo.

**B. Coste de hardware por rendimiento**
- **EUR por token/s = coste total de adquisición documentado (EUR) ÷ decode tokens/s publicados.**
- **Tokens/s por 1.000 € = decode tokens/s publicados ÷ (coste total EUR / 1.000).**
- Si solo se conoce MSRP en USD o el precio no incluye IVA/envío, mostrarlo como escenario separado y no etiquetarlo como coste final entregado en España.
- El numerador debe incluir el mismo alcance de sistema para todas las opciones: placa/kit completo, fuente, refrigeración/carcasa y almacenamiento imprescindible; identificar por separado cualquier componente ya incluido.
- No mezclar precios de módulo suelto con kit completo. Registrar fecha de consulta, IVA, envío, stock y garantía.
- Esta métrica es **coste de capital por throughput publicado**, no coste operativo por token ni coste energético. Sin potencia y energía verificables, tokens/J, tokens/kWh y coste eléctrico se marcan como “no disponible”; no se estiman a partir del TDP.

**C. Dos vistas que nunca se deben colapsar**
1. **Comparativa de mejor modelo elegible por plataforma:** calidad/capacidad según AA + velocidad local publicada para ese modelo si existe.
2. **Comparativa de mejor throughput local publicado por plataforma:** modelo/runtime/configuración exactos del benchmark público, aunque el modelo no sea el líder de AA.
No calcular una única puntuación agregada entre inteligencia, tokens/s, memoria y precio sin una fórmula explícita y una justificación. Si las pruebas usan contextos, cuantizaciones o runtimes diferentes, etiquetar el cociente coste/rendimiento como **orientativo/no normalizado**.

### Incertidumbre y reglas anti-inferencia

- **PUBLISHED:** cifra publicada por fuente externa; no implica reproducción ni verificación independiente por LEONES.
- **ESTIMATED:** cálculo transparente con entradas citadas; incluir fórmula, supuestos y sensibilidad.
- **NO DATA / NOT COMPARABLE:** falta una medición o las condiciones difieren materialmente.
- **MEASURED BY LEONES:** no utilizar en este informe, dado que no habrá pruebas físicas.
- No extrapolar un benchmark de 1.5B a 30–35B, un resultado de CPU a Vulkan/CUDA, un modelo podado a su versión completa, ni un resultado cloud a inferencia local.
- No usar TOPS, GB/s de memoria o especificaciones máximas de fabricante como sustituto de tokens/s publicados.
- No afirmar soporte de modelo/runtime/backend sin fuente pública concreta.
- Si no existe velocidad pública para la pareja exacta hardware/modelo, la respuesta correcta es señalar la brecha de evidencia; no inventar una cifra ni ejecutar una prueba física.

### Entregables finales

- Tabla de mejores modelos elegibles según Artificial Analysis por plataforma, con la fecha y categoría AA.
- Tabla de throughput local público (decode y prefill separados) con modelo/runtime/condiciones exactas.
- Tabla de precio del sistema completo y procedencia de la cotización.
- Ranking de **EUR por token/s** y **tokens/s por 1.000 €**, solo para filas con precio y throughput razonablemente comparables.
- Análisis de sensibilidad: precio de referencia frente a precio europeo con IVA; y, cuando haya varios benchmarks comparables, rango de rendimiento en lugar de un único valor.
- Lista explícita de brechas de evidencia. No se debe recomendar compra basándose únicamente en una estimación no verificada.

## 0.1 Primera extracción de Artificial Analysis y normalización pública (consulta: 24-10-2026)

Esta sección fija una primera instantánea pública; los rankings, precios y benchmarks cambian. Volver a consultar las fuentes antes de una decisión de compra.

### Modelos candidatos según Artificial Analysis

| Modelo | Artificial Analysis Intelligence Index | Velocidad AA publicada | Memoria/formato local conocido | Lectura para este estudio |
|---|---:|---:|---|---|
| [Qwen3.8 27B (Xhigh)](https://artificialanalysis.ai/models/qwen3-8-27b) | 34 | 45,2 output tok/s, medidos en API de Alibaba | 27B; pesos abiertos; Apache 2.0; contexto publicado de ~256K | Candidato principal de calidad dentro de la clase pequeña (≤40B) según la página AA consultada. Los 45,2 tok/s son de API, no de O6 ni Jetson. |
| [Qwen3.6 35B A3B (Reasoning)](https://artificialanalysis.ai/models/qwen3-6-35b-a3b) | 19 | 129,4 output tok/s, según API de Alibaba en la página consultada | 36B totales / 3B activos; Apache 2.0; contexto 262K | Candidato MoE de mayor tamaño activo razonable para estudiar en sistemas con 64 GB; su throughput de API no es una predicción de rendimiento local. |
| [Qwen3.6 35B A3B GGUF](https://huggingface.co/Infatoshi/Qwen3.6-35B-A3B-GGUF) | Hereda la familia del modelo; no es un ranking distinto | El repositorio publica 153,9 decode tok/s Q4_K_M en RTX 3090 y llama.cpp; prefill 329,7 tok/s | Archivo Q4_K_M listado en ~20–21,2 GB según página/artefacto | Evidencia de que existe una conversión GGUF y un benchmark local en GPU de sobremesa. No transferir esa velocidad a ARM/Orin/O6. |
| [Qwen3.5 35B A3B](https://artificialanalysis.ai/models/qwen3-5-35b-a3b) | 19 estimado en la ficha consultada; ficha marcada obsoleta por AA | La ficha histórica publica ~147 tok/s API | 36B totales / 3B activos; Apache 2.0 | Mantener como referencia histórica, no preferirlo sobre Qwen3.6 sin justificar la versión anterior. |

Fuentes primarias de modelo y evaluación:
- Artificial Analysis, Qwen3.8 27B: https://artificialanalysis.ai/models/qwen3-8-27b
- Artificial Analysis, Qwen3.6 35B A3B: https://artificialanalysis.ai/models/qwen3-6-35b-a3b
- Artificial Analysis, comparación de variantes Qwen3.6: https://artificialanalysis.ai/models/comparisons/qwen3-6-35b-a3b-non-reasoning-vs-qwen3-6-35b-a3b
- GGUF y benchmark publicado por el repositorio de conversión: https://huggingface.co/Infatoshi/Qwen3.6-35B-A3B-GGUF
- AA advierte que las velocidades de sus fichas representan la API de primera parte o una mediana de proveedores, no una prueba local en las placas estudiadas.

**Criterio de selección provisional:** Qwen3.8 27B (Xhigh) lidera esta instantánea de AA entre los candidatos de hasta 40B aquí examinados (índice 34). Qwen3.6 35B A3B (Reasoning) se mantiene como candidato MoE de interés por sus 3B parámetros activos y por existir un GGUF público. Esto no afirma que sean los dos mejores modelos absolutos ni garantiza que todas sus funciones o cuantizaciones corran en ambas placas. La lista debe actualizarse consultando el ranking completo de AA y documentando el filtro de viabilidad.

### Coste por tokens/s: lo que se puede y no se puede calcular hoy

| Sistema / evidencia | Coste de hardware usado | Decode publicado | Cociente aritmético | Estado y limitación |
|---|---:|---:|---:|---|
| Jetson AGX Orin Developer Kit 64 GB + benchmark Strata publicado en AGX Orin 32 GB | 4.012,53 € IVA incluido (precio de RS localizado; stock/precio sujetos a checkout) | 18,6–21,6 tok/s, publicado por el fork Strata en Orin 32 GB | 185,76–215,73 €/tok/s; 4,63–5,38 tok/s por 1.000 € | **ESTIMATED, NO COMPARABLE:** el precio corresponde al kit de 64 GB y el benchmark a una máquina de 32 GB; no es una medida válida de eficiencia del mismo SKU. Solo ilustra el cálculo y queda excluido de cualquier ranking final. |
| Radxa Orion O6 64 GB + baseline oficial de llama.cpp CPU | MSRP histórico de 539 USD; precio final EUR entregado no confirmado | 36,29 ± 0,16 tok/s, tg128, con DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M | No calcular EUR/tok/s; no hay coste entregado en EUR y el modelo es 1.5B | **PUBLISHED, NO COMPARABLE** con los benchmarks MoE de 30–35B. |
| Qwen3.6 35B A3B en API de Alibaba | No aplica: coste del hardware local no identificado | 129,4 tok/s según AA | No calcular coste de hardware/tok/s | **PUBLISHED/API**, no velocidad local ni numerador válido para coste de hardware. |
| Qwen3.6 35B A3B Q4_K_M en RTX 3090 + llama.cpp | Precio del sistema no recogido en la fuente de benchmark | 153,9 decode tok/s (benchmark de repositorio) | No calcular hasta tener precio de sistema equivalente y ficha completa del test | **PUBLISHED/THIRD-PARTY**; GPU de sobremesa distinta de las plataformas ARM objetivo. |

Cálculos ilustrativos del primer renglón:
- 4.012,53 € ÷ 21,6 tok/s = 185,76 €/tok/s.
- 4.012,53 € ÷ 18,6 tok/s = 215,73 €/tok/s.
- 21,6 ÷ (4.012,53 / 1.000) = 5,38 tok/s por 1.000 €.
- 18,6 ÷ (4.012,53 / 1.000) = 4,63 tok/s por 1.000 €.

Aunque las operaciones son correctas, la comparación cruza SKU de 64 GB con mediciones de 32 GB. **No utilizar esos valores para declarar ganador ni eficiencia real.** Para un ranking válido se requiere una fuente pública que mida el mismo SKU o una combinación claramente equivalente, con modelo/runtime/configuración documentados, y precio completo del sistema correspondiente.

## 0.2 Experiencias comunitarias: repositorios, issues y benchmarks públicos (consulta: 24-10-2026)

Esta sección amplía el estudio con experiencias de personas que ya intentaron ejecutar modelos localmente en placas ARM, sistemas de memoria compartida y equipos de recursos limitados. Se priorizan repositorios con instrucciones, configuraciones y números concretos. Son resultados publicados por terceros; no se han reproducido por LEONES.

### Hallazgos principales

| Plataforma / proyecto | Experiencia pública | Datos publicados | Qué demuestra y qué no |
|---|---|---|---|
| **Radxa Orion O6 64 GB — llama.cpp CPU** | [Hilo de Radxa Community: llama.cpp benchmarks](https://forum.radxa.com/t/llama-cpp-benchmarks/27813) | Qwen3 MoE ~30,53B, Q4_K, CPU, 7 hilos: **pp512 45,76 ± 0,85 tok/s; tg128 13,79 ± 0,75 tok/s**. Otro usuario publicó Q4_1 con 8 hilos: pp512 30,97 y tg128 20,30 tok/s. | Evidencia directa de un MoE de ~30B en O6 CPU. Las dos filas no son comparables entre sí: cuantización, build y configuración diferentes. |
| **Radxa Orion O6 — KleidiAI/Vulkan** | Mismo hilo comunitario | El autor informa que KleidiAI redujo la generación de Qwen3 A3B:30B Q4_K_M a unos **12 tok/s**; Vulkan compiló pero se congeló o fue extremadamente lento durante prefill/generación. | Alerta práctica: activar un backend no garantiza aceleración. El resultado negativo de Vulkan es una experiencia de ese build/fecha, no prueba de que todas las versiones futuras fallen. |
| **Radxa Orion O6 64 GB — Ollama CPU** | [Experiencia y benchmarks de usuario en Reddit](https://www.reddit.com/r/ollama/comments/1q33op3/radxa_orion_o6_llm_benchmarks_ollama_debian_12/) | Qwen3-Next: **2,41 eval tok/s**; Nemotron-3-nano: **6,04 eval tok/s**. Sistema headless, Ollama CPU-only; el autor destaca refrigeración y airflow. | Evidencia complementaria de ejecución real, pero los modelos, runtime y configuración no coinciden con llama-bench. El resultado de Qwen3-Next no debe mezclarse con el benchmark de Qwen3 A3B:30B. |
| **Radxa Orion O6 — benchmark oficial** | [Guía de Arm Learning Paths para ERNIE-4.5 MoE en O6](https://learn.arm.com/learning-paths/cross-platform/ernie_moe_v9/2_llamacpp_installation/) | Procedimiento para instalar llama.cpp, descargar GGUF Q4 y validar inferencia en la placa. | Guía técnica de instalación/validación; no la contamos como benchmark de throughput hasta que haya resultados numéricos comparables. |
| **Jetson AGX Orin 32 GB — Strata ARM64/CUDA** | [Repositorio y resultados del port](https://github.com/calvinvette/strata-inference-orin) | Qwen3.8-Flash-Next Coder IQ1_M: decode mediano **18,6–21,6 tok/s**; prefill **37,8–52,5 tok/s** en prompts de 172–1069 tokens. Con contexto 262K: prefill 58,5 tok/s y decode 6,6 tok/s. | Es la evidencia ARM64/CUDA más detallada encontrada para MoE muy grande con expertos respaldados por archivos. La variante Coder tiene expertos podados; el contexto y el tamaño de respuesta cambian mucho la velocidad. Ya se detalla en §2. |
| **Radxa O6 + GPU discreta PCIe** | [Proyecto de benchmarks de James Geerling](https://github.com/geerlingguy/ai-benchmarks) | En una configuración O6 16 GB + RTX 3080 Ti, DeepSeek R1 14B aparece con **64,58 eval tok/s**; O6 CPU sin GPU discreta aparece con **4,33 eval tok/s** en ese conjunto de resultados. | Demuestra que el sistema completo con GPU discreta puede cambiar radicalmente el rendimiento; no se puede extrapolar al O6 solo. |

## 0.3 Fuentes en chino y plataformas de China continental, Hong Kong y Taiwán (consulta: 24-10-2026)

Se amplió la búsqueda más allá de Reddit y los repositorios anglófonos. Se revisaron páginas en chino y resultados públicos de GitHub, ModelScope, Seeed Wiki, CSDN, Zhihu, Bilibili, Gitee, PTT, Mobile01 y LIHKG. La lengua de una publicación no demuestra la ubicación del autor: por eso las fuentes siguientes se clasifican por plataforma/idioma, no por nacionalidad atribuida.

### Evidencia nueva incorporable

| Fuente pública | Plataforma / ámbito | Información relevante | Uso y limitaciones |
|---|---|---|---|
| [Jetson-LlamaCpp-TensorRT-Benchmark](https://github.com/studynan/Jetson-LlamaCpp-TensorRT-Benchmark) | Repositorio público con documentación en chino | Publica una matriz de **252 puntos / 18 configuraciones** en Jetson AGX Orin 64 GB, JetPack 6.1, CUDA 12.6 y TensorRT 10.3; compara llama.cpp y TensorRT Edge-LLM con Qwen3-VL 2B/4B/8B. Incluye scripts, resultados, parches y protocolo. En una prueba de una imagen a 448 px, la tabla de generación publica llama.cpp Q4_0: 60,24 / 32,99 / 22,93 tok/s para 2B/4B/8B; Q4_K_M: 52,32 / 26,66 / 18,05 tok/s. | **PUBLISHED, evidencia detallada** para VLM y esa carga multimodal. No es texto-only ni MoE de 30–35B; no comparar directamente con resultados de O6 CPU o con Qwen texto-only. La guía señala límites de memoria unificada y fija prompt, imágenes, cuantización y concurrencia. |
| [Seeed Studio — guía china Jetson-Claw para Orin Nano/NX 8 GB](https://wiki.seeedstudio.com/cn/getting_started_with_jetson_claw_on_orin_nano_nx_8gb/) y [fuente editable en GitHub](https://github.com/Seeed-Studio/wiki-documents/blob/docusaurus-version/sites/zh-CN/docs/Edge/NVIDIA_Jetson/Application/Physical_AI/cn_Getting_Started_with_Jetson_Claw_on_Orin_Nano_NX_8GB.md) | Documentación técnica en chino de un proveedor de hardware | Describe despliegue local con CUDA + llama.cpp + Qwen3.5-4B GGUF, llama-server, contexto configurable, offload a GPU y swap como recurso auxiliar; integra nanobot con Feishu. | **Receta de despliegue**, no un benchmark cuantitativo normalizado. La propia guía advierte que si la respuesta va lenta conviene reducir contexto/concurrencia o usar un modelo menor. Swap no debe contabilizarse como RAM física disponible ni como prueba de buen rendimiento interactivo. |
| [Qwen3.5 on Jetson Orin NX — llama.cpp](https://github.com/taeyoun811/qwen3.5-jetson) | Repositorio público con README en inglés; añadido como evidencia técnica adicional, no atribuido a una región | Orin NX 16 GB, CUDA 12.6, llama.cpp con commit 2850bc6, Q4_K_M y offload GPU completo: Qwen3.5 2B/4B/9B publica 23,3 / 11,5 / 8,5 tok/s en texto; 24,3 / 11,5 / 8,2 tok/s en VL. Incluye scripts y JSON de resultados. | **PUBLISHED**, útil como punto de referencia reproducible para modelos pequeños. El 9B-VL puede agotar memoria; no es evidencia de ejecución de MoE 30B. Se conserva por complementar las fuentes en chino con un repositorio estructurado. |
| [ModelScope — Qwen3-VL-32B-Instruct](https://modelscope.cn/models/Qwen/Qwen3-VL-32B-Instruct) y [Qwen3-VL-8B-Instruct](https://modelscope.cn/models/Qwen/Qwen3-VL-8B-Instruct) | Hub de modelos usado ampliamente en China continental | Páginas de modelos, metadatos, pesos y distribución de artefactos. El benchmark chino anterior documenta descarga de pesos desde ModelScope y propone comprobar SHA-256 frente a Hugging Face. | **Fuente de artefactos y metadatos, no evidencia de velocidad por sí sola.** No convertir descargas, popularidad ni tamaño del modelo en tokens/s. |
| [Radxa Community — benchmarks de llama.cpp para Orion O6](https://forum.radxa.com/t/llama-cpp-benchmarks/27813/17) | Foro de fabricante, discusión internacional con aportaciones en inglés | Una respuesta informa de una Radeon RX 7900 XTX externa por Vulkan: Qwen3-30B-A3B Q4_K, pp512 1.698,22 tok/s y tg128 57,64 tok/s; la misma aportación da CPU 8 hilos pp512 27,44 y tg128 16,84 tok/s. | La GPU externa cambia por completo el sistema: esos 57,64 tok/s **no corresponden al O6 integrado**. Los 16,84 tok/s son un resultado de esa build/configuración, no deben sustituir los otros resultados CPU del hilo sin conciliar cuantización y condiciones. |

### Cobertura de Hong Kong y Taiwán: resultado negativo documentado

En esta consulta no apareció, dentro de los resultados públicos recuperables, una publicación de PTT, Mobile01 o LIHKG con un benchmark controlado que añadiera una cifra comparable de decode para Radxa Orion O6 o Jetson Orin ejecutando un MoE de 30–35B. Esto **no prueba que no existan**; significa que no se encontró evidencia que cumpliera el umbral del informe. Se dejan enlaces de búsqueda para futuras revisiones, en vez de inventar hallazgos:

- Taiwán — [PTT: Jetson Orin + LLM](https://www.google.com/search?q=site%3Aptt.cc+%22Jetson+Orin%22+LLM), [Mobile01: Jetson Orin + LLM](https://www.google.com/search?q=site%3Amobile01.com+%22Jetson+Orin%22+LLM), [GitHub: Orin / Qwen / benchmark](https://github.com/search?q=Jetson+Orin+Qwen+benchmark&type=repositories).
- Hong Kong — [LIHKG: Jetson Orin + LLM](https://www.google.com/search?q=site%3Alihkg.com+%22Jetson+Orin%22+LLM). La búsqueda web no proporcionó un hilo LIHKG verificable que cumpliera los criterios.
- China continental — [Zhihu: Orion O6 + 大模型](https://www.google.com/search?q=site%3Azhihu.com+%22Orion+O6%22+%E5%A4%A7%E6%A8%A1%E5%9E%8B), [Bilibili: Orion O6 + llama.cpp](https://www.google.com/search?q=site%3Abilibili.com+%22Orion+O6%22+llama.cpp), [CSDN: Jetson Orin + Qwen3-VL](https://www.google.com/search?q=site%3Acsdn.net+%22Jetson+Orin%22+%22Qwen3-VL%22), [Gitee: llama.cpp + Orin](https://gitee.com/search?utf8=%E2%9C%93&q=llama.cpp+Orin&type=repository).

**Regla de admisión para futuras revisiones:** vídeos, hilos y publicaciones sociales pueden servir como pista, pero solo se añadirán a la tabla de rendimiento si revelan SKU/RAM, modelo y archivo/quant exactos, runtime/backend/versión, contexto y longitud de salida, método de medición y una cifra explícita de decode. Si faltan varios datos, registrar el enlace como pista comunitaria con nivel de evidencia B/C, y no usarlo para ordenar coste/rendimiento. En páginas de vídeo, citar el minuto o la tabla concreta cuando esté disponible.

### Búsquedas permanentes y portales que se deben volver a consultar

- **China continental:** [ModelScope](https://modelscope.cn/), [Gitee](https://gitee.com/), [GitCode](https://gitcode.com/), [CSDN](https://www.csdn.net/), [Zhihu](https://www.zhihu.com/), [Bilibili](https://www.bilibili.com/), [百度贴吧](https://tieba.baidu.com/).
- **Hong Kong:** [LIHKG](https://lihkg.com/), además de repositorios públicos y foros de hardware; comprobar si el enlace es accesible sin sesión antes de citarlo.
- **Taiwán:** [PTT](https://www.ptt.cc/), [Mobile01](https://www.mobile01.com/), [巴哈姆特](https://forum.gamer.com.tw/), además de GitHub y documentación de fabricantes.
- **Fuentes regionales transversales:** [Seeed Studio Wiki en chino](https://wiki.seeedstudio.com/cn/), [Arm Learning Paths](https://learn.arm.com/), [NVIDIA Developer Forums](https://forums.developer.nvidia.com/) y [Radxa Forum](https://forum.radxa.com/).

La cobertura regional se debe volver a ejecutar en chino simplificado y tradicional (por ejemplo, 本地大模型, 推理速度, 每秒 token, 统一内存, Orin NX, Orion O6, 混合专家, 量化, llama.cpp, Qwen3 A3B), además de los términos ingleses. Mantener separados el origen geográfico demostrado, el idioma de publicación y el país del hosting: no inferir la procedencia de un autor a partir de su nombre o idioma.

---

## 1. Plataformas evaluadas (reintroducido del histórico)

### 1.1 Radxa Orion O6 (CIX P1)

Fuentes oficiales:
- Producto: https://radxa.com/products/orion/o6/
- Documentación: https://docs.radxa.com/en/orion/o6
- PDF con precio minorista oficial: https://dl.radxa.com/orion/o6/radxa_orion_o6_announcement_presentation_2024_12_18.pdf

Especificaciones confirmadas:
- SoC CIX P1 ARMv9.2, 12 núcleos (4×A720 2.6 GHz + 4×A720 2.4 GHz + 4×A520 1.8 GHz)
- GPU Arm Immortals G720 MC10 (Vulkan 1.3 / OpenCL 2.2)
- NPU Zhouyi anunciada 30 TOPS (no diseñada para decode autoregresivo de LLM)
- 64 GB LPDDR5, bus 128-bit, hasta ~100 GB/s
- PCIe Gen4 x8 físico + M.2 NVMe
- Precio MSRP histórico 64 GB: **539 USD** (no precio final España)

### 1.2 NVIDIA Jetson AGX Orin

- AGX Orin 32/64 GB, CPU Cortex-A78AE + GPU Ampere, LPDDR5 compartida
- Developer Kit 64 GB MSRP oficial: **3.499 USD**
- Evidencia real: fork Strata en 32 GB con decode 18,6–21,6 tok/s (Qwen3.8-Flash-Next Coder)

### 1.3 Alternativas de más memoria

| Plataforma | RAM física compartida | Estado para esta investigación | Uso recomendado |
|---|---:|---|---|
| Radxa Orion O6 | Hasta 64 GB LPDDR5 | Especificaciones oficiales; benchmark LLM grande comparable no encontrado | Opción abierta para evaluar CPU/Vulkan y PCIe |
| Jetson AGX Orin | 32/64 GB según kit/módulo | Hay fork ARM64/CUDA con mediciones reales de 32 GB | Referencia para motor especializado y offload |
| Jetson Orin NX | 8/16 GB según SKU | CUDA maduro, memoria demasiado pequeña para varios MoE de 30B sin descarga agresiva | Modelos pequeños, visión y nodo de control |
| AMD Strix Halo / Ryzen AI Max+ | 128–192 GB UMA | Ecosistema 2026 muy activo (multi-slot, Vulkan/ROCm) | Referencia de alto throughput en memoria unificada |
| Apple Silicon | Configuración dependiente del equipo | Memoria unificada madura, plataforma cerrada | Referencia de experiencia de usuario y rendimiento, no hardware abierto |

## 2. Evidencia reproducible: Strata en Jetson AGX Orin (reintroducido)

Repositorio: https://github.com/calvinvette/strata-inference-orin  

Resultados publicados (PUBLISHED, no medidos por LEONES):
- Hardware: Jetson AGX Orin 32 GB, JetPack 6.2, CUDA 12.6, MAXN
- Modelo: Qwen3.8-Flash-Next Coder IQ1_M, expertos a fichero, MTP speculative
- Decode mediana: **18,6–21,6 tok/s** (respuestas 64 tokens)
- Prefill: **37,8–52,5 tok/s** (prompts 172–1069 tokens)
- Contexto 262K: decode cae a ~6,6 tok/s
- RAM disponible mínima reportada ~7–9 GiB (con swap)

Interpretación: evidencia sólida de que un MoE cuantizado agresivamente puede ejecutarse en Orin compartiendo RAM. No generalizable a cualquier 30–35B ni a potencia limitada.

## 3. Controladores y backends: matriz de compatibilidad (reintroducido)

| Plataforma / backend | Estado documental | Qué queda por verificar |
|---|---|---|
| Jetson Orin + CUDA + Strata ARM64 | Evidencia publicada en AGX Orin 32 GB | Repetición independiente, potencia limitada, modelos completos |
| Jetson Orin + llama.cpp CUDA + GGUF | Vía ampliamente disponible | Compilar versión fijada, capas GPU, KV cache, MoE |
| Orion O6 + llama.cpp CPU | Punto de partida razonable | Build limpio, kernels ARM, estabilidad |
| Orion O6 + llama.cpp Vulkan | GPU anuncia Vulkan 1.3 | `vulkaninfo`, backend compilado, operaciones soportadas vs CPU |
| Orion O6 + NPU Zhouyi | NPU 30 TOPS con SDK | No asumir GGUF ni decode autoregresivo (confirmado por CIX) |
| Orion O6 + GPU PCIe externa | Ranura PCIe Gen4 x8 física | IOMMU, driver ARM64, alimentación, CUDA/ROCm |

## 4. Coste total de propiedad (TCO) y escala de precios por Tiers (reintroducido + ampliado)

### Escala de precios por Tiers (EUR, orientativa, sistema completo)

| Tier | Rango de precio | Opciones típicas en este rango | Notas |
|---|---|---|---|
| **Tier 0** | ≤ 1.000 € | Radxa Orion O6 32/64 GB (MSRP histórico ~500–600 USD + IVA/envío) + NVMe + fuente | Mejor relación RAM unificada / precio de investigación abierta. Precio final España no confirmado. |
| **Tier 1** | 1.000 – 2.000 € | O6 64 GB + accesorios premium / refrigeración / NVMe grande; o Jetson Orin NX sistemas | Ampliación de O6 o entrada Jetson de menor memoria. |
| **Tier 2** | 2.000 – 3.000 € | Sistemas Jetson Orin de producción + carrier; o mini-PCs con Ryzen AI de gama media | Transición a CUDA maduro o AMD UMA. |
| **Tier 3** | 3.000 – 4.000 € | Jetson AGX Orin Developer Kit 64 GB (MSRP 3.499 USD + IVA/envío ~4.000 €) | Referencia CUDA ARM de mayor memoria. |
| **Tier 4** | 4.000 – 5.000 € | AGX Orin 64 GB con accesorios / refrigeración / NVMe de alta capacidad | Coste realista de sistema listo. |
| **Tier 5** | 5.000 – 6.000 € | Sistemas integrados Orin o primeras configuraciones Strix Halo de entrada | |
| **Tier 6** | 6.000 – 7.000 € | Mini-PCs / workstations con Ryzen AI Max+ 128 GB | |
| **Tier 7** | 7.000 – 8.000 € | Configuraciones Strix Halo / Gorgon Halo de gama media | |
| **Tier 8** | 8.000 – 9.000 € | Sistemas de 128–192 GB UMA bien equipados | |
| **Tier 9** | 9.000 – 10.000 € | Workstations de alto ancho de banda con 192 GB UMA + almacenamiento | |
| **Tier 10+** | > 10.000 € | Clusters, DGX Spark / GB10 class, o configuraciones enterprise | Fuera del alcance principal de este estudio. |

**Advertencia:** Los rangos son orientativos y se basan en MSRP + estimaciones de IVA/envío. Toda decisión de compra requiere cotización actual con stock, IVA, envío y garantía.

### 4.1 Radxa Orion O6 64 GB – presupuesto orientativo

- MSRP histórico 64 GB: 539 USD
- IVA + transporte + posible aduana: pendientes de cotización
- NVMe 1–2 TB + fuente ≥65 W: añadir según oferta
- **Total final España: NO VERIFICADO**

### 4.2 Jetson AGX Orin Developer Kit 64 GB

- MSRP oficial: 3.499 USD
- Cotización europea reciente orientativa ~4.000 €+ (verificar stock)
- **Total final España: NO VERIFICADO** hasta oferta concreta

## 5. Plan de benchmark reproducible (resumen del histórico)

Fase A — Validar máquina y drivers (uname, lscpu, free, vulkaninfo, tegrastats, vatímetro).
Fase B — Baseline CPU → Vulkan (O6) → CUDA (Jetson) con misma revisión de llama.cpp.
Fase C — MoE (Qwen3-30B-A3B / 35B-A3B GGUF), mismo quant, contexto 4K→8K, registrar OOM, swap, offload de expertos.

Todas las cifras futuras de LEONES se etiquetarán MEASURED solo si se ejecutan físicamente (fuera del alcance actual).

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

*Informe actualizado el 24 de octubre de 2026. Se han reintroducido las tablas históricas de plataformas, backends, TCO y la nueva escala de precios por Tiers, junto con la sección exhaustiva 7 de experiencias en repositorios públicos. Todos los datos de rendimiento son PUBLISHED por terceros; no han sido reproducidos por LEONES.*
