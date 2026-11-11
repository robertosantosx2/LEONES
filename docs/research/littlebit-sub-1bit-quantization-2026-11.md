# LittleBit y LittleBit-2: investigación de cuantización sub-1-bit

**Fecha:** 2026-11-11  
**Área LEONES:** Quant / investigación de métodos de compresión  
**Estado:** investigación documental; sin integración ni ejecución local verificadas  
**Hardware objetivo de referencia:** MSI Thin 15 B12UC, Ubuntu, i7-12650H, RTX 3050 Laptop 4 GiB (SM86), 14 GiB RAM y 31 GiB swap.

## 1. Resumen ejecutivo

LittleBit propone comprimir matrices de pesos de LLM mediante factorización de bajo rango y factores binarios, en lugar de cuantizar directamente cada elemento de la matriz densa. LittleBit-2 mejora la preparación geométrica de los factores mediante rotación latente y Joint Iterative Quantization (Joint-ITQ).

La tecnología es relevante para LEONES Quant porque explora el régimen inferior a un bit por peso (BPW). No es, sin embargo, un formato universal de pesos ni un reemplazo directo de GGUF/GPTQ/AWQ: necesita un loader que conozca la representación, reconstrucción de capas y kernels adecuados. El tamaño teórico de los pesos tampoco equivale a la memoria total de inferencia.

**Dictamen:** incorporar al catálogo de investigación de cuantización y estudiar primero una reproducción pequeña con OPT-125M o Qwen3-0.6B. No declarar compatibilidad con llama.cpp, TensorFold, Kinetic, vLLM u Ollama hasta disponer de pruebas específicas.

## 2. Publicaciones

### LittleBit

- **Título:** *LittleBit: Ultra Low-Bit Quantization via Latent Factorization*.
- **Autores:** Banseok Lee, Dongkyu Kim, Youngcheon You y Youngmin Kim (Samsung Research).
- **Publicación:** NeurIPS 2025.
- **arXiv:** https://arxiv.org/abs/2506.13771
- **OpenReview:** https://openreview.net/forum?id=zJzu9evD5K
- **Actas NeurIPS:** https://proceedings.neurips.cc/paper_files/paper/2025/hash/a917c1d57088897beba47f96b4fd7f3c-Abstract-Conference.html
- **Explicación Samsung:** https://research.samsung.com/blog/LittleBit-Ultra-Low-Bit-Quantization-via-Latent-Factorization

### LittleBit-2

- **Título:** *LittleBit-2: Maximizing the Spectral Energy Gain in Sub-1-Bit LLMs via Latent Geometry Alignment*.
- **Autores:** Banseok Lee y Youngmin Kim.
- **Publicación:** ICML 2026; Proceedings of Machine Learning Research, volumen 306.
- **arXiv:** https://arxiv.org/abs/2603.00042
- **Actas PMLR:** https://proceedings.mlr.press/v306/lee26y.html
- **Explicación Samsung:** https://research.samsung.com/blog/LittleBit-2-Maximizing-the-Spectral-Energy-Gain-in-Sub-1-Bit-LLMs-via-Latent-Geometry-Alignment

## 3. Método

Para una matriz de pesos (W\in\mathbb{R}^{m\times n}), LittleBit aprende una aproximación de rango reducido:

\[
W\approx UV^\top
\]

Los factores se representan mediante sus signos binarios y escalas aprendidas:

\[
\widehat W =
\operatorname{diag}(h)\,
\operatorname{sign}(U)\,
\operatorname{diag}(\ell)\,
\operatorname{sign}(V)^\top\,
\operatorname{diag}(g)
\]

Las escalas por fila, columna y dimensión latente recuperan información de magnitud perdida al binarizar. El rango latente determina buena parte del compromiso entre tasa BPW y error de aproximación.

Elementos del método:

- **Dual-SVID:** inicialización basada en descomposición espectral para estabilizar el entrenamiento.
- **SmoothSign:** aproximación suave de la función signo durante el entrenamiento.
- **Multi-scale compensation:** escalas aprendidas para recuperar magnitudes.
- **Residual compensation:** ruta paralela para compensar error de aproximación.
- **QAT:** entrenamiento consciente de cuantización; no es una conversión post-entrenamiento trivial.

### LittleBit-2 / Joint-ITQ

LittleBit-2 alinea la geometría de los factores latentes con el hipercubo binario. Una rotación ortogonal interna conserva la reconstrucción antes de cuantizar, y Joint-ITQ busca una orientación que reduzca el error de asignación a signos binarios. La rotación y la optimización de inicialización se realizan en preparación/entrenamiento; no debe suponerse que añaden una etapa de inferencia por token.

## 4. BPW, tamaño y memoria

BPW (*bits per weight*) expresa una tasa media para los pesos contemplados por el método. No representa por sí sola el tamaño total del checkpoint ni el requisito de RAM/VRAM.

El cálculo idealizado (N\times BPW/8) solo estima el almacenamiento de los pesos contabilizados. Deben considerarse por separado:

- embeddings y `lm_head`, que pueden permanecer en BF16/FP16;
- factores, escalas, residuales y metadatos;
- formato real de serialización y alineamiento;
- memoria temporal de carga y ejecución;
- activaciones, workspace y caché KV;
- buffers de runtime y contexto.

Por tanto, cifras como “modelo de 13B por debajo de 1 GB” deben atribuirse a una configuración y contabilidad concretas del artículo, no presentarse como memoria total del sistema. En tasas muy bajas, los parámetros auxiliares y las partes no cuantizadas adquieren mayor peso relativo.

## 5. Repositorios y checkpoints

### Implementación oficial

- Repositorio: https://github.com/SamsungLabs/LittleBit
- Licencia indicada por el repositorio: CC BY-NC 4.0 (no comercial).
- Implementación PyTorch y kernels CUDA; scripts de entrenamiento y evaluación.
- Arquitecturas documentadas en el proyecto: OPT, Llama, Phi-4, Qwen2.5/QwQ, Gemma y Qwen3 (consultar README/commits para la cobertura exacta de cada script).
- La disponibilidad del código no implica que Samsung publique checkpoints oficiales entrenados.

### Reimplementación independiente

- Repositorio: https://github.com/mgiachetti/little-bit
- Licencia: MIT para esa implementación; las licencias de modelos y datasets siguen siendo independientes.
- Reimplementa LittleBit y LittleBit-2 en PyTorch.
- Añade una pérdida de destilación consciente de *attention sinks*, relevante para Qwen3.
- El README informa Qwen3-0.6B a 0,55 BPW: WikiText-2 PPL 36,43 tras unos 107 millones de tokens y PPL 30,64 tras aproximadamente 1.000 millones de tokens; referencia FP de PPL 20,95.
- El experimento de 107M tokens se reporta en una GTX 1080 de 8 GB durante 66,5 horas; la corrida larga se hizo en L40S.
- Limitación declarada: no incluye todavía un kernel de inferencia con empaquetado binario; los checkpoints almacenan latentes FP32 y el tamaño reportado se calcula mediante fórmula.

### Checkpoint comunitario Qwen3-8B

- Organización: https://huggingface.co/LittleBitLLM
- Modelo: https://huggingface.co/LittleBitLLM/littlebit-qwen3-8b-0.55bpw
- Proyecto comunitario independiente de Samsung.
- La ficha reporta Qwen3-8B a 0,55 BPW en capas lineales, con embeddings y `lm_head` BF16, y entrenamiento parcial de media época.
- La ficha informa entrenamiento con NVIDIA H200 SXM y evaluación con NVIDIA A40.
- Los resultados publicados muestran degradación sustancial respecto al modelo original (por ejemplo, WikiText-2 PPL 9,73 frente a 24,48 y ARC-Challenge 55,5% frente a 19,5%). Debe tratarse como checkpoint experimental, no como reemplazo funcional equivalente.

Portal comunitario: https://littlebitllm.com/

## 6. Compatibilidad de motores

Estado documental al 2026-11-11:

| Motor / entorno | Estado | Observación |
|---|---|---|
| PyTorch + implementación LittleBit | Disponible | Vía principal de entrenamiento/evaluación. |
| Transformers | Dependiente del loader | Verificar clase/modelo y formato exactos del checkpoint. |
| llama.cpp | No verificado | No asumir que GGUF estándar representa factores LittleBit. |
| Ollama | No verificado | Depende del soporte subyacente y del formato. |
| vLLM | No verificado | Requiere integración de capas/kernels compatibles. |
| TensorFold | No verificado | No consta backend LittleBit nativo. |
| Kinetic | No verificado | No consta parser/kernel LittleBit. |

Deben distinguirse tres niveles: lectura del artefacto, reconstrucción matemáticamente correcta de la capa y ejecución eficiente mediante kernels. Superar el primero no demuestra los otros dos.

## 7. Viabilidad en el MSI de referencia

Hardware conocido del equipo:

- Intel Core i7-12650H.
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM, Compute Capability SM86.
- 14 GiB RAM.
- 31 GiB swap.
- Ubuntu; CUDA toolkit instalado en el entorno local.

La swap puede evitar algunos fallos por falta de memoria, pero no sustituye VRAM ni RAM rápida. QAT requiere memoria para activaciones, gradientes, estados del optimizador y, en destilación, el modelo profesor. No se deben extrapolar los BPW del artefacto final a los requisitos de entrenamiento.

| Experimento | Evaluación preliminar en MSI |
|---|---|
| OPT-125M | Candidato recomendado para reproducibilidad. |
| Qwen3-0.6B | Posible investigación muy ajustada; reducir secuencia/batch y medir. No hay garantía de cabida. |
| Qwen3-4B | No recomendado como primer entrenamiento local en 4 GiB VRAM. |
| Qwen3-8B | No viable como entrenamiento local razonable en este equipo; checkpoint comunitario requiere loader específico. |
| Desarrollo de kernel CUDA SM86 | Viable como línea de ingeniería incremental, empezando por microbenchmarks y matrices pequeñas. |

## 8. Relación con LEONES Quant

La investigación encaja en el contrato de `quant/README.md` y `docs/CUANTIZACION.md`: método, modelo base, artefacto, runtime, hardware, métricas y evidencia deben quedar relacionados.

LittleBit debe registrarse como **método de cuantización/factorización entrenable**, no como formato de inferencia universal. Cada artefacto derivado deberá registrar:

- modelo base, revisión y tokenizer;
- arquitectura y capas transformadas;
- variante (LittleBit o LittleBit-2);
- BPW objetivo y BPW efectivo;
- rango por tipo de capa;
- tratamiento de embeddings y `lm_head`;
- compensación residual y escalas;
- datos, tokens, pasos, hiperparámetros y semilla;
- framework, versiones, CUDA y commit del código;
- hardware de entrenamiento y evaluación;
- tamaño real del artefacto y memoria máxima observada;
- PPL y benchmarks de calidad;
- runtime/loader y pruebas de inferencia;
- hashes y licencia.

Mantener los estados de LEONES: artefacto creado, validación pendiente, verificado o revisión. No declarar calidad preservada ni compatibilidad sin medición.

## 9. Plan de trabajo propuesto

1. **Documentación y trazabilidad:** registrar papers, repositorios, licencias y checkpoints en el catálogo Quant.
2. **Reproducción pequeña:** comenzar por OPT-125M con el repositorio independiente u oficial; fijar entorno y semilla.
3. **Qwen3-0.6B:** reproducir la receta sink-aware solo después de validar memoria y disponibilidad de datos.
4. **Evaluación:** comparar FP de referencia, LittleBit y LittleBit-2 con mismo tokenizer, dataset, secuencia y protocolo.
5. **Perfilado:** registrar RAM, VRAM, swap, tiempo de entrenamiento, tamaño de checkpoint, latencia y tokens/s.
6. **CUDA SM86:** medir primero kernels de signo/factorización y compararlos con FP16; no inferir aceleración de la tasa BPW.
7. **Integración de motor:** diseñar loader/runtime solo cuando exista artefacto reproducible y prueba de equivalencia de capas.

## 10. Tabla de modelos, motores y hardware

Los requisitos siguientes son orientativos; no equivalen a certificación de ejecución. Los tamaños GGUF son dependientes de la variante exacta y del archivo.

### Modelos LittleBit de interés

| Modelo / variante | Evidencia disponible | Motor o vía | Hardware de referencia / MSI |
|---|---|---|---|
| OPT-125M LittleBit 0,55 BPW | Ejemplo de entrenamiento en repositorio independiente | PyTorch | Candidato cómodo para comenzar; medir RAM/VRAM real |
| Qwen3-0.6B LittleBit-2 0,55 BPW | PPL 36,43 (107M tokens) y 30,64 (1B tokens) reportados por reimplementación | PyTorch, loader del proyecto | GTX 1080 8 GB para receta corta; MSI 4 GB muy ajustado |
| Qwen3-8B LittleBit-2 0,55 BPW | Checkpoint comunitario experimental | Loader específico de Hugging Face/proyecto | Entrenamiento reportado en H200; MSI no apto para entrenar |
| Llama 2 7B/13B/70B | Resultados en publicaciones | Código oficial y configuración correspondiente | No inferir que el tamaño comprimido permita entrenar/ejecutar en MSI |

### Motores locales conocidos en LEONES/MSI

| Motor | Modelos/formatos conocidos en el entorno | Estado para LittleBit | Hardware MSI |
|---|---|---|---|
| llama.cpp CUDA | GGUF; Qwen3.5-35B-A3B IQ2_XXS y TwIL-8B Q4_K_M probados | Sin soporte LittleBit verificado | RTX 3050 + CPU/offload; depende del modelo |
| TensorFold 1.2.3 | Qwen3.5-2B operativo; Qwen3.5-4B en validación/integración | Sin soporte LittleBit verificado | 4 GiB VRAM limita 4B y superiores |
| Kinetic | LFM3-1.7B y otros GGUF del inventario | Sin soporte LittleBit verificado | Adecuado para modelos pequeños compatibles |
| PyTorch LittleBit | OPT/Qwen3 según implementación | Vía de investigación | OPT-125M primero; Qwen3-0.6B experimental |
| vLLM / Ollama | No se registra aquí una prueba local específica | Sin integración verificada | No asignar requisito hasta seleccionar implementación |

### Referencias de modelos locales ya probados

| Modelo | Cuantización | Motor / resultado conocido |
|---|---|---|
| LiquidAI LFM3-1.7B | Q4_K_M | Kinetic, operativo |
| MiniCPM5-2B | GGUF Q4 | llama.cpp, pruebas CUDA |
| TwIL-8B | Q4_K_M | llama.cpp; benchmark alrededor de 2,73 tok/s en la configuración documentada |
| Qwen3.5-35B-A3B | IQ2_XXS | Tandem/llama.cpp; alrededor de 35,6 tok/s en configuración CPU-MoE documentada |
| Qwen3.5-2B | Formato TensorFold compatible | TensorFold CUDA, servidor operativo |
| Qwen3.5-4B | Formato TensorFold compatible | Validación de memoria; no confundir catálogo con ejecución satisfactoria |

Los resultados anteriores pertenecen a sesiones y configuraciones distintas; no constituyen comparación directa entre motores. Consultar los informes de benchmark de LEONES para los comandos, logs y hashes exactos.

## 11. Fuentes

1. https://arxiv.org/abs/2506.13771
2. https://openreview.net/forum?id=zJzu9evD5K
3. https://proceedings.neurips.cc/paper_files/paper/2025/hash/a917c1d57088897beba47f96b4fd7f3c-Abstract-Conference.html
4. https://arxiv.org/abs/2603.00042
5. https://proceedings.mlr.press/v306/lee26y.html
6. https://github.com/SamsungLabs/LittleBit
7. https://github.com/mgiachetti/little-bit
8. https://huggingface.co/LittleBitLLM/littlebit-qwen3-8b-0.55bpw
9. https://huggingface.co/LittleBitLLM
10. https://research.samsung.com/blog/LittleBit-Ultra-Low-Bit-Quantization-via-Latent-Factorization
11. https://research.samsung.com/blog/LittleBit-2-Maximizing-the-Spectral-Energy-Gain-in-Sub-1-Bit-LLMs-via-Latent-Geometry-Alignment

## 12. Limitaciones y control de calidad documental

- No se ha ejecutado LittleBit en el MSI durante esta investigación.
- No se ha validado ningún checkpoint LittleBit con llama.cpp, TensorFold o Kinetic.
- Los requisitos de hardware son estimaciones de planificación, salvo los experimentos de hardware expresamente atribuidos a sus autores.
- Los resultados comunitarios no deben atribuirse a Samsung.
- Las licencias de código, pesos y datasets deben revisarse por separado antes de redistribuir o integrar.
- Las menciones de redes sociales/Reddit no se utilizan como evidencia cuantitativa si no se puede verificar el perfil, publicación y contexto originales.

**Conclusión:** LittleBit/LittleBit-2 queda registrado como línea de investigación de LEONES Quant. El primer hito técnico propuesto es reproducir OPT-125M y medir el coste real; el segundo, estudiar Qwen3-0.6B y los kernels CUDA SM86. No se promueve todavía a backend de inferencia soportado.
