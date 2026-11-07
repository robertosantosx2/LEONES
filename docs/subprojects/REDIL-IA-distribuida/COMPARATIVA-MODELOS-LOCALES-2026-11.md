# Comparativa de modelos locales para REDIL — noviembre de 2026

> **Tipo de documento:** investigación comparativa y registro de benchmarks externos y mediciones locales.  
> **Fecha de corte:** 7 de noviembre de 2026.  
> **Ámbito:** Qwen3.5-4B, Qwen3-30B-A3B, Qwen3.5-35B-A3B, LFM3-1.7B y TwIL-8B.  
> **Relación con REDIL:** selección y asignación de especialistas para una futura arquitectura de servicios de IA local distribuida.  
> **Estado:** evaluación documental más resultados experimentales del equipo del autor. No constituye validación de despliegue de REDIL ni prueba normalizada entre todos los modelos.

## 1. Resumen ejecutivo

Los cinco modelos no son intercambiables. La evidencia disponible sugiere una arquitectura de especialistas:

- **Qwen3.5-35B-A3B:** candidato principal para razonamiento general avanzado, visión, documentos y comprensión de vídeo.
- **Qwen3.5-4B:** candidato generalista multimodal compacto, con un equilibrio atractivo entre calidad y velocidad local.
- **LFM3-1.7B (checkpoint de texto):** candidato para agentes ligeros, uso de herramientas, clasificación y automatizaciones de bajo coste.
- **TwIL-8B:** especialista de texto para matemáticas, programación y seguimiento de instrucciones; no es un modelo generalista de conocimiento equivalente a Qwen3.5.
- **Qwen3-30B-A3B:** referencia MoE textual de generación anterior, útil para experimentación comparativa de runtimes y razonamiento.

La recomendación operativa preliminar para REDIL es mantener Qwen3.5-35B-A3B, Qwen3.5-4B y LFM3-1.7B como núcleo de evaluación; incorporar TwIL-8B como especialista y conservar Qwen3-30B-A3B como referencia experimental.

## 2. Identidad, arquitectura y contexto

| Modelo | Parámetros / arquitectura | Contexto declarado | Entrada y salida del checkpoint considerado | Especialidad |
|---|---|---:|---|---|
| Qwen3.5-4B | 4B; denso | 262.144 | Texto + imagen; vídeo mediante secuencias de fotogramas; texto de salida | Generalista multimodal compacto, razonamiento, OCR/documentos, agentes |
| Qwen3-30B-A3B | 30,5B totales; 3,3B activos; MoE, 128 expertos y 8 activos en la variante Thinking-2507 | Hasta 262.144 en Thinking-2507; comprobar variante exacta | Texto → texto | Razonamiento, conocimiento, matemáticas, código y uso de herramientas |
| Qwen3.5-35B-A3B | 35B totales; 3B activos; MoE con 256 expertos, 8 enrutados + 1 compartido | 262.144 nativos; extensible según ficha hasta 1.010.000 | Texto + imagen; vídeo mediante fotogramas; texto de salida | Razonamiento avanzado, visión-lenguaje, documentos, vídeo y agentes |
| LFM3-1.7B | 1,73B; arquitectura híbrida tri-híbrida (convoluciones, atención local y global) | 256K | **El checkpoint probado es texto → texto** | Agentes locales, llamadas a herramientas, tareas especializadas y edge |
| TwIL-8B | 8,79B; Transformer denso basado en Granite 4.2 8B | 131.072 | Texto → texto; inglés según ficha | Matemáticas competitivas, código e instruction following |

**Precaución de variante:** Qwen3-30B-A3B existe en variantes con y sin razonamiento y con revisiones posteriores (por ejemplo, Instruct-2507 y Thinking-2507). Las cifras del benchmark de Thinking-2507 que aparecen más abajo son referencia oficial de esa revisión, no una afirmación de que el artefacto local del usuario sea idéntico. En TwIL-8B existen variantes `balanced` y `verbose`; la ficha marca explícitamente qué pruebas se hicieron en cada una.

## 3. Benchmarks de lenguaje, razonamiento, código y agentes

Los valores siguientes son puntuaciones publicadas por los autores de los modelos, expresadas como porcentaje salvo indicación contraria. Se muestran pruebas representativas, no un promedio agregado. **No son una clasificación perfectamente homogénea**: pueden variar las revisiones, prompts, presupuestos de tokens, herramientas, variantes de razonamiento y protocolos de evaluación.

| Benchmark | Qwen3.5-4B | Qwen3-30B-A3B Thinking-2507 | Qwen3.5-35B-A3B | LFM3-1.7B | TwIL-8B |
|---|---:|---:|---:|---:|---:|
| MMLU-Pro (conocimiento) | 79,1 | 80,9 | **85,3** | N/D | 76,5† |
| GPQA Diamond (ciencia) | 76,2 | 73,4 (GPQA en ficha) | **84,2** | 63,37 | 70,2 |
| IFEval (instrucciones) | 89,8 | 88,9 | 91,9 | **96,66** | 91,8 |
| IFBench (instrucciones difíciles) | 59,2 | N/D en tabla comparable | 70,2 | 73,03 | **74,4†** |
| HMMT Feb 2025 (matemáticas) | 74,0 | 71,4 (HMMT25) | 89,0 | N/D | 85,0 |
| LiveCodeBench | 55,8 (v6) | 66,0 (v6) | 74,6 (v6) | 73,46 (v6) | **81,6†** |
| SWE-bench Verified (agente de código) | N/D aquí | N/D aquí | 69,2 | 43,40 | N/D |
| BFCL (uso de herramientas) | TIR-Bench: 38,9/29,9* | BFCL-v3: 72,4 | BFCL-v4: 67,3 | BFCL-v4: 71,39 | N/D |
| RULER 128K / contexto largo | 84,63 | Consultar protocolo de la revisión | N/D en esta tabla | 65,56 | N/D |

† TwIL: puntuación medida en la variante **verbose**, no en balanced, según la ficha del modelo.  
* Qwen3.5-4B: TIR-Bench se publica con dos configuraciones de CI; no es el mismo benchmark que BFCL.  
N/D significa que no se encontró una cifra publicada comparable en las fichas consultadas; no significa cero ni incapacidad.

### Lectura de los resultados

- **Qwen3.5-35B-A3B** es el más fuerte de este grupo en las cifras de conocimiento y ciencia indicadas (MMLU-Pro 85,3; GPQA Diamond 84,2) y mantiene resultados competitivos en código, agentes y matemáticas.
- **Qwen3.5-4B** es sorprendentemente capaz para su tamaño: 79,1 en MMLU-Pro, 76,2 en GPQA Diamond y 55,8 en LiveCodeBench v6.
- **Qwen3-30B-A3B Thinking-2507** muestra mejora respecto a la versión original en tareas de razonamiento, con 85,0 en AIME25, 71,4 en HMMT25 y 66,0 en LiveCodeBench v6. No debe mezclarse con resultados de la variante base no-thinking.
- **LFM3-1.7B** está orientado a agentes, herramientas y tareas especializadas. Sus resultados publicados son especialmente interesantes en IFEval (96,66), IFBench (73,03), BFCL V4 (71,39) y LiveCodeBench v6 (73,46), aunque su GPQA Diamond (63,37) muestra que no sustituye a un modelo grande de conocimiento.
- **TwIL-8B** destaca en MATH-500 (98,2), AIME 2025 (88,3) y LiveCodeBench (81,6†) en la comparación de su propia ficha. La ficha advierte que LiveCodeBench, IFBench y varias pruebas de código se midieron en verbose, no en balanced. También advierte que el modelo queda por detrás de modelos mayores en conocimiento (GPQA Diamond 70,2; MMLU-Pro 76,5†).

### Benchmarks adicionales destacados

| Modelo | Prueba | Resultado publicado | Interpretación |
|---|---|---:|---|
| Qwen3-30B-A3B Thinking-2507 | AIME25 | 85,0 | Razonamiento matemático competitivo |
| Qwen3-30B-A3B Thinking-2507 | BFCL-v3 | 72,4 | Uso de herramientas / llamadas funcionales |
| Qwen3.5-35B-A3B | SWE-bench Verified | 69,2 | Resolución de incidencias de repositorios |
| Qwen3.5-35B-A3B | TAU2-Bench | 81,2 | Ejecución agentiva en dominios simulados |
| Qwen3.5-35B-A3B | BrowseComp | 61,0 | Búsqueda e investigación con herramientas |
| LFM3-1.7B | LiveClaw | 45,60 | Evaluación agentiva publicada por Liquid AI |
| LFM3-1.7B | Claw-Eval General (EN), media | 68,64 | Tareas generales en harnesses de agentes |
| LFM3-1.7B | MCP-Atlas | 32,57 | Selección/uso de herramientas MCP |
| TwIL-8B balanced | MATH-500 | 98,2 | Especialización matemática |
| TwIL-8B balanced | AIME 2025 | 88,3 | Matemáticas de competición |

No se debe convertir estos resultados en una puntuación global única: los conjuntos de evaluación y protocolos son diferentes.

## 4. Visión, vídeo y audio: capacidades reales del checkpoint

| Modelo / checkpoint | Texto | Imagen | Vídeo | Audio |
|---|---|---|---|---|
| Qwen3.5-4B | Sí | Sí, nativo | Sí, comprensión mediante fotogramas/secuencias | No se declara audio nativo en este checkpoint |
| Qwen3-30B-A3B | Sí | No | No | No |
| Qwen3.5-35B-A3B | Sí | Sí, nativo | Sí, comprensión mediante fotogramas/secuencias | No se declara audio nativo en este checkpoint |
| LFM3-1.7B **Text** | Sí | No | No | No |
| TwIL-8B | Sí | No | No | No |

### 4.1 Qwen3.5-4B y Qwen3.5-35B-A3B

La familia Qwen3.5 integra visión y lenguaje. Sus usos documentados incluyen:

- Interpretación de fotografías, capturas de pantalla, gráficos y diagramas.
- OCR, comprensión de documentos y extracción de información visual.
- Razonamiento visual y espacial.
- Comprensión de vídeo a partir de secuencias de fotogramas y evaluación en benchmarks como VideoMME, VideoMMMU, MLVU y MVBench.
- Agentes visuales y tareas de interacción con interfaces, sujetas a herramientas y runtime compatibles.

Resultados representativos publicados:

| Benchmark visual / vídeo | Qwen3.5-4B | Qwen3.5-35B-A3B |
|---|---:|---:|
| MMMU (razonamiento visual) | 77,6 | 81,4 |
| MMMU-Pro | 66,3 | 75,1 |
| MathVista (mini) | 85,1 | 86,2 |
| RealWorldQA | 79,5 | 84,1 |
| MMBench EN-DEV | 89,4 | 91,5 |
| OCRBench | 85,0 | 91,0 |
| VideoMME con subtítulos | 83,5 | 86,6 |
| VideoMME sin subtítulos | 76,9 | 82,5 |
| MLVU | 82,8 | 85,6 |
| MVBench | 71,2 | 74,8 |
| LVBench | 66,4 | 71,4 |

Los resultados del 4B se han transcrito de su ficha oficial; no deben sustituirse por cifras de otros tamaños.

**Límite de interpretación:** comprender vídeo no equivale a generar vídeo. La entrada de vídeo se procesa mediante fotogramas/representación temporal compatible con el modelo y el runtime. El rendimiento real depende del muestreo, resolución, número de fotogramas, contexto y preprocesamiento.

### 4.2 LFM3: separar familia y checkpoint

Liquid AI presenta LFM3 como una familia multimodal con variantes separadas de texto, visión, audio, omni y decisión. El modelo instalado/probado aquí es **LFM3-1.7B de texto**. Por tanto:

- LFM3-1.7B Text: texto y herramientas; no atribuirle entrada de imagen, vídeo o audio.
- Las variantes Vision/Audio/Omni de la familia son checkpoints distintos, que requerirían selección, descarga, runtime y validación propios.
- El checkpoint de texto está diseñado para agentes locales y especialización; Liquid AI declara contexto de 256K y un tamaño aproximado de 1 GB a 4 bits.
- No considerar que el nombre de la familia habilita automáticamente todas las modalidades en un mismo binario o checkpoint.

### 4.3 Qwen3-30B-A3B y TwIL-8B

Ambos checkpoints considerados son modelos de texto. Pueden trabajar con descripciones textuales de imágenes o transcripciones, pero eso no los convierte en modelos de visión o audio nativos. REDIL debe conectarles un servicio VLM, OCR, ASR o TTS cuando una tarea requiera esas modalidades.

## 5. Mediciones locales del usuario en MSI Thin 15

**Hardware de referencia:** MSI Thin 15 B12UC, Intel Core i7-12650H, NVIDIA RTX 3050 Laptop de 4 GB VRAM, 14 GB RAM, Ubuntu. Estas mediciones son resultados comunicados por el usuario en sus experimentos y se registran como evidencia local; no son resultados de los fabricantes.

| Modelo | Motor / versión | Generación medida | Observaciones |
|---|---|---:|---|
| Qwen3.5-4B | TensorFold | 53–55 tok/s | Medición local |
| Qwen3.5-4B | TensorFold PR #1879 | 54–56 tok/s | PR relacionado con la reserva de memoria CUDA; medición local |
| Qwen3.5-4B | llama.cpp CUDA CLI | 42,4 tok/s | CLI |
| Qwen3.5-4B | llama.cpp CUDA API | 47,65 tok/s | API |
| Qwen3.5-4B | RustingStrata | No expuesta por API | Sin cifra comparable disponible |
| Qwen3-30B-A3B | llama.cpp CUDA | 1,51–2,00 tok/s | Tanda larga |
| Qwen3-30B-A3B | RustingStrata | 7,74 tok/s | Generación de 64 tokens |
| Qwen3.5-35B-A3B | Tandem.cpp | **35,6 tok/s** | Ejecución CPU-MoE; configuración experimental registrada por separado |
| LFM3-1.7B | Pithos 0.5.0 | 87,22 tok/s | Ejecución local |
| LFM3-1.7B | Pithos 0.5.1 | **104,84 tok/s** | Ejecución local |
| TwIL-8B | llama.cpp CUDA | 3,89–5,11 tok/s | GGUF Q4_K_M balanced; intervalo observado |

### 5.1 Interpretación de rendimiento

- LFM3-1.7B con Pithos 0.5.1 ofrece la mayor velocidad de generación registrada: 104,84 tok/s.
- Qwen3.5-4B se sitúa en torno a 42–56 tok/s según motor/API.
- Tandem.cpp alcanza 35,6 tok/s con Qwen3.5-35B-A3B, un resultado especialmente relevante para un modelo MoE de 35B totales en este equipo.
- RustingStrata registra 7,74 tok/s con Qwen3-30B-A3B en una generación de 64 tokens, frente a 1,51–2,00 tok/s en la tanda larga de llama.cpp; no es una comparación controlada.
- TwIL-8B es más lento en la ejecución registrada, pero su especialización matemática y de código puede justificar un servicio dedicado.

**Advertencia:** no comparar directamente tok/s de pruebas con contextos, cuantizaciones, prompts, longitudes de salida, modos de razonamiento o configuraciones diferentes. Para un benchmark REDIL normalizado se deben fijar modelo/hash, cuantización, runtime/commit, contexto, prompt, tokens de salida, temperatura, batch, offload, modo thinking, caché y número de repeticiones. Registrar TTFT, prefill tok/s, decode tok/s, RAM/VRAM pico, swap, energía si se mide y calidad de tarea.

## 6. Artificial Analysis Intelligence Index: criterio de uso

No se asigna aquí un número de Artificial Analysis Intelligence Index a cada uno de los cinco modelos. Un índice compuesto solo debe consignarse cuando el modelo y la configuración exactos aparezcan en la tabla oficial de resultados y se pueda identificar la versión metodológica.

Artificial Analysis anunció Intelligence Index v5 el 27 de octubre de 2026. V5 introduce pruebas nuevas y privadas, cambia pesos y conjuntos, y no es intercambiable con cifras de versiones anteriores. Por tanto:

- No reutilizar puntuaciones antiguas de AA como si fueran v5.
- No inferir el índice a partir de MMLU, GPQA, LiveCodeBench o una valoración cualitativa.
- Registrar por separado **AA Intelligence Index (versión)** y benchmarks individuales.
- Si un modelo no aparece en la tabla oficial comparable, consignar **N/D — no listado/no verificado**, no una estimación.

## 7. Valoración técnica para REDIL

La valoración siguiente es cualitativa y orientada a asignación de servicio. No es una puntuación oficial ni sustituye los benchmarks.

| Modelo | Capacidad general | Velocidad local observada | Multimodalidad del checkpoint | Especialidad | Papel propuesto |
|---|---|---|---|---|---|
| Qwen3.5-4B | Alta para su tamaño | 42,4–56 tok/s | Texto + imagen + vídeo | Generalista multimodal, documentos, OCR, agentes ligeros | Servicio generalista multimodal de baja latencia |
| Qwen3-30B-A3B | Alta en texto/razonamiento | 1,51–7,74 tok/s según prueba/motor | Solo texto | Razonamiento, matemáticas, código | Banco de pruebas MoE / especialista textual alternativo |
| Qwen3.5-35B-A3B | Muy alta | 35,6 tok/s con Tandem.cpp | Texto + imagen + vídeo | Razonamiento, visión, vídeo, agentes | Especialista principal para tareas complejas |
| LFM3-1.7B Text | Especializada; menor conocimiento general que modelos grandes | 87,22–104,84 tok/s | Solo texto en este checkpoint | Agentes, herramientas, clasificación y automatización | Enrutador asistido, agente ligero y tareas frecuentes |
| TwIL-8B | Alta en dominios específicos | 3,89–5,11 tok/s | Solo texto | Matemáticas, código e instrucciones | Especialista de matemáticas/programación |

### Recomendación de arquitectura

1. **Qwen3.5-35B-A3B — razonamiento y multimodalidad avanzada.** Usarlo cuando la complejidad justifique el coste de memoria/latencia. Su rendimiento Tandem.cpp es una evidencia local destacada, pero mantener la configuración experimental documentada.
2. **Qwen3.5-4B — generalista multimodal de servicio frecuente.** Es el candidato más equilibrado para solicitudes normales que requieran texto, imágenes, documentos o clips de vídeo.
3. **LFM3-1.7B Text — agente de alta frecuencia.** Adecuado para tareas cortas, clasificación, extracción estructurada y llamadas a herramientas; no enrutarle imágenes o audio como si el checkpoint fuera multimodal.
4. **TwIL-8B — matemáticas y código.** Enrutar tareas de programación y matemáticas cuando las pruebas internas confirmen ventaja real; tener en cuenta licencia no comercial.
5. **Qwen3-30B-A3B — referencia experimental.** Mantenerlo para comparar MoE, runtimes y estrategias de offload; no parece el mejor candidato general frente a Qwen3.5-35B-A3B en el conjunto de resultados consultado.

## 8. Implicaciones para el hardware local y nodos REDIL

El equipo de referencia tiene 4 GB de VRAM y 14 GB de RAM. Los parámetros activos de un MoE no equivalen al tamaño total de los pesos que deben almacenarse. Qwen3-30B-A3B y Qwen3.5-35B-A3B requieren dimensionar pesos, buffers, caché KV, contexto y memoria del runtime; el hecho de activar aproximadamente 3B parámetros por token no implica que solo haya que alojar 3B parámetros.

Recomendaciones de despliegue:

- No mantener los cinco modelos residentes a la vez en el MSI.
- Cargar especialistas bajo demanda y descargar/liberar memoria entre servicios.
- Mantener límites de contexto y concurrencia explícitos; medir swap y memoria pico.
- Separar procesos y puertos para que las pruebas no interfieran con LEONES/ODS u otros servicios.
- No asumir que la compatibilidad de un modelo con un runtime se transfiere a otro runtime o a otra versión.
- Para REDIL distribuida, asignar servicios a nodos por especialidad; no presentar la RAM de varios equipos como memoria unificada salvo que un backend implemente explícitamente particionado de pesos.

## 9. Limitaciones, licencias y reproducibilidad

- **TwIL-8B:** la ficha declara licencia webAI Non-Commercial License 1.0. No tratarlo como componente libre para uso comercial sin revisar las condiciones.
- **Qwen3-30B-A3B y Qwen3.5:** verificar licencia y artefacto exacto de cada revisión antes de redistribuir.
- **LFM3:** la familia tiene checkpoints separados para texto, visión, audio, omni y decisión. La licencia y compatibilidad deben verificarse para el artefacto elegido.
- Las puntuaciones de los fabricantes son resultados declarados por sus autores. No son mediciones independientes de LEONES.
- Las cifras locales del usuario no son todavía un benchmark común entre los cinco modelos.
- Los nombres de motor, versión, modelo, cuantización y configuración deben acompañar siempre a cada cifra.

### Protocolo mínimo para la siguiente ronda de pruebas REDIL

1. Registrar SHA del modelo, nombre exacto del artefacto, cuantización y tokenizer.
2. Fijar runtime, commit/build, backend efectivo (CUDA/CPU), flags y contexto.
3. Ejecutar prompts idénticos y controlar thinking/no-thinking, temperatura, batch y salida máxima.
4. Hacer al menos tres repeticiones y registrar media, mediana y dispersión.
5. Medir TTFT, prefill tok/s, decode tok/s, RAM/VRAM pico, swap y estabilidad.
6. Evaluar calidad por especialidad: MMLU/GPQA para conocimiento, MATH/AIME para matemáticas, LiveCodeBench/SWE-bench para código, IFEval/IFBench para instrucciones, MMMU/OCRBench/VideoMME para visión y vídeo, y BFCL/τ-bench para herramientas.
7. Conservar logs, comandos, manifiesto, entorno y resultados JSON/JSONL.
8. Marcar como **MEASURED-LEONES** solo resultados reproducibles en el hardware identificado. Mantener los resultados upstream como **UPSTREAM-REPORTED**.

## 10. Fuentes primarias y trazabilidad

Consultadas el 7 de noviembre de 2026, salvo que la página indique otra fecha:

1. [Qwen3.5-4B — ficha oficial en Hugging Face](https://huggingface.co/Qwen/Qwen3.5-4B) — benchmarks de lenguaje, visión, vídeo, herramientas y contexto.
2. [Qwen3-30B-A3B-Thinking-2507 — ficha oficial](https://huggingface.co/Qwen/Qwen3-30B-A3B-Thinking-2507) — arquitectura MoE y benchmarks de razonamiento, código, agentes y multilingüismo.
3. [Qwen3.5-35B-A3B — ficha oficial](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) — arquitectura, parámetros activos, contexto y benchmarks de lenguaje, visión y vídeo.
4. [Liquid AI — Introducing LFM3](https://www.liquid.ai/blog/lfm3) — descripción de la familia, variantes de modalidad y benchmarks del checkpoint LFM3-1.7B Text. Publicado el 27 de octubre de 2026.
5. [LFM3-1.7B-Base — ficha en Hugging Face](https://huggingface.co/LiquidAI/LFM3-1.7B-Base) — arquitectura, tamaño y contexto del modelo base.
6. [TwIL-8B — ficha oficial de webAI](https://huggingface.co/webAI-Official/TwIL-8B) — variantes balanced/verbose, benchmarks, protocolo, contexto, idioma y licencia.
7. [Artificial Analysis — Intelligence Index v5](https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v5/) — metodología y cambios anunciados el 27 de octubre de 2026.
8. [Artificial Analysis — metodología de benchmarking](https://artificialanalysis.ai/methodology/intelligence-benchmarking) — definición del índice compuesto y evaluaciones.

### Registro de procedencia

- **UPSTREAM-REPORTED:** puntuaciones publicadas en las fichas/blogs oficiales de los desarrolladores.
- **LOCAL-MEASURED-USER:** velocidades de inferencia facilitadas por el usuario para su MSI Thin 15; conservar los logs originales de cada experimento para reproducibilidad.
- **QUALITATIVE-ASSESSMENT:** valoración y asignación propuestas por este informe para REDIL; no es una puntuación externa.
- **N/D:** dato no disponible o no comparable en las fuentes consultadas.

---
*Documento de investigación de REDIL dentro de LEONES. Actualizarlo cuando cambien las revisiones de los modelos, los benchmarks upstream o las mediciones locales. No sobrescribir resultados históricos: añadir fecha, artefacto y configuración para conservar la trazabilidad.*
