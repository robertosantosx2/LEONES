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
| **Radxa O6 + GPU discreta PCIe** | [Proyecto de benchmarks de James Geerling](https://github.com/geerlingguy/ai-benchmarks) | En una configuración O6 16 GB + RTX 3080 Ti, DeepSeek R1 14B aparece con **64,58 eval tok/s**; O6 CPU sin GPU discreta aparece con **4,33 eval tok/s** en ese conjunto de resultados. | Demuestra que el sistema completo con GPU discreta puede cambiar radicalmente el rendimiento; esos 64,58 tok/s son de la RTX 3080 Ti, no de la GPU integrada O6. No comparar como si fuese la misma configuración. |
| **O6 CPU y O6 + RTX 3060** | [eullm/eullm: resultados y matriz de plataformas](https://github.com/eullm/eullm) | El proyecto informa **9–11 tok/s** para Qwen3.6-35B-A3B en O6 CPU y **35,6 tok/s** para el mismo modelo en O6 con RTX 3060; también informa Qwen3-14B a 33 tok/s en la configuración con GPU. | Resultado comunitario potencialmente muy relevante para coste/rendimiento con expansión PCIe. Antes de usarlo en un ranking hay que recuperar la ficha de benchmark completa: quant exacta, runtime, versión, contexto, tokens generados y SKU/precio del conjunto. |
| **Radxa ROCK 5B+ / RK3588** | [llamacpp-workbench y documentación de benchmarks](https://github.com/SergiioB/llamacpp-workbench) | El proyecto describe pruebas de Qwen3.5-2B/4B/9B y modelos MoE podados como GLM-4.7-Flash-REAP-23B-A3B en ROCK 5B+ con ~24 GiB. Incluye presets de afinidad, hilos, KV cache y contexto. | No es la misma SoC que O6 ni Orin, pero sí una fuente práctica para estudiar inferencia ARM con memoria limitada y MoE podados. No transferir sus tokens/s a otras placas. |
| **Jetson Orin Nano Super** | [llm-in-c: implementaciones por chip/modelo](https://github.com/baryhuang/llm-in-c) | Registra Qwen3.8-27B IQ1_S mediante llama.cpp/CUDA parcheado; las interacciones anotadas tardaron **114–156 segundos**, con uso considerable de swap. | Prueba de que “arranca” no equivale a uso interactivo rápido. La ficha consultada no proporciona una cifra de decode directamente comparable con las demás filas. |
| **Comparación comunitaria amplia** | [Token Atlas](https://tokatlas.github.io/) | Dataset consultado el 22-10-2026: declara 41.103 registros, 733 modelos, 444 equipos y 45 backends, con enlaces a fuentes por registro. | Índice útil para seguir buscando combinaciones modelo/quant/chip/runtime y verificar atribución. No tratar el agregado como una única prueba normalizada; inspeccionar el enlace y la configuración de cada registro. |
| **Protocolo reproducible para nuevos aportes** | [Compute:Arena — artículo de Hugging Face](https://huggingface.co/blog/basecompute/local-inference-benchmarks-computearena) y [Compute:Arena](https://computearena.ai/) | Propone sweeps de prefill de 128–16.384 tokens y decode de 128 tokens, warmup y tres repeticiones; registra hashes del modelo/runtime y telemetría de memoria, swap, temperatura y potencia. | Referencia metodológica para evaluar la calidad de futuros resultados públicos. Los números solo son comparables cuando coinciden workload, modelo/quant y configuración, y aun así hay que respetar las diferencias entre runtimes. |

### Lectura crítica de la experiencia comunitaria

1. **O6 sí tiene evidencia pública de MoE ~30B en CPU**: la cifra más útil localizada en el foro es 13,79 ± 0,75 tok/s de generación con Qwen3 MoE Q4_K y 7 hilos; otro build/configuración publica 20,30 tok/s con Q4_1 y 8 hilos. La diferencia subraya que cuantización, kernels, build y configuración importan. No debe presentarse una sola cifra como “la velocidad del O6”.
2. **No se ha encontrado una prueba válida de que la GPU integrada del O6 acelere actualmente esos MoE mediante Vulkan**. En el hilo, la experiencia publicada fue negativa para una versión concreta. La existencia de Vulkan 1.3 en la especificación no reemplaza una prueba del backend y del modelo.
3. **La memoria unificada no elimina el cuello de botella de ancho de banda ni el coste de mover expertos**. Los usuarios describen velocidades modestas en CPU para MoE grandes, y resultados muy distintos al instalar una GPU discreta. Separar siempre placa sola, placa + GPU, memoria del sistema y VRAM dedicada.
4. **Orin tiene evidencia más profunda para offload experto con CUDA**, pero el benchmark más fuerte localizado usa Qwen3.8-Flash-Next Coder IQ1_M, expertos en archivos, MTP=4 y contextos largos; no equivale a un Qwen 30–35B completo Q4.
5. **Los proyectos que comparten números sin configuración completa sirven como pistas, no como base para el cociente coste/rendimiento**. Por ejemplo, los 9–11 tok/s de eullm en O6 y 35,6 tok/s con RTX 3060 quedan en la lista de candidatos para verificar, no entran en el ranking hasta disponer de la receta exacta y un coste total equivalente.
6. **Codeberg y otros forges**: la búsqueda web directa de Codeberg no devolvió contenido accesible en esta consulta. No se interpreta esa limitación como ausencia de proyectos; esta instantánea prioriza enlaces públicos verificables de GitHub, Hugging Face, foros de Radxa y Reddit.

### Nuevas fuentes que conviene seguir

- Foro de Radxa, hilo completo y respuestas con builds/quant alternativos: https://forum.radxa.com/t/llama-cpp-benchmarks/27813
- Resultados de usuarios de O6 con Ollama: https://www.reddit.com/r/ollama/comments/1q33op3/radxa_orion_o6_llm_benchmarks_ollama_debian_12/
- Índice de benchmarks por modelo y hardware: https://tokatlas.github.io/
- Protocolo de medición abierta: https://computearena.ai/
- Experiencias de inferencia en ARM integrado/RK3588: https://github.com/SergiioB/llamacpp-workbench
- MoE en Jetson Orin: https://github.com/calvinvette/strata-inference-orin
- O6 CPU y O6 + GPU PCIe en el proyecto eullm: https://github.com/eullm/eullm
- MoE con RAM/swap en Jetson Orin Nano: https://github.com/baryhuang/llm-in-c

## 1. Plataformas evaluadas

### 1.1 Radxa Orion O6 (CIX P1)

Fuentes oficiales:
- Producto y vías de compra: https://radxa.com/products/orion/o6/
- Documentación: https://docs.radxa.com/en/orion/o6
- Especificación de bajo nivel: https://docs.radxa.com/en/orion/o6/low-level-dev
- PDF con precio minorista oficial publicado: https://dl.radxa.com/orion/o6/radxa_orion_o6_announcement_presentation_2024_12_18.pdf
- Proyecto comunitario de kernel CIX P1 (O6N, relacionado pero no idéntico en validación): https://github.com/AkaseToshiyuki/cix-p1-kernel-deploy

Especificaciones confirmadas por Radxa:
- SoC CIX P1, arquitectura ARMv9.2.
- CPU de 12 núcleos: 4 Cortex-A720 de rendimiento (hasta 2,6 GHz), 4 Cortex-A720 balanceados (hasta 2,4 GHz) y 4 Cortex-A520 eficientes (hasta 1,8 GHz).
- GPU Arm Immortals G720 MC10; documentación declara Vulkan 1.3 y OpenCL 2.2.
- NPU anunciada como 30 TOPS; la página de producto promociona 45 TOPS combinados CPU/GPU/NPU. Estas cifras no son benchmarks de LLM y no demuestran que la NPU pueda ejecutar un modelo GGUF.
- RAM LPDDR5, bus de 128 bits, 5500 MT/s, hasta 64 GB; ancho de banda declarado de hasta 100 GB/s.
- Ranura PCIe x16 física con conexión PCIe Gen4 x8. No implica x16 eléctrico.
- Ranura M.2 M-key PCIe Gen4 x4 para NVMe; M.2 E-key PCIe Gen4 x2.
- Dos interfaces Ethernet de 5 GbE.
- Alimentación: entrada USB-C PD de 20 V o conector ATX de 24 pines; PSU recomendada de al menos 65 W.
- La documentación indica que el paquete suele incluir placa, disipador Radxa 8420B, caja acrílica y shield de E/S; verificar el contenido del vendedor.

**Precio de referencia, no precio final de compra:** PDF oficial publicado: 8 GB 289 USD, 16 GB 329 USD, 32 GB 389 USD, 64 GB 539 USD. Es un precio minorista oficial anunciado en 2024, no una oferta actual con stock y envío confirmados. Página oficial: https://radxa.com/products/orion/o6/ (disponibilidad mediante socios autorizados). Antes de comprar, solicitar precio final en EUR con IVA español, transporte, garantía y plazo de entrega por escrito.

#### Valor real para LLM

La ventaja de O6 es tener 64 GB de RAM física compartida para CPU/GPU, con una GPU moderna y PCIe para expansión. Es una candidata para ejecutar modelos grandes cuantizados principalmente por CPU, probar backends Vulkan y experimentar con una GPU PCIe ARM-compatible.

Riesgos y límites:
- El controlador gráfico y el soporte del SoC son más jóvenes y menos estandarizados que CUDA en Jetson.
- El soporte Vulkan/OpenCL de la GPU no demuestra por sí solo que la versión de llama.cpp que se compile detecte correctamente la GPU, que todas las operaciones estén implementadas o que el backend sea más rápido que CPU.
- La NPU de 30 TOPS es un acelerador separado con SDK, operadores y formatos propios. No se debe dar por hecho que acepta GGUF ni que llama.cpp/Strata la utilicen.
- Los TOPS son irrelevantes como predictor directo de tokens/s para un modelo MoE si el runtime no puede ejecutar sus operaciones en ese acelerador.
- **Baseline oficial de llama.cpp en CPU publicado por Radxa:** DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf, 8 hilos, pp512 = 64,60 ± 0,27 tokens/s y tg128 = 36,29 ± 0,16 tokens/s. La guía fija el commit `4aced7a` y activa ARMv9/I8MM/dotprod/KleidiAI. Esto verifica una ruta GGUF/CPU para O6; no demuestra aceleración Vulkan ni rendimiento de MoE grande. Fuente primaria: https://docs.radxa.com/en/orion/o6/app-development/artificial-intelligence/llama-cpp
- No se ha encontrado en esta revisión un benchmark público suficientemente reproducible de O6 con un MoE de 30–35B en GGUF, con logs completos de tokens/s, RAM máxima y consumo de pared. Resultado: **no verificado**.

### 1.2 NVIDIA Jetson AGX Orin 32 GB / 64 GB

Fuentes:
- Página oficial Jetson Orin: https://www.nvidia.com/es-es/autonomous-machines/embedded-systems/jetson-orin/
- FAQ/precios de NVIDIA: https://developer.nvidia.com/embedded/faq
- Fork Strata para Orin: https://github.com/calvinvette/strata-inference-orin
- Benchmarks comunitarios del fork: https://github.com/calvinvette/strata-inference-orin/blob/main/docs/COMMUNITY_BENCHMARKS.md

Características relevantes:
- AGX Orin utiliza CPU ARM Cortex-A78AE y GPU NVIDIA Ampere integrada con memoria LPDDR5 compartida.
- Según SKU, NVIDIA publica hasta 64 GB de memoria y hasta 204,8 GB/s de ancho de banda para AGX Orin de 64 GB.
- El módulo de producción AGX Orin 64 GB se anuncia con hasta 275 TOPS y rango configurable de potencia 15–60 W; no confundir ese dato de módulo con el kit de desarrollo ni con consumo de pared de todo el sistema.
- NVIDIA indica un precio de 3.499 USD para el Jetson AGX Orin Developer Kit de 64 GB y especifica que su rendimiento es el mismo que el kit de desarrollo original de 32 GB, salvo la memoria.
- Los módulos de producción se venden aparte y requieren carrier board, fuente, refrigeración y almacenamiento apropiados. Para un primer experimento es preferible un kit completo o un sistema integrado que incluya esos componentes.

**Coste total:** el precio oficial de 3.499 USD no es coste entregado en España. Añadir IVA/importación si proceden, transporte, NVMe, alimentación/cableado y posible carcasa/refrigeración. Un resultado de shopping reciente mostró un listado europeo del kit a unos 4.800 EUR, pero no se considera una oferta auditada ni necesariamente comparable; comprobar stock, SKU, IVA, envío y devolución antes de decidir. Fuente oficial para MSRP: https://developer.nvidia.com/embedded/faq

### 1.3 Alternativas de más memoria

| Plataforma | RAM física compartida | Estado para esta investigación | Uso recomendado |
|---|---:|---|---|
| Radxa Orion O6 | Hasta 64 GB LPDDR5 | Especificaciones oficiales; benchmark LLM grande comparable no encontrado | Opción abierta para evaluar CPU/Vulkan y PCIe |
| Jetson AGX Orin | 32/64 GB según kit/módulo | Hay fork ARM64/CUDA con mediciones reales de 32 GB | Referencia para motor especializado y offload |
| Jetson Orin NX | 8/16 GB según SKU | CUDA maduro, memoria demasiado pequeña para varios MoE de 30B sin descarga agresiva | Modelos pequeños, visión y nodo de control |
| AMD BC-250 | 16 GB GDDR6 | Proyecto comunitario y Vulkan; arquitectura APU no ARM | Referencia económica alternativa, no objetivo ARM |
| Apple Silicon | Configuración dependiente del equipo | Memoria unificada madura, plataforma cerrada | Referencia de experiencia de usuario y rendimiento, no hardware abierto |

## 2. Evidencia reproducible: Strata en Jetson AGX Orin

Repositorio: https://github.com/calvinvette/strata-inference-orin  
Rama del port descrita por el proyecto: `feat/jetson-orin-arm64`.

El fork deriva de Strata y añade:
- compilación ARM64 para SM87;
- kernels CPU portables y backend ARM de ggml fijado;
- presupuesto unificado de RAM física para asignaciones CPU/GPU;
- expertos respaldados por ficheros cuando no caben en RAM;
- sincronización ARM para buffers host mapeados en CUDA y alternativas de registro;
- ajustes de caché VMM;
- instalación que conserva las bibliotecas CUDA de JetPack, evitando binarios x86 o paquetes CUDA de escritorio incompatibles.

Advertencia importante: el propio proyecto indica que CPU y GPU comparten los 32 GB del AGX Orin de prueba; no son 32 GB de RAM más otros 32 GB de VRAM. El runtime deja por defecto aproximadamente 6 GiB de margen físico y reserva otros 3 GiB para espacios de trabajo tardíos al calcular la caché automática de expertos. La memoria gestionada se admite para transferencia secuencial de propiedad, pero no se reporta acceso gestionado concurrente. El proyecto mantiene asignaciones de dispositivo y buffers de control mapeados en vez de reemplazar todo por managed memory.

### Resultados publicados por el fork (no medidos por LEONES)

Configuración documentada:
- Hardware: Jetson AGX Orin 32 GB.
- Sistema: JetPack 6.2, CUDA 12.6.68.
- Modo de potencia: MAXN y relojes desbloqueados.
- Modelo: Qwen3.8-Flash-Next Coder IQ1_M, expertos respaldados por archivos, MTP speculative de 4, prefill batch 64.
- Build inicial descrito como Strata 0.1.40.3; el repo también documenta validación posterior tras rebase a 0.1.41.

Resultados del build 0.1.40.3:
- Decode: mediana de 18,6–21,6 tokens/s en tres ejecuciones por tamaño de prompt con respuestas de 64 tokens.
- Prefill: mediana de 37,8–52,5 tokens/s para prompts de 172–1069 tokens.
- Contexto largo: 31.234 tokens procesados en 584 segundos en una prueba con contexto de 32K; respuesta esperada y seguimiento superados.
- RAM física disponible mínima reportada: 7,33 GiB; había swap en uso.
- Validación API: respuestas greedy repetidas, streaming OpenAI/Anthropic y recuperación tras cancelación superados.
- Visión: validación de encoder CPU/CUDA para una imagen de 56×56 y límite de encoder de 16 tokens.

Validación posterior del rebase a 0.1.41:
- Nueve capacidades de contexto desde 1K hasta 256K completadas.
- Con contexto 262.144, prompt de 261.936 tokens procesado a 58,5 tokens/s; luego 64 tokens generados a 6,6 tokens/s.
- RAM disponible mínima: 9,33 GiB; swap en uso.
- El contexto más grande reduce la caché automática de expertos y la velocidad de decode.

Interpretación:
- Es evidencia relevante de que un MoE con cuantización agresiva puede ejecutarse en Jetson Orin compartiendo RAM con la GPU y usando offload de expertos a fichero.
- No es prueba de que cualquier modelo de 30–35B funcione igual, ni de que la velocidad sea sostenible con refrigeración pasiva o a potencia limitada.
- El modelo Coder tiene expertos eliminados respecto al modelo completo; no equivale al modelo íntegro para tareas generales.
- Las pruebas de rendimiento no sustituyen a una validación independiente de calidad, seguridad y precisión numérica.
- Las cifras publicadas deben permanecer etiquetadas **PUBLISHED / THIRD-PARTY** en LEONES.

### Instalación indicada por el proyecto

Requisitos: AGX Orin 32 GB, JetPack 6.2, CUDA 12.6 y NVMe con espacio suficiente.

```bash
git clone --branch feat/jetson-orin-arm64 https://github.com/calvinvette/strata-inference-orin.git
cd strata-inference-orin
./setup.sh --cuda 12
```

Seguir el README y `docs/AI_SETUP.md` del repositorio en la revisión exacta que se vaya a medir. No exponer el servidor fuera de localhost sin configurar API key. Para reproducibilidad, guardar SHA de commit, versión de JetPack, modelo GGUF y hashes de los artefactos.

## 3. Controladores y backends: matriz de compatibilidad

| Plataforma / backend | Estado documental | Qué queda por verificar |
|---|---|---|
| Jetson Orin + CUDA + Strata ARM64 | Evidencia publicada en AGX Orin 32 GB | Repetición independiente, potencia limitada, modelos completos y métricas de pared |
| Jetson Orin + llama.cpp CUDA + GGUF | Vía de software ampliamente disponible en ARM64/CUDA, pero el rendimiento depende de build y modelo | Compilar versión fijada, confirmar capas GPU, KV cache, MoE y memoria |
| Orion O6 + llama.cpp CPU | ARM64 CPU como punto de partida razonable | Build limpio, kernels ARM, BLAS opcional y estabilidad |
| Orion O6 + llama.cpp Vulkan | GPU anuncia Vulkan 1.3; compatibilidad del runtime no se deduce de la especificación | `vulkaninfo`, backend Vulkan compilado, operaciones soportadas y benchmark contra CPU |
| Orion O6 + OpenCL | GPU anuncia OpenCL 2.2 | Backend concreto, disponibilidad de ICD, operadores y precisión |
| Orion O6 + NPU | NPU de 30 TOPS con SDK del fabricante | Si el SDK soporta el modelo/operadores; no asumir compatibilidad GGUF ni Strata |
| Orion O6 + GPU PCIe externa | Ranura PCIe Gen4 x8 física | IOMMU, kernel/driver ARM64 de GPU, ancho de enlace negociado, alimentación y compatibilidad de CUDA/ROCm |

Fuentes de software/controladores:
- Radxa O6: https://docs.radxa.com/en/orion/o6
- CIX P1 kernel deployment (proyecto comunitario para O6N, usar como pista, no como garantía de paridad O6): https://github.com/AkaseToshiyuki/cix-p1-kernel-deploy
- Strata Orin: https://github.com/calvinvette/strata-inference-orin
- llama.cpp: https://github.com/ggml-org/llama.cpp

El script comunitario CIX P1 informa de GPU disponible como `/dev/dri/card0` y PCIe probado con una NIC RTL8125 en un O6N; marca VPU/NPU como dependientes de firmware. Esto no valida por sí solo una O6 de venta, un runtime GGUF ni aceleración LLM por NPU. La variante O6N y O6 deben mantenerse diferenciadas en la matriz.

## 4. Coste total de propiedad (TCO) y compras

### 4.1 Radxa Orion O6 64 GB

**Precio de referencia publicado:** 539 USD (MSRP oficial anunciado en PDF de 2024; no equivale a cotización actual ni incluye impuestos/envío).

Enlaces de compra / distribución (stock y precio O6 64 GB deben confirmarse en la ficha de cada vendedor):
- Página oficial del producto y socios autorizados: https://radxa.com/products/orion/o6/
- OKdo, distribuidor global que Radxa lista en su página histórica de distribuidores: https://www.okdo.com/
- Innet24 (Alemania): https://www.innet24.de/
- Maker-store (Alemania): https://shop.maker-store.de/
- Allnet España: https://www.allnet.es/ — el directorio de Radxa publica contacto de ALLNET España en Carballo (A Coruña); solicitar cotización del SKU de 64 GB.
- Directorio de distribuidores (fuente Radxa, página archivada): https://wiki.radxa.com/Buy
- Documentación y contenido del paquete: https://docs.radxa.com/en/orion/o6
- Accesorio de alimentación oficial: desde la sección de accesorios de https://radxa.com/products/orion/o6/
- Almacenamiento NVMe: elegir un SSD M.2 2280 PCIe Gen4 x4 de 1–2 TB de vendedor con stock y factura en España; la ranura está confirmada por la documentación oficial.

No se ha podido confirmar en esta revisión una ficha de venta actual del SKU O6 64 GB con precio final en EUR. Estos enlaces son rutas verificables hacia vendedores/distribuidores, no prueba de stock, precio ni plazo de entrega.

Presupuesto que debe completarse con cotización real:
- Placa O6 64 GB: 539 USD como referencia histórica, **no precio entregado**.
- IVA, transporte, posible aduana/gestión: pendientes de cotización del vendedor.
- Fuente USB-C PD 20 V ≥65 W o fuente ATX compatible: coste pendiente según opción.
- NVMe 1–2 TB: coste pendiente de oferta y capacidad elegidas.
- Cableado/adaptadores y refrigeración extra: 0 € si el paquete incluye caja/disipador y basta la fuente elegida; en caso contrario añadir coste real.
- Total final España: **NO VERIFICADO**. No sumar cifras de accesorios no consultadas ni presentar una conversión de divisa como precio final.

La compra solo se recomienda después de confirmar por escrito SKU de 64 GB, stock, contenido del paquete, IVA, envío a España, garantía y política de devolución. Si el vendedor no puede facilitar esos datos, registrar la oferta como “lead”, no como compra disponible.

### 4.2 Jetson AGX Orin

**Ofertas europeas localizadas (consulta 24-10-2026; verificar antes de pagar):**

| Vendedor | SKU | Precio anunciado | IVA / disponibilidad | Enlace |
|---|---|---:|---|---|
| [Aetherix](https://aetherix.com/product/nvidia-jetson-agx-orin-developer-kit-64gb-945-13730-0055-000/) | Developer Kit 64 GB, 945-13730-0055-000 | 4.199,00 € | IVA incluido; la página indicaba 3 unidades en stock y envío gratuito por Europa | [Ficha](https://aetherix.com/product/nvidia-jetson-agx-orin-developer-kit-64gb-945-13730-0055-000/) |
| [RS España](https://es.rs-online.com/web/p/kits-de-desarrollo-de-procesadores/2539662) | Developer Kit 64 GB, 945-13730-0055-000 | 4.012,53 € | IVA incluido; la página indicaba 9 unidades disponibles para enviar y más desde otro centro | [Ficha](https://es.rs-online.com/web/p/kits-de-desarrollo-de-procesadores/2539662) |
| [Reichelt España](https://www.reichelt.com/es/es/shop/producto/kit_de_desarrollo_nvidia_jetson_agx_orin_cpu_de_12_nucleos_64-383698) | Developer Kit 64 GB, 945-13730-0055-000 | 3.967,06 € antes de IVA | Ficha indica IVA del 21 % adicional y envío desde 9,95 €; plazo indicado 4–5 días laborables | [Ficha](https://www.reichelt.com/es/es/shop/producto/kit_de_desarrollo_nvidia_jetson_agx_orin_cpu_de_12_nucleos_64-383698) |

Reichelt totaliza aproximadamente 4.800,14 € con IVA del 21 % antes del envío (3.967,06 × 1,21). Son precios visibles en páginas de producto, no garantía de que el checkout conserve stock o precio. Confirmar total final y distinguir el kit de desarrollo de un módulo suelto.

Enlaces:
- Especificaciones oficiales: https://www.nvidia.com/es-es/autonomous-machines/embedded-systems/jetson-orin/
- Precio oficial/FAQ: https://developer.nvidia.com/embedded/faq
- Distribuidores desde NVIDIA: usar el enlace “local distributor” de la FAQ oficial.

Presupuesto:
- AGX Orin Developer Kit 64 GB: 3.499 USD de precio oficial anunciado por NVIDIA. No es precio final en EUR.
- NVMe con espacio para modelos y packs: necesario/recomendado por el fork; seleccionar y presupuestar según capacidad.
- Alimentación y refrigeración: verificar si vienen incluidas en el kit específico; no duplicar componentes incluidos.
- IVA/transporte: cotizar con distribuidor europeo.
- Total final España: **NO VERIFICADO** hasta disponer de una oferta final.

Un módulo de producción AGX Orin no es un kit completo: sumar carrier board compatible, fuente, disipación, almacenamiento y carcasa. Comparar ofertas solo cuando el SKU y la lista de componentes coincidan.

### 4.3 Fórmula TCO para LEONES

Registrar por separado:
1. precio del hardware y SKU;
2. IVA e impuestos;
3. envío y tasas de gestión;
4. fuente, carcasa y refrigeración no incluidas;
5. NVMe;
6. adaptadores y cables;
7. consumo de pared medido durante idle, prefill y decode;
8. coste de electricidad según tarifa introducida por el usuario;
9. disponibilidad/garantía y plazo de reposición.

No comparar precio por TOPS. Métricas útiles: EUR por GB de RAM realmente disponible, tokens/s por vatio de pared, tokens generados por kWh y coste total por token para un workload especificado.

## 5. Protocolo de extracción y normalización de benchmarks públicos (sin pruebas físicas)

### A. Revisión documental de plataforma y controladores

Para cada sistema, extraer de fuentes públicas cuando exista:
- modelo/SKU, memoria física, kernel, distribución y firmware;
- `uname -a`, `lscpu`, `free -h`, `lsblk`, `dmesg` relevante;
- versión del driver GPU, Vulkan/OpenCL/CUDA;
- para Vulkan: salida de `vulkaninfo --summary`;
- para PCIe: `lspci -vv` y ancho/velocidad realmente negociados;
- sensores térmicos y límites de potencia disponibles;
- `tegrastats` en Jetson; para ambos sistemas, vatímetro externo en la toma como fuente primaria de consumo.

No afirmar “GPU acelerada” hasta que el log del runtime identifique el backend y la carga real de GPU.

### B. Recopilación de benchmarks públicos de CPU y GPU

Buscar resultados publicados con revisión fijada de llama.cpp cuando existan: CPU pura, Vulkan en O6 y CUDA en Jetson. Registrar commit, flags, backend detectado y logs que el autor haya publicado. Si no hay fuente pública suficiente, marcar el resultado como no disponible; no compilar ni probar el hardware.

Modelo inicial pequeño para validar instalación; después un modelo dense de 7–8B y, finalmente, el MoE seleccionado. No empezar por el modelo más grande antes de validar el runtime.

### C. Selección documental de MoE y memoria

Modelos prioritarios que deben investigarse en fuentes públicas (sin ejecutarlos físicamente):
- un modelo Qwen3-30B-A3B o Qwen3.5-35B-A3B disponible en GGUF;
- registrar URL exacta, revisión, nombre de fichero, tamaño y SHA-256;
- cuantización idéntica entre plataformas, siempre que el formato sea compatible;
- contexto de 4K y después 8K, aumentando solo si no hay presión de memoria;
- tipo de KV explícito, batch/prefill, número de capas GPU, threads y offload registrados;
- distinguir modelo completo frente a variantes “Coder” con expertos eliminados;
- registrar fallos OOM, swap, uso de SSD y si se leen expertos desde fichero.

Para Strata, registrar la configuración publicada y comparar solo benchmarks públicos existentes. No declarar reproducido el resultado ni atribuir a LEONES la medición del autor.

### D. Normalización de métricas publicadas

- Extraer del autor la mediana/rango y número de repeticiones cuando estén publicados; no asumir repeticiones si no se declaran.
- Separar tiempo de carga, TTFT, prefill tok/s, decode tok/s, latencia total y memoria máxima.
- Separar consumo en pared, TDP y límite de potencia; son magnitudes distintas.
- Para Strata, conservar datos de prefijos reutilizados, tokens nuevos y caché de expertos caliente/fría si la fuente los distingue.
- Guardar URL, fecha de consulta, commit/hash disponible, modelo, configuración y cita de cada cifra.
- Anotar si el benchmark incluye evaluación de calidad/corrección o solo velocidad.

### Tabla de resultados públicos (rellenar únicamente con datos publicados; los cálculos derivados son ESTIMATED)

| Placa / backend | Modelo / cuantización | Contexto | Prefill tok/s | Decode tok/s | TTFT | RAM máxima / swap | W pared medio decode | tokens/J | Estado |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| Radxa O6 CPU | DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M (Radxa, terceros) | pp512 / tg128 | 64,60 ± 0,27 (pp512) | 36,29 ± 0,16 (tg128) | No publicado | No publicado | No publicado | No calculable | PUBLISHED por Radxa; no prueba física LEONES |
| Radxa O6 Vulkan | Pendiente | 4K | No medido | No medido | No medido | No medido | No medido | No medido | PENDIENTE |
| Jetson AGX Orin CUDA/Strata | Qwen3.8-Flash-Next Coder IQ1_M (terceros) | 32K | 37,8–52,5 tok/s en prompts cortos; caso 31.234 tokens/584 s | 18,6–21,6 tok/s (terceros) | No publicado aquí | ≥7,33 GiB libres; swap usado | No medido aquí | No medido aquí | PUBLISHED, tercero |
| Jetson AGX Orin CUDA/Strata | Qwen3.8-Flash-Next Coder IQ1_M (terceros, rebase 0.1.41) | 256K | 58,5 tok/s en prompt de 261.936 tokens | 6,6 tok/s (64 tokens) | No publicado aquí | ≥9,33 GiB libres; swap usado | No medido aquí | No medido aquí | PUBLISHED, tercero |

Los resultados de Orin anteriores no son comparables directamente con las filas de O6 pendientes: los tamaños de prompt, modelo, configuración y contexto difieren. No derivar tokens/J sin medición de potencia.

## 6. Riesgos de evidencia y criterios de comparación

**Radxa O6 — comprar solo si:**
- se acepta trabajo de integración de kernel/backend;
- el vendedor confirma versión de 64 GB y soporte/garantía;
- hay política de devolución si Vulkan/llama.cpp no funciona como se necesita;
- el objetivo incluye desarrollo de drivers y expansión PCIe, no solo “tokens/s listos para usar”.

**Jetson AGX Orin — elegir si:**
- el objetivo prioritario es reproducir Strata/CUDA y validar offload de expertos con menor incertidumbre;
- el coste alto está justificado por la madurez del ecosistema y el tiempo de ingeniería ahorrado;
- se acepta que los resultados publicados pertenecen a Orin 32 GB y a una cuantización/modelo concretos.

**No comprar aún** si el requisito es ejecutar un modelo MoE completo de 30–35B a una tasa de tokens/s mínima concreta: primero fijar el modelo, la cuantización, contexto y objetivo de rendimiento, y exigir un benchmark reproducible del mismo hardware o derecho de devolución.

## 7. Fuentes principales y nivel de confianza

1. Radxa Orion O6 oficial: https://radxa.com/products/orion/o6/ — alta confianza en especificaciones declaradas, no en rendimiento LLM.
2. Documentación O6: https://docs.radxa.com/en/orion/o6 — alta confianza en interfaces y configuración publicada.
3. PDF de precios oficiales históricos: https://dl.radxa.com/orion/o6/radxa_orion_o6_announcement_presentation_2024_12_18.pdf — fuente del MSRP anunciado, no de precio actual entregado.
4. NVIDIA Jetson Orin: https://www.nvidia.com/es-es/autonomous-machines/embedded-systems/jetson-orin/ — alta confianza en especificaciones oficiales.
5. NVIDIA FAQ: https://developer.nvidia.com/embedded/faq — alta confianza en precio oficial anunciado y distinción entre kit y módulo.
6. Strata Orin fork: https://github.com/calvinvette/strata-inference-orin — fuente primaria del port y de las mediciones publicadas por el autor; requiere reproducción independiente.
7. Protocolo de benchmarks Strata: https://github.com/calvinvette/strata-inference-orin/blob/main/docs/COMMUNITY_BENCHMARKS.md — buena guía de campos de medición y transparencia.
8. Kernel CIX P1 comunitario (O6N): https://github.com/AkaseToshiyuki/cix-p1-kernel-deploy — evidencia útil pero específica de O6N; no extrapolar sin comprobar.

## Conclusión

En la evidencia pública disponible, **Jetson AGX Orin es la plataforma con menor incertidumbre documental para Strata/CUDA ARM64**, porque existe un fork con benchmarks publicados. Se han localizado páginas de distribuidores europeos con precios anunciados de unos 4.012–4.199 € IVA incluido para el kit de 64 GB; comprobar disponibilidad y total final en el checkout.

Para un proyecto más abierto, con mayor RAM compartida y expansión PCIe, **Radxa Orion O6 64 GB es una candidata prometedora**. Ya existe un baseline oficial GGUF/CPU de 1.5B documentado por Radxa, pero falta evidencia pública comparable para MoE de 30–35B con backend Vulkan, memoria máxima, swap y consumo de pared. No recomendar comprar la O6 solo por el dato de 100 GB/s o los TOPS anunciados hasta verificar ese caso de uso.

El siguiente hito es cerrar las brechas documentales: revisar el ranking completo de Artificial Analysis, encontrar benchmarks públicos del mismo modelo/quant en Radxa O6 y Jetson Orin, y obtener precio final del SKU exacto para cada fila calculable. El primer barrido ya está incorporado en §0.1; los valores cruzados entre Orin 32 GB y el precio del kit 64 GB se excluyen del ranking. No se realizarán pruebas físicas. Si una combinación carece de benchmark público comparable, quedará explícitamente como brecha de evidencia.
