# Modelos de difusión de texto con pesos abiertos: catálogo, hardware, runtimes y benchmark

**Fecha de corte:** 2026-10-30  
**Estado:** investigación documental; no constituye una medición LEONES.  
**Ámbito:** modelos de lenguaje que generan o editan texto mediante difusión discreta, enmascarada, por bloques o mecanismos híbridos.

> **Regla de evidencia LEONES:** los resultados de autores o terceros son evidencia externa. Las estimaciones de memoria son ESTIMATED. Solo una ejecución controlada en hardware identificado, con artefactos y configuración conservados, puede producir MEASURED de LEONES.

## 1. Resumen ejecutivo

La difusión de texto genera o edita secuencias refinando progresivamente tokens enmascarados, bloques o secuencias parciales, en lugar de depender exclusivamente de la generación autorregresiva token a token.

Hallazgos principales:

1. LLaDA y Dream son referencias útiles para masked discrete diffusion y generación de texto/código.
2. DiffuCoder explora difusión para programación e infilling.
3. Clover-35B-A3B y DiffusionGemma-26B-A4B representan modelos grandes y MoE. Los parámetros activos no equivalen al tamaño de pesos que hay que alojar.
4. llama.cpp, Transformers y diffuse-cpp son rutas de ejecución que merecen evaluación independiente. La compatibilidad depende de modelo, versión, formato y backend.
5. TensorFold no queda acreditado como runtime de difusión de texto en esta investigación. Se registra como integración pendiente, no como incompatibilidad definitiva.
6. Para el MSI con RTX 3050 Laptop de 4 GiB, 16 GB RAM e i7-12650H, el primer objetivo razonable es un checkpoint pequeño como Open-dCoder 0.5B. Dream y LLaDA deben estudiarse inicialmente cuantizados en CPU/offload.

## 2. Taxonomía técnica

| Familia | Mecanismo | Ejemplos | Observaciones |
|---|---|---|---|
| Masked discrete diffusion | Se enmascaran tokens y se predicen/revelan progresivamente | LLaDA, Dream, MDLM | Los tokens resueltos por iteración afectan a latencia |
| Block diffusion | Refinamiento por bloques | Clover y variantes | No implica generación plenamente paralela sin dependencias |
| Difusión para código | Infilling, edición y completado | DiffuCoder, Dream-Coder, Open-dCoder | Evaluar preservación del contexto |
| AR-to-diffusion / híbridos | Adaptación o combinación de modelos autorregresivos y difusión | DiffuLLaMA, RND1 y líneas híbridas | La conversión no implica compatibilidad automática con runtimes AR |
| Continuous / latent diffusion | Difusión en representaciones continuas o latentes | Investigación académica | No siempre existe un asistente descargable |
| Fundamentos y entrenamiento | Objetivos y formulaciones de entrenamiento | MDLM, SEDD, DiffusionBERT, DiffuSeq | Referencias científicas; no todos son checkpoints instruct |

### Métricas y terminología

- **Paso/iteración de difusión:** actualización del estado enmascarado o de la secuencia.
- **Denoising steps:** número de iteraciones realizadas.
- **Tokens/s:** indicar si son tokens nuevos/s, tokens de secuencia completa/s o throughput agregado.
- **Tiempo por iteración:** separar forward, selección/muestreo, actualización de máscara y transferencias cuando sea posible.
- **Tokens resueltos por iteración:** medida necesaria para interpretar la eficiencia.
- **TTFT:** definir si se mide hasta el primer token visible o hasta completar el primer bloque.
- **KV cache / caché inter-step:** no todos los modelos y motores usan la misma estrategia.

No es correcto concluir que un modelo será más rápido solo porque resuelve varios tokens en paralelo. El número de iteraciones, tamaño de bloque, política de confianza, muestreo, atención y cachés determinan el resultado.

## 3. Catálogo de modelos y proyectos

| Proyecto / modelo | Escala declarada | Tipo / objetivo | Referencias |
|---|---:|---|---|
| **LLaDA-8B** | 8B | Masked discrete diffusion; instruction following | [GitHub](https://github.com/ML-GSAI/LLaDA) · [Hugging Face](https://huggingface.co/GSAI-ML/LLaDA-8B-Instruct) |
| **Dream-7B / Dream-v0-Instruct-7B** | ~7B | DLM general, masked diffusion | [Dream](https://github.com/DreamLM/Dream) · [diffuse-cpp GGUF](https://huggingface.co/diffuse-cpp) |
| **Dream-Coder-7B** | ~7B | Código, infilling y edición | [Dream-Coder](https://github.com/DreamLM/Dream-Coder) |
| **DiffuCoder-7B** | 7B | Difusión para generación de código | [Apple ml-diffucoder](https://github.com/apple/ml-diffucoder) · [pesos](https://huggingface.co/apple/DiffuCoder-7B-Base) |
| **Open-dLLM / Open-dCoder** | Incluye 0.5B | Entrenamiento, inferencia y evaluación abiertos | [Open-dLLM](https://github.com/pengzhangzhi/Open-dLLM) |
| **DiffuLLaMA** | ~7B | Adaptación AR a difusión | [HKUNLP](https://github.com/HKUNLP/DiffuLLaMA) |
| **ELYZA-Diffusion-Instruct-1.0-Dream-7B** | 7.6B | Instruct japonés basado en Dream | [Hugging Face](https://huggingface.co/elyza/ELYZA-Diffusion-Instruct-1.0-Dream-7B) |
| **LLaDA-MoE / líneas MoE** | Variable | Investigación de expertos dispersos | Verificar checkpoint exacto; no confundir con Clover |
| **Clover-35B-A3B** | 35B total / ~3B activos declarados | MoE y block diffusion | [GGUF](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview-GGUF) |
| **DiffusionGemma-26B-A4B** | ~26B total / ~4B activos declarados | MoE de difusión de Google | [Model card](https://ai.google.dev/gemma/docs/diffusiongemma/model_card) · [Unsloth](https://unsloth.ai/docs/models/diffusiongemma) |
| **RND1** | ~30B según checkpoint | Adaptación de modelos a difusión | [RadicalNumerics](https://github.com/RadicalNumerics/RND1) |
| **LLaDA2.x** | Varios tamaños | Nueva generación de modelos de difusión/edición | [InclusionAI](https://github.com/inclusionAI/LLaDA2.X) |
| **Nemotron-Labs-Diffusion** | Checkpoints de la familia 8B | Investigación de difusión de texto | [Colección NVIDIA](https://huggingface.co/collections/nvidia/nemotron); verificar checkpoint exacto |
| **MDLM** | Investigación / varias escalas | Masked Diffusion Language Model | [Artículo](https://arxiv.org/abs/2406.07524) |
| **SEDD** | Investigación | Discrete Score Entropy | [Artículo](https://arxiv.org/abs/2310.16834) |
| **DiffusionBERT** | Investigación | Difusión discreta basada en BERT | [Artículo](https://arxiv.org/abs/2211.15029) |
| **DiffuSeq** | Investigación | Difusión discreta para generación condicionada | [Artículo](https://arxiv.org/abs/2210.08933) |
| **UltraLLaDA** | Investigación | Contexto largo | Verificar checkpoint, licencia y runtime |
| **MMaDA** | Multimodal | Modelado multimodal con difusión | No clasificar como exclusivamente textual |

### Servicios cerrados: contexto, no inventario open-weights

- **Mercury / Mercury Coder (Inception Labs):** difusión comercial/API; no tratar como pesos abiertos sin checkpoint público verificable.
- **Gemini Diffusion (Google):** demostración/línea experimental; no confundir con DiffusionGemma descargable.
- **Seed Diffusion (ByteDance):** línea de investigación/servicio; registrar solo checkpoints públicos verificables como open-weights.

## 4. Cuantización y memoria

Las cifras son estimaciones de planificación, no mínimos garantizados. El tamaño del archivo no equivale a memoria total de ejecución.

| Modelo | Parámetros | Pesos cuantizados orientativos | Memoria total orientativa | Nota |
|---|---:|---:|---:|---|
| Open-dCoder 0.5B | 0.5B | FP16 ~1 GB | 1.5–2.5 GB | Candidato para GPU pequeña |
| Modelos pequeños ~1.3B | 1.3B | FP16 ~2.6 GB | 3–4.5 GB | Verificar nombre y arquitectura exactos |
| DiffuLLaMA-7B | ~7B | Q4 ~3.8–4.3 GB | 5–7 GB | Depende de conversión |
| Dream-7B | ~7B | Q4 ~4–5 GB | 6–8 GB | Añadir buffers/contexto |
| Dream-Coder-7B | ~7B | Depende de checkpoint | 6–8 GB | No asumir mismo tamaño que Dream base |
| DiffuCoder-7B | 7B | Q4 ~4.2–4.7 GB | 6–8 GB | Verificar tokenizer y arquitectura |
| LLaDA-8B | 8B | Q4 ~4.5–5.1 GB | 6–8 GB | Contexto y buffers elevan total |
| ELYZA Dream 7B | 7.6B | Q4_K_M publicado ~4.68 GB | ~5.8–8 GB | Contexto y runtime importan |
| DiffusionGemma-26B-A4B | ~26B | Q4 dinámico / formatos específicos | ~16–18 GB según guía publicada | MoE: alojar expertos, no solo activos |
| Clover-35B-A3B | 35B | Q4_K_M publicado ~21.42 GiB | >22 GiB más buffers/contexto | GPU 24 GB muy ajustada |
| RND1 | ~30B | Depende del checkpoint | ~20–24 GB o más | No hay cifra universal |
| LLaDA2.2-mini | 16.3B declarados | Depende de pesos/quant | Estimación no validada | No usar como requisito oficial |
| LLaDA2.2-flash | ~100B declarado | Depende de pesos/quant | Clase 80 GB+ orientativa | Confirmar arquitectura/formato |

### Reglas para cuantizaciones

1. Registrar repositorio y archivo exactos, tamaño en bytes, formato, cuantización y fecha.
2. Distinguir Q4_0, Q4_K_M, IQ4_XS, UD-Q4_K_XL y cuantizaciones de terceros.
3. GGUF no garantiza compatibilidad: la arquitectura debe estar soportada por la versión del runtime.
4. Registrar contexto, generación, batch, iteraciones, buffers, offload y precisión.
5. En MoE, el cómputo activo por token no reduce automáticamente el almacenamiento de todos los expertos.

## 5. Hardware: matriz preliminar

| Memoria GPU / unificada disponible | Objetivo razonable | Restricciones |
|---:|---|---|
| 4 GiB | Open-dCoder 0.5B y checkpoints pequeños | Contexto corto; no asumir GPU completa |
| 6 GiB | Modelos pequeños y algunos 7B muy cuantizados con offload | Ajuste severo |
| 8 GiB | Dream/LLaDA 7–8B Q4 con contexto moderado si el motor lo permite | Depende de arquitectura y buffers |
| 12 GiB | 7–8B Q4/Q8 según formato y contexto | Mayor margen |
| 16 GiB | Modelos 7–8B de mayor precisión y medianos | DiffusionGemma Q4 puede requerir más |
| 24 GiB | DiffusionGemma Q4 como objetivo; Clover Q4 muy ajustado | Comprobar memoria real |
| 32 GiB | Clover Q4 con margen más razonable | Runtime sigue siendo gate |
| 48–80 GiB | Modelos MoE grandes y precisiones superiores | Medir por modelo |

### Perfil local de referencia LEONES

Hardware conocido para planificar, no como benchmark:

- MSI Thin 15 B12UC.
- Intel Core i7-12650H.
- 16 GB RAM.
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- Ubuntu; driver NVIDIA/CUDA instalados.
- Swap configurada; no contarla como RAM ni VRAM.

**Prioridad:** Open-dCoder 0.5B en Transformers/CUDA si la implementación es compatible; después Dream-7B y LLaDA-8B cuantizados mediante diffuse-cpp en CPU. Evaluar offload/GPU solo después de verificar soporte. No intentar cargar Clover o DiffusionGemma íntegramente en esta GPU.

## 6. Compatibilidad de runtimes

Estados:
- **Documentado:** existe código/documentación que contempla esa familia.
- **Condicional:** requiere versión, fork, conversión o implementación específica.
- **No acreditado:** no se ha localizado evidencia suficiente.
- **Pendiente de prueba LEONES:** el soporte upstream no se ha ejecutado en entorno LEONES.

| Modelo/familia | TensorFold | llama.cpp | Transformers | diffuse-cpp |
|---|---|---|---|---|
| Open-dCoder 0.5B | No acreditado | No acreditado | Condicional: código/modelo específico | No acreditado |
| Mask DFM / Edit Flow | No acreditado | No acreditado | Condicional | No acreditado |
| LLaDA-8B | No acreditado | Documentado en rutas de difusión compatibles | Implementación LLaDA | Documentado |
| Dream-7B | No acreditado | Documentado en rutas de difusión compatibles | Implementación Dream | Documentado |
| Dream-Coder | No acreditado | Condicional al checkpoint | Condicional | No acreditado |
| DiffuCoder-7B | No acreditado | Condicional a versión/implementación | Implementación Apple | No acreditado |
| DiffuLLaMA | No acreditado | Condicional | Implementación del proyecto | No acreditado |
| ELYZA Dream | No acreditado | Condicional a compatibilidad Dream | Condicional | Condicional; validar conversión/tokenizer |
| Clover-35B-A3B | No acreditado | Condicional a versión con soporte Clover y GGUF adecuado | Condicional | No acreditado |
| DiffusionGemma | No acreditado | No acreditado en la ruta revisada | Documentado | No acreditado |
| RND1 | No acreditado | Condicional a soporte específico | Condicional | No acreditado |
| LLaDA2.x | No acreditado | Condicional por subversión | Implementación específica | No acreditado |
| Nemotron-Labs-Diffusion | No acreditado | No acreditado | Condicional a implementación oficial | No acreditado |

### Referencias de runtime

- [llama.cpp — examples/diffusion](https://github.com/ggml-org/llama.cpp/tree/master/examples/diffusion)
- [diffuse-cpp](https://github.com/iafiscal1212/diffuse-cpp)
- [Transformers — DiffusionGemma](https://huggingface.co/docs/transformers/main/model_doc/diffusion_gemma)
- [TensorFold](https://github.com/ashhart/TensorFold)
- [Open-dLLM](https://github.com/pengzhangzhi/Open-dLLM)

**TensorFold:** no se ha encontrado una receta/capability explícita de DLM en la documentación consultada. El estado correcto es not-verified; no se afirma imposibilidad técnica.

**llama.cpp:** soporte dependiente de revisión. Registrar versión/commit y backend CUDA. Una CLI de difusión no implica que cualquier checkpoint funcione.

**Transformers:** un checkpoint en Hugging Face no basta; hace falta una implementación compatible y dependencias adecuadas.

**diffuse-cpp:** motor especializado. Verificar las arquitecturas y formatos de la revisión utilizada; no extrapolar Dream/LLaDA a todos los modelos.

## 7. Rendimiento publicado: evidencia externa

### 7.1 diffuse-cpp: CPU AMD EPYC 4465P

La documentación/benchmarks del proyecto muestran resultados de Dream-7B y LLaDA-8B en AMD EPYC 4465P de 12 núcleos, Q4_K_M y 12 hilos, con opciones de caché/early-exit indicadas por el benchmark.

| Modelo | Resultado promedio citado | Condiciones |
|---|---:|---|
| Dream-7B | ~11.6 tokens/s | EPYC 4465P, Q4_K_M, 12 hilos; caché/early-exit |
| LLaDA-8B | ~15.3 tokens/s | EPYC 4465P, Q4_K_M, 12 hilos; caché/early-exit |

Resultados por tarea comunicados (configuración concreta del proyecto; no mezclar con el promedio anterior):

| Tarea | Dream-7B | LLaDA-8B |
|---|---:|---:|
| Pregunta factual | 21.6 tok/s | 24.4 tok/s |
| Traducción francesa | 14.3 tok/s | 27.7 tok/s |
| Aritmética | 21.6 tok/s | 15.7 tok/s |
| Traducción española | 13.2 tok/s | 22.9 tok/s |
| Programación | 8.2 tok/s | 4.9 tok/s |
| Escritura creativa | 4.5 tok/s | 5.3 tok/s |

**Advertencia:** verificar en el benchmark original la definición de throughput, longitud de secuencia, prompt, tokens generados y pasos antes de comparar con otro motor. Son cifras externas, no mediciones LEONES.

Fuente: [diffuse-cpp](https://github.com/iafiscal1212/diffuse-cpp).

### 7.2 llama.cpp: Dream-7B en A100

Se ha comunicado una ejecución de Dream-v0-Instruct-7B Q4_K_M en NVIDIA A100, longitud máxima 512 y 256 pasos:

| Métrica publicada | Resultado |
|---|---:|
| Throughput comunicado | 11.98 tok/s |
| Tiempo medio por paso | 166.91 ms |
| Forward/cálculo por paso | 108.24 ms |
| Muestreo por paso | 58.67 ms |
| Iteraciones | 256 |
| Longitud máxima | 512 |

La cifra de tok/s debe interpretarse según la definición del benchmark: puede contar secuencia completa y no solo tokens nuevos. No es directamente comparable con diffuse-cpp.

Fuente: [llama.cpp discussion #22972](https://github.com/ggml-org/llama.cpp/discussions/22972).

### 7.3 Matriz de rendimiento por modelo y motor

| Modelo | Motor | Hardware | Tokens/s | ms/iteración | Estado |
|---|---|---|---:|---:|---|
| Dream-7B | diffuse-cpp | EPYC 4465P, 12 hilos | ~11.6 promedio citado | No desglosado | Evidencia externa |
| LLaDA-8B | diffuse-cpp | EPYC 4465P, 12 hilos | ~15.3 promedio citado | No desglosado | Evidencia externa |
| Dream-7B | llama.cpp | A100 | 11.98 publicado | 166.91 | Evidencia externa; definición distinta |
| LLaDA-8B | llama.cpp | No consolidado | — | — | Pendiente |
| Open-dCoder 0.5B | Transformers | No consolidado | — | — | Pendiente |
| DiffuCoder-7B | Transformers | No consolidado | — | — | Pendiente |
| DiffusionGemma | Transformers | No consolidado | — | — | Pendiente |
| Clover | llama.cpp | No consolidado | — | — | Pendiente |
| Cualquier DLM | TensorFold | No consolidado | — | — | Sin soporte acreditado |

El guion significa pendiente, no cero.

## 8. Metodología de benchmark LEONES

### 8.1 Objetivo

Comparar calidad, latencia, throughput, memoria y recursos de DLM bajo configuraciones reproducibles. Separar CPU y GPU. No comparar tokens/s entre motores sin normalizar la definición de tokens y el trabajo realizado.

### 8.2 Batería inicial

| ID | Modelo | Runtime | Dispositivo | Configuración inicial |
|---|---|---|---|---|
| DLM-001 | Open-dCoder 0.5B | Transformers | RTX 3050 CUDA | FP16 si cabe; contexto corto |
| DLM-002 | Dream-7B | diffuse-cpp | i7-12650H CPU | Q4_K_M, hilos registrados |
| DLM-003 | Dream-7B | llama.cpp | CPU y/o CUDA | GGUF compatible |
| DLM-004 | LLaDA-8B | diffuse-cpp | i7-12650H CPU | Q4_K_M |
| DLM-005 | LLaDA-8B | llama.cpp | CPU y/o CUDA | GGUF compatible |
| DLM-006 | Dream-7B | Transformers | CPU; CUDA solo si cabe | Implementación original |
| DLM-007 | DiffuCoder-7B | Transformers | CPU/offload | Implementación Apple |
| DLM-008 | TensorFold | — | — | Gate de descubrimiento; no ejecutar como soportado sin receta |

### 8.3 Tareas comunes

1. **Factual breve:** respuesta de 1–3 frases.
2. **Aritmética:** operaciones con respuesta verificable.
3. **Traducción:** español ↔ inglés y, cuando aplique, francés.
4. **Código:** función completa con tests.
5. **Code infilling:** completar hueco con contexto anterior y posterior.
6. **Edición localizada:** corregir una función sin alterar regiones no objetivo.
7. **Escritura:** generación de texto de longitud fija.

Guardar prompts exactos, seeds cuando el sampler lo permita, tokenizer, versión del modelo y grader.

### 8.4 Métricas obligatorias

| Métrica | Definición |
|---|---|
| Model load time | Inicio de carga hasta modelo listo |
| Prompt processing | Tiempo de procesamiento de entrada |
| First visible output | Tiempo hasta primera salida visible/bloque |
| Total generation latency | Solicitud hasta resultado completo |
| New tokens/s | Tokens nuevos / tiempo de generación |
| Sequence tokens/s | Tokens de secuencia / tiempo; reportar aparte |
| Denoising steps | Iteraciones realizadas |
| ms/step | Tiempo de denoising / pasos, separando overhead |
| Tokens resolved/step | Tokens fijados por iteración |
| Peak VRAM | Pico de memoria GPU |
| Peak RAM | Pico RSS y memoria del sistema |
| CPU utilization | Uso y número de hilos |
| GPU utilization | Uso, memoria, potencia y temperatura |
| Energy | Wh por tarea si hay medición fiable |
| Quality | Exactitud, tests, pass@1 y preservación de contexto |

### 8.5 Protocolo

- Registrar commit del runtime, driver, CUDA, PyTorch, Transformers, sistema operativo y kernel.
- Registrar SHA256 del modelo, tokenizer y configuración.
- Separar carga en frío, warmup y ejecuciones medidas.
- Ejecutar al menos tres repeticiones medidas por tarea, salvo excepción documentada.
- Fijar prompt, salida objetivo, batch, contexto, sampler, pasos, threshold, early-exit y caché.
- No comparar run con early-exit/caché contra otro sin esas optimizaciones sin etiquetarlo.
- Reportar media, mediana, desviación y valores individuales.
- Guardar stdout/stderr, métricas de sistema, JSON y entorno.
- No usar swap como sustituto de memoria física sin declararlo.
- Resultados de otras máquinas = EXTERNAL_REFERENCE, nunca MEASURED.

### 8.6 Definiciones

- new_tokens_per_second = generated_tokens / generation_seconds
- sequence_tokens_per_second = completed_sequence_tokens / generation_seconds
- ms_per_step = denoising_seconds / denoising_steps
- tokens_resolved_per_step = newly_fixed_tokens / denoising_steps

Declarar si el tiempo incluye muestreo, tokenización, transferencia, detokenización y consola.

## 9. Plan de integración LEONES

### R0 — Catálogo y procedencia
Registrar proyectos, checkpoint IDs, licencias, formatos, revisiones y fechas. Añadir arquitectura, tamaño total/activo y estado de evidencia.

### R1 — Descubrimiento de runtimes
Inspeccionar capacidades reales de llama.cpp, diffuse-cpp y Transformers. Consultar TensorFold capabilities/recipes. Detectar soporte por arquitectura/modelo, no solo por extensión GGUF. Guardar versiones/commits.

### R2 — Primeras ejecuciones físicas
Ejecutar Open-dCoder 0.5B con Transformers si implementación/dependencias son compatibles. Preparar diffuse-cpp aislado y ejecutar Dream/LLaDA CPU. No interferir con servicios ODS/llama-server existentes. No intentar Clover/DiffusionGemma en la RTX 3050 para carga completa.

### R3 — Benchmarks comparables
Repetir tareas comunes en runtimes compatibles. Medir pasos, tokens resueltos, tokens nuevos/s, ms/paso, memoria y calidad. Comparar AR vs DLM con hardware y prompts equivalentes.

### R4 — Atlas / recomendador
Añadir DLM como familia distinta. Separar compatibilidad runtime de fit de memoria. Añadir modo de inferencia y coste de iteraciones. No recomendar ejecución basándose solo en parámetros activos o tamaño de archivo. Mantener estado ESTIMATED hasta ejecución.

## 10. Relevancia para REDIL

DLM pueden aportar generación, infilling y edición a nodos distribuidos. La difusión introduce retos:

- La secuencia parcial puede requerir estado compartido entre iteraciones.
- La división por bloques podría permitir asignar bloques a nodos, pero deben medirse dependencias.
- La latencia de comunicación puede anular el paralelismo de cálculo.
- Sincronizar máscaras, logits y estados tiene coste.
- La asignación de expertos MoE añade tráfico y memoria aunque haya pocos expertos activos.

Tratar DLM como backend experimental REDIL. Medir comunicación, sincronización, throughput agregado y calidad frente a nodo único. No asumir que el paralelismo interno implica escalabilidad distribuida.

## 11. Riesgos, correcciones y límites

1. No confundir parámetros activos con parámetros almacenados: MoE puede requerir alojar todos los expertos.
2. No confundir tamaño del archivo con VRAM total: hay buffers, activaciones, cachés y contexto.
3. No asumir Q4 universal: esquemas distintos tienen tamaño/calidad distintos.
4. No extrapolar rendimiento entre EPYC, A100 y RTX 3050.
5. No mezclar métricas: algunos benchmarks cuentan secuencia completa y otros tokens nuevos.
6. No asumir compatibilidad por extensión GGUF.
7. No declarar TensorFold compatible sin prueba; estado not-verified.
8. No tratar servicios comerciales/demos como open-weights.
9. No declarar mediciones LEONES antes de ejecución física.
10. Revisar nombres, tamaños, licencias y repositorios en cada actualización; registrar fecha y revisión.

## 12. Bibliografía y fuentes

### Catálogos y revisiones
- [Awesome Diffusion Language Models (VILA-Lab)](https://github.com/VILA-Lab/Awesome-DLMs)
- [Open-dLLM](https://github.com/pengzhangzhi/Open-dLLM)

### Modelos
- [LLaDA](https://github.com/ML-GSAI/LLaDA)
- [Dream](https://github.com/DreamLM/Dream)
- [Dream-Coder](https://github.com/DreamLM/Dream-Coder)
- [Apple DiffuCoder](https://github.com/apple/ml-diffucoder)
- [DiffuLLaMA](https://github.com/HKUNLP/DiffuLLaMA)
- [Clover-35B-A3B GGUF](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview-GGUF)
- [DiffusionGemma model card](https://ai.google.dev/gemma/docs/diffusiongemma/model_card)
- [LLaDA2.X](https://github.com/inclusionAI/LLaDA2.X)
- [RND1](https://github.com/RadicalNumerics/RND1)
- [ELYZA Dream](https://huggingface.co/elyza/ELYZA-Diffusion-Instruct-1.0-Dream-7B)

### Runtimes
- [llama.cpp diffusion examples](https://github.com/ggml-org/llama.cpp/tree/master/examples/diffusion)
- [diffuse-cpp](https://github.com/iafiscal1212/diffuse-cpp)
- [Transformers — DiffusionGemma](https://huggingface.co/docs/transformers/main/model_doc/diffusion_gemma)
- [TensorFold](https://github.com/ashhart/TensorFold)

### Fundamentos científicos
- [SEDD](https://arxiv.org/abs/2310.16834)
- [MDLM](https://arxiv.org/abs/2406.07524)
- [DiffusionBERT](https://arxiv.org/abs/2211.15029)
- [DiffuSeq](https://arxiv.org/abs/2210.08933)

### Benchmarks externos
- [diffuse-cpp — documentación y benchmarks](https://github.com/iafiscal1212/diffuse-cpp)
- [llama.cpp — benchmark Dream discussion #22972](https://github.com/ggml-org/llama.cpp/discussions/22972)

## 13. Estado LEONES

| Elemento | Estado |
|---|---|
| Catálogo de modelos | Investigación documental |
| Taxonomía de arquitecturas | Investigación documental |
| Matriz de memoria | ESTIMATED |
| Compatibilidad de runtimes | Evidencia documental; prueba física pendiente |
| Benchmarks diffuse-cpp / llama.cpp | Referencias externas |
| TensorFold | No acreditado |
| RTX 3050 / i7-12650H | Perfil conocido; DLM sin medir |
| Ejecución Open-dCoder | Pendiente |
| Ejecución Dream/LLaDA CPU | Pendiente |
| Comparación AR vs DLM | Pendiente |
| Integración Atlas/REDIL | Propuesta |

**Criterio de promoción:** ninguna fila de rendimiento o compatibilidad pasará a MEASURED hasta que exista un artefacto reproducible LEONES con hardware, versión, modelo, configuración, logs y resultados.
