# Clover-35B-A3B-Preview en Ubuntu — informe de ejecución y benchmark

**Fecha:** 2026-10-31  
**Estado:** ejecución local confirmada; benchmark preliminar, no normalizado  
**Equipo:** MSI Thin 15 B12UC  
**Repositorio de evidencia:** [LEONES](https://github.com/robertosantosx2/LEONES)

## 1. Resumen ejecutivo

Se ha conseguido ejecutar **Clover-35B-A3B-Preview** en el MSI Thin 15 con Ubuntu, utilizando una compilación CUDA aislada de llama.cpp y la cuantización comunitaria GGUF **IQ2_S-exps-down3-hq**. La ruta de conversación funcional requiere una plantilla Jinja simplificada propia: el parser especializado Qwen3-Coder seleccionado automáticamente por la plantilla original del GGUF fallaba al procesar el prompt de completion.

La prueba conversacional más larga completada produjo 255 tokens de evaluación (con un máximo solicitado de 256), a **4,90 tokens/s** de generación y **3,60 tokens/s** de prefill. El proceso alcanzó **10.560.356 KiB** de RSS máximo (aprox. 10,08 GiB) y terminó con código 0.

Estos resultados son **MEASURED en este equipo y esta configuración**, pero siguen siendo preliminares: no hay todavía repeticiones suficientes para una media estadística, comparación normalizada entre motores ni evaluación independiente de calidad.

## 2. Equipo y entorno

Datos del equipo registrados durante las pruebas:

- Portátil MSI Thin 15 B12UC.
- CPU Intel Core i7-12650H; 16 CPU lógicas.
- RAM física: aproximadamente 14 GiB.
- GPU NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- Driver NVIDIA 580.178.04; CUDA 13.0 reportado por `nvidia-smi`.
- CUDA Toolkit utilizado para compilar: 13.4.92.
- Ubuntu; kernel 7.0.0-38-generic.
- Swap configurada en `/swap32.img` (32 GiB).

La máquina también tiene otros proyectos y runtimes instalados. Clover se compiló y probó en su propio directorio para no alterar ODS, Magnitude, TensorFold ni los servicios existentes.

## 3. Código y compilación

Directorio de trabajo:

```text
~/clover-35b-a3b-preview/
└── llama.cpp/
    └── build-clover-cuda/
```

- Rama: `clover-pr-31306`.
- HEAD: `cb09d4355d8bf968bb907c5de03cf42d8aa073ce`.
- Commit: `clover: performance fix`.
- Versión del binario: `0.7.0-dev (build 11955, commit cb09d4355)`.
- Arquitectura CUDA: 86 (RTX 3050).
- Compilador C++: GCC 15.2.
- CUDA Toolkit: 13.4.92.
- Binario empleado: `build-clover-cuda/bin/llama-completion`.

Configuración CMake usada:

```bash
cmake -S . -B build-clover-cuda \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-13.4/bin/nvcc \
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++ \
  -DCUDAToolkit_ROOT=/usr/local/cuda-13.4 \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
  -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_SERVER=OFF \
  -DCMAKE_BUILD_TYPE=Release
```

El proyecto incorporaba la implementación Clover en `src/models/clover-moe.cpp` y la arquitectura `LLM_ARCH_CLOVER_MOE`.

## 4. Modelo y cuantización

- Modelo: `Clover-35B-A3B-Preview`.
- Repositorio de la cuantización: [na0x2c6/Clover-35B-A3B-Preview-GGUF](https://huggingface.co/na0x2c6/Clover-35B-A3B-Preview-GGUF).
- Archivo: `Clover-35B-A3B-Preview-IQ2_S-exps-down3-hq.gguf`.
- Tamaño exacto registrado: 13.795.534.208 bytes (aprox. 13,80 GB decimales).
- Ruta local: `~/clover-35b-a3b-preview/models/Clover-35B-A3B-Preview-IQ2_S-exps-down3-hq.gguf`.
- Model card: licencia declarada Apache-2.0; modelo base indicado como [Diffuspace/Clover-35B-A3B-Preview](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview).

La ficha del modelo describe una arquitectura de 35B parámetros totales y aproximadamente 3B activos por token, con 40 capas, 256 expertos enrutados, top-8, un experto compartido por capa y una combinación de Gated DeltaNet y atención completa. Se describe contexto de hasta 128K y entrenamiento/inferencia de tipo block-diffusion. Estos datos proceden de la ficha y metadatos publicados, no de una inspección independiente de todos los tensores.

La cuantización IQ2_S es agresiva. El repositorio comunitario publica KLD medio 0,1499 y top-1 agreement 83% respecto a BF16. Estas cifras son indicadores de similitud de cuantización, no resultados de benchmarks de tareas ni una medida directa de calidad conversacional.

Como referencia, las cuantizaciones publicadas de mayor tamaño (Q8_0, Q6_K, Q4_K_M, IQ4_XS, Q3_K_M y Q3_K_S) exceden la RAM física de 14 GiB del equipo. La cuantización IQ2_S elegida permite probar el modelo con mmap y paginación, pero con coste apreciable de memoria y almacenamiento.

## 5. Problema de plantilla y solución

### 5.1 Fallo con la plantilla original

La plantilla incluida en el GGUF contiene marcadores compatibles con el formato Qwen3-Coder. La detección automática de llama.cpp seleccionó el parser especializado Qwen3-Coder al encontrar, en el template source, los marcadores `<tool_call>`, `<function=` y `<parameter=`.

Al intentar la ruta Jinja con la plantilla original se produjo:

```text
Jinja Exception: No user query found in messages.
```

La traza pasaba por `common_chat_params_init_qwen3_coder`, `common_chat_templates_apply_jinja` y `llama_completion`. Añadir `--skip-chat-parsing` no evitó la selección del parser especializado.

### 5.2 Plantilla simplificada funcional

Se creó el archivo local:

`~/clover-35b-a3b-preview/clover-chat-no-thinking.jinja`

Contenido:

```jinja
{%- for message in messages %}
{{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>\\n' }}
{%- endfor %}
{%- if add_generation_prompt %}
{{- '<|im_start|>assistant\\n' }}
{%- if enable_thinking is defined and enable_thinking is false %}
{{- '<think>\\n\\n</think>\\n\\n' }}
{%- else %}
{{- '<think>\\n' }}
{%- endif %}
{%- endif %}
```

La plantilla no contiene los marcadores que activaban la detección Qwen3-Coder. Conserva el formato básico de mensajes `<|im_start|>` / `<|im_end|>` y el prefijo de generación de assistant.

**Limitación:** es una plantilla mínima de conversación de texto. No pretende reproducir todas las capacidades del template original, en particular la serialización de herramientas y otras ramas especiales.

### 5.3 Razonamiento

Se ejecutaron las opciones `--reasoning off` y `--reasoning-format none`, pero el modelo siguió generando contenido entre `<think>` y `</think>`. En una de las pruebas, ese contenido ocupó buena parte del presupuesto de salida. Por tanto, no se ha demostrado que el razonamiento interno quede desactivado; las opciones de parser/formato no deben confundirse con una garantía de que el modelo no genere esos tokens.

## 6. Resultados experimentales

Los valores siguientes son los que imprimió llama.cpp. Las pruebas tienen prompts, longitudes y modos diferentes, por lo que no constituyen una comparación perfectamente controlada.

| Prueba | Modo | Tokens evaluados/generados | Prefill | Generación | Carga | Tiempo total |
|---|---|---:|---:|---:|---:|---:|
| Primera prueba | speculative, draft-self | 17 | 2,36 t/s | 0,438 t/s | 21,94 s | 50,27 s |
| Segunda prueba | speculative, draft-self | 129 | 2,44 t/s | 0,402 t/s | 25,07 s | 332,02 s |
| Convencional sin conversación | no-conversation | 127 | 2,21 t/s | 2,68 t/s | 20,67 s | 58,03 s |
| Conversación, reasoning activado | chat | 47 | 2,64 t/s | 2,41 t/s | 23,42 s | 42,44 s |
| Conversación, reasoning off | chat | 95 | 2,64 t/s | 2,60 t/s | 23,75 s | 59,57 s |
| Conversación, budget 0 | chat | 127 | 2,71 t/s | 3,19 t/s | 28,15 s | 62,22 s |
| Plantilla Jinja personalizada | chat | 95 | 2,79 t/s | 5,15 t/s | 20,82 s | 41,58 s |
| Plantilla Jinja personalizada | chat | 255 | 3,60 t/s | 4,90 t/s | 20,39 s | 74,95 s |

### 6.1 Prueba Jinja de 96 tokens

- Prompt: explicación de Mixture of Experts y router.
- Sistema: responder en español, con precisión.
- Contexto: 256.
- Batch: 16; ubatch: 8.
- CPU: 4 threads; batch threads: 4.
- GPU offload: `-ngl 1`.
- KV cache: K y V en `q8_0`.
- Flash Attention: activada.
- Temperatura: 0; seed solicitado: 42.
- Salida: respuesta en español con estructura Markdown.
- Carga: 20.821,56 ms.
- Prefill: 22.945,68 ms / 64 tokens = 2,79 t/s.
- Eval: 18.449,00 ms / 95 runs = 5,15 t/s.
- Total: 41.582,48 ms / 159 tokens.
- Grafos reutilizados: 94; reasignaciones: 0.

### 6.2 Prueba Jinja de 256 tokens

- Prompt: explicación detallada de Clover, MoE, router, expertos compartidos y especializados.
- Contexto: 512.
- Resto de configuración igual que la prueba anterior.
- Salida: 255 runs de evaluación; el texto mostró una respuesta prudente, reconociendo que no tenía información fiable sobre el modelo específico y evitando inventar detalles.
- Carga: 20.392,00 ms.
- Prefill: 22.527,03 ms / 81 tokens = 3,60 t/s.
- Eval: 52.005,32 ms / 255 runs = 4,90 t/s.
- Total: 74.952,40 ms / 336 tokens.
- Grafos reutilizados: 254; reasignaciones: 1.
- RSS máximo: 10.560.356 KiB (aprox. 10,08 GiB).
- CPU: 247% de media durante 1:39,65.
- Page faults mayores: 66.820; menores: 443.539.
- Exit status: 0.
- Señales entregadas: 0.

El dato `Swaps: 0` de `/usr/bin/time` es una estadística del proceso y no debe interpretarse como prueba de que el sistema no utilizó swap en ningún momento.

## 7. Configuración reproducible de la prueba Jinja

Comando de la prueba larga:

```bash
cd ~/clover-35b-a3b-preview/llama.cpp

MODEL="$HOME/clover-35b-a3b-preview/models/Clover-35B-A3B-Preview-IQ2_S-exps-down3-hq.gguf"
TEMPLATE="$HOME/clover-35b-a3b-preview/clover-chat-no-thinking.jinja"

timeout --signal=INT --kill-after=10s 180s \
  /usr/bin/time -v \
  build-clover-cuda/bin/llama-completion \
  -m "$MODEL" \
  --single-turn \
  --load-mode mmap \
  --jinja \
  --chat-template-file "$TEMPLATE" \
  --reasoning off \
  --reasoning-format none \
  -ngl 1 \
  -c 512 \
  -b 16 \
  -ub 8 \
  -t 4 \
  -tb 4 \
  -ctk q8_0 \
  -ctv q8_0 \
  --flash-attn on \
  -sys "Eres un asistente técnico. Responde siempre en español, con precisión y sin mostrar razonamiento interno." \
  -p "Explica detalladamente cómo funciona Clover-35B-A3B-Preview, su arquitectura Mixture of Experts, el router, los expertos compartidos y especializados, y las ventajas y limitaciones de esta arquitectura." \
  -n 256 \
  --temp 0 \
  --seed 42 \
  --perf \
  2>&1 | tee ~/clover-35b-a3b-preview/clover-jinja-256-token-test.log
```

## 8. Interpretación y límites

1. **Viabilidad:** se ha confirmado que esta cuantización del modelo puede cargar y generar texto en el MSI Thin 15 con 14 GiB de RAM y RTX 3050 de 4 GiB, utilizando mmap, offload CUDA limitado y paginación.
2. **Velocidad:** el resultado largo de conversación es 4,90 t/s de generación y 3,60 t/s de prefill. La prueba corta obtuvo 5,15 t/s. Son medidas observadas, no una promesa de rendimiento constante.
3. **Memoria:** el RSS máximo medido en la prueba larga fue aproximadamente 10,08 GiB. No equivale al consumo total del sistema ni incluye necesariamente todas las páginas mapeadas/compartidas.
4. **Calidad:** no se ha realizado una batería de evaluación formal. La respuesta sobre Clover mostró prudencia epistémica, pero no valida conocimiento factual de su arquitectura.
5. **Cuantización:** IQ2_S puede afectar a la calidad. No se ha comparado aquí con BF16 ni con cuantizaciones de mayor precisión.
6. **Especulación:** las pruebas draft-self dieron 0,40–0,44 t/s; en esta configuración fueron mucho más lentas que la ruta conversacional Jinja. No se debe presentar el 100% de aceptación de las pocas propuestas como evidencia robusta de ventaja especulativa.
7. **Comparabilidad:** prompts, longitudes, contexto y rutas de ejecución variaron. Para un benchmark formal deben fijarse las mismas condiciones, realizar calentamiento y varias repeticiones, y publicar media/mediana y dispersión.
8. **Integridad:** no se modificó el GGUF ni se alteraron los servicios ODS, Magnitude, TensorFold o Hermes.

## 9. Archivos de evidencia local

Los siguientes artefactos se generaron en el equipo durante el experimento:

- `~/clover-35b-a3b-preview/clover-chat-no-thinking.jinja` — plantilla Jinja mínima funcional.
- `~/clover-35b-a3b-preview/clover-custom-template-test.log` — salida de la prueba Jinja de 96 tokens.
- `~/clover-35b-a3b-preview/clover-jinja-256-token-test.log` — salida de la prueba Jinja de 256 tokens.
- `~/clover-35b-a3b-preview/clover-128-token-run.log` — prueba especulativa de 128 tokens.
- `~/clover-35b-a3b-preview/models/Clover-35B-A3B-Preview-IQ2_S-exps-down3-hq.gguf` — modelo descargado.

Estos ficheros permanecen en el equipo local; este informe no afirma que los logs o el GGUF se hayan subido al repositorio.

## 10. Próximas acciones recomendadas

- Repetir al menos tres veces la prueba Jinja de 256 tokens, conservando configuración y prompt idénticos.
- Registrar temperatura, consumo VRAM y RAM del sistema durante toda la ejecución.
- Separar tiempo de carga, prefill y decode en los informes comparativos LEONES.
- Evaluar calidad con preguntas de conocimiento general y tareas reproducibles; suministrar documentación de Clover cuando se evalúe conocimiento específico del modelo.
- Comparar con otros motores solo cuando la misma cuantización, prompt, contexto y límites estén disponibles.
- Mantener claramente separados los resultados **MEASURED** del hardware local y los datos **ESTIMATED** o publicados por terceros.

---

**Conclusión:** Clover-35B-A3B-Preview se ha ejecutado correctamente en Ubuntu sobre el MSI Thin 15. El mejor resultado conversacional medido hasta ahora es 4,90 tokens/s de generación, 3,60 tokens/s de prefill y 10,08 GiB de RSS máximo en la prueba de 256 tokens. La plantilla Jinja simplificada resuelve el bloqueo de la ruta de conversación, pero la calidad y la reproducibilidad estadística aún requieren más pruebas.
