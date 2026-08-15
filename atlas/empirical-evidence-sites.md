# Atlas — Sitios de evidencia empírica

## Objetivo

Registro de fuentes que aportan observaciones, mediciones, evaluaciones reproducibles o datos suficientemente detallados para generar **hipótesis de recomendación**.

Una fuente empírica no convierte automáticamente sus datos en mediciones LEONES. Los resultados se conservan como `external_evidence` y se etiquetan según método, fecha, condiciones y reproducibilidad.

## 1. Evaluación y benchmarks principales

| Fuente | URL | Qué evalúa | Uso inicial |
|---|---|---|---|
| LMSYS Chatbot Arena | https://chat.lmsys.org/ | Evaluación ciega cara a cara (humana y por votos ELO) de modelos en tiempo real | hipótesis de calidad/preferencia; no rendimiento de hardware |
| Open LLM Leaderboard (Hugging Face) | https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard | Pruebas empíricas automatizadas sobre modelos open source, incluyendo razonamiento, matemáticas y seguimiento de instrucciones | hipótesis de capacidad/calidad; no inferencia local |
| LLM Stats | https://llm-stats.com/benchmarks | Comparativas de métricas empíricas entre cientos de modelos en razonamiento (GPQA, SWE-bench, MMLU-Pro), visión y código | contraste y generación de hipótesis |
| Model Spend Arena (MSA) | https://msa.millaguie.net/ | Análisis y observaciones de modelos, incluyendo mediciones de ejecución local cuando se publican | hipótesis de modelo/runtime/quant/hardware |

## 2. Rendimiento, latencia y costes

| Fuente | URL | Qué evalúa | Uso inicial |
|---|---|---|---|
| Artificial Analysis | https://artificialanalysis.ai/ | Datos empíricos sobre latencia (TTFT), velocidad de generación (tokens/segundo), coste por millón de tokens y precisión en pruebas de referencia | hipótesis comparativas de rendimiento/coste |
| Vellum LLM Leaderboard | https://www.vellum.ai/llm-leaderboard | Métricas combinadas de rendimiento empírico en razonamiento, ventanas de contexto y costes de inferencia | hipótesis comparativas |
| Lambda LLM Benchmarks | https://lambda.ai/llm-benchmarks-leaderboard | Rendimiento de modelos ejecutados en infraestructura estandarizada en tareas de programación y conocimiento general | hipótesis de capacidad bajo infraestructura controlada |

## 3. Agentes, código y razonamiento complejo

| Fuente | URL | Qué evalúa | Uso inicial |
|---|---|---|---|
| SWE-bench (Princeton / Yale) | https://www.swebench.com/ | Capacidad empírica para resolver issues y errores reales de código en repositorios de GitHub | hipótesis agentic/coding |
| LiveCodeBench | https://livecodebench.github.io/ | Desempeño en problemas de programación actualizados continuamente para reducir la contaminación de datos de entrenamiento | hipótesis coding/reasoning |

## Fuentes prioritarias de descubrimiento

Además de las fuentes anteriores, Atlas debe consultar como primera capa de descubrimiento y evidencia externa:

- https://huggingface.co/open-llm-leaderboard
- https://huggingface.co/docs/leaderboards/en/index
- https://huggingface.co/datasets/open-llm-leaderboard/results
- https://huggingface.co/datasets/open-llm-leaderboard/contents
- Artificial Analysis
- LMSYS Chatbot Arena
- sitio/blog oficial del fabricante

El orden inicial de descubrimiento de modelos será preferentemente: **Hugging Face → LMSYS/Chatbot Arena → Artificial Analysis → fabricante**, complementado por las fuentes empíricas especializadas de este fichero.

## Hugging Face: qué cuenta como prueba

Hugging Face sí dispone de una infraestructura formal de **Leaderboards and Evaluations**. La documentación distingue resultados de evaluaciones oficiales, community-managed leaderboards y el Open LLM Leaderboard.

https://huggingface.co/docs/leaderboards/en/index

El Open LLM Leaderboard fue diseñado para evaluaciones comparables y reproducibles; su documentación conserva resultados y detalles por modelo.

https://huggingface.co/docs/leaderboards/open_llm_leaderboard/archive

Importante: los resultados clásicos del Open LLM Leaderboard se ejecutaron en 8 H100 en una configuración controlada. Por tanto son evidencia de **capacidad comparativa bajo un protocolo concreto**, no evidencia de tok/s en hardware de consumo.

https://huggingface.co/docs/leaderboards/open_llm_leaderboard/archive

También debe conservarse la precisión/commit: HF documenta que el mismo modelo puede aparecer con distinta precisión (por ejemplo fp16 y 4bit), lo que es relevante para Atlas.

https://huggingface.co/docs/leaderboards/open_llm_leaderboard/faq

## Evidencia local/empírica destacada: Model Spend Arena

MSA se incorpora como fuente prioritaria porque publica observaciones propias además de agregación de datos. En su página declara que los datos están fechados y que el sitio distingue datos agregados de mediciones propias.

https://msa.millaguie.net/

Ejemplos observados el 2026-08-14:

- Nemotron 3.5 Lightning: 30B MoE / 3B activos; 34.7% en BigCodeBench-Hard, medido por el sitio.
- Qwen3.8-27B: en una GPU de 16 GB, Q3 de ~14 GB; ~36 tok/s con MTP speculative decoding mediante llama-server frente a ~18 tok/s sin speculative decoding; aproximadamente 87% de aceptación de drafts según la observación publicada.
- El mismo artículo señala una penalización de calidad al usar Q3 en 16 GB frente a precisiones mayores.

Estos datos se almacenarán como `external_evidence` con fuente, fecha, claim y condiciones. No se copiarán como `verified` automáticamente.

## Política de hipótesis

Los datos empíricos externos pueden producir **HYPOTHESIS**, no recomendaciones definitivas.

Ejemplo:

`Qwen3.8-27B + Q3 + llama-server + 16GB GPU + MTP → candidato a RULA interactivo`

La hipótesis se puede puntuar por:

- evidencia independiente;
- antigüedad;
- detalle de hardware;
- detalle de runtime/versión;
- cuantización;
- workload;
- reproducibilidad;
- distancia respecto del hardware objetivo.

Una hipótesis solo se convierte en recomendación Atlas/LEONES cuando la evidencia disponible cumple las reglas de confianza correspondientes.

## Separación obligatoria

`external_evidence` ≠ `LEONES measurement`

`external_evidence` ≠ `MANADA report`

`benchmark score` ≠ `tok/s`

`CABE` ≠ `RULA`

Una evaluación HF puede decir que un modelo es fuerte en una tarea; MSA puede aportar una observación de ejecución; MANADA puede aportar una medición de una máquina; y LEONES puede reproducirla. Son evidencias distintas y deben permanecer separadas.
