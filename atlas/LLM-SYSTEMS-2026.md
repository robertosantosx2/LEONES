# LLM Systems 2026 — criterios técnicos para Atlas

**Estado:** integrado como documento de conocimiento técnico.

**Fuentes de entrada:**
- *Serie de Modelos de Lenguaje de Gran Escala (LLM) de Cero a Héroe*, Ahmad (@TheAhmadOsman), compilada en agosto de 2026 y aportada al proyecto.
- *Estudio-de-llms.txt*, que apunta a la comparativa de modelos locales de coding de Kilo Code: https://blog.kilo.ai/p/the-best-local-coding-models-for

> Este documento conserva la separación entre evidencia de terceros y resultados propios de LEONES. Los datos externos sirven para hipótesis, selección de candidatos y diseño experimental; no se convierten automáticamente en benchmarks oficiales LEONES.

## 1. Memoria: CABE no significa RULA

Para estimar si un modelo puede entrar en memoria se adopta como aproximación inicial:

`VRAM (GB) ≈ parámetros (B) × bits efectivos por peso / 8`

Referencias de la fuente:

- FP16/BF16 ≈ 2 GB por 1B de parámetros.
- FP8/INT8 ≈ 1 GB por 1B.
- 4-bit ≈ 0,5 GB por 1B.
- GGUF depende de la cuantización: Q6_K ≈ 0,82; Q5_K ≈ 0,69; Q4_K ≈ 0,56; Q3_K ≈ 0,43; Q2_K ≈ 0,33 GB por 1B.

La huella real debe incorporar caché KV, activaciones, batching/concurrencia y overhead del runtime. La fuente recomienda reservar aproximadamente 10–30 % adicional de VRAM para una ejecución segura, y más para contexto largo, concurrencia o agentes.

**Aplicación Atlas:** `fit/CABE` no debe decidirse solo por tamaño de pesos. Debe distinguir memoria de pesos, KV, overhead y margen de seguridad.

## 2. Ancho de banda: el segundo eje obligatorio

La fuente establece el modelo:

`hardware de IA local = capacidad × ancho de banda × pila de software`

La capacidad determina qué puede entrar; el ancho de banda condiciona especialmente la velocidad de decode; el software determina cuánto del hardware puede aprovecharse realmente.

Esto es especialmente importante para el recomendador porque una máquina con mucha memoria pero poco ancho de banda puede ser capaz de ejecutar un modelo y, sin embargo, resultar poco usable.

**Aplicación Atlas:** separar siempre:

1. capacidad de memoria;
2. ancho de banda;
3. backend/runtime;
4. rendimiento observado.

No sustituir estos campos por una única puntuación de hardware.

## 3. Prefill frente a decode

La inferencia tiene dos fases con cuellos de botella distintos:

- **Prefill:** procesa el prompt; es más intensivo en cómputo y condiciona TTFT.
- **Decode:** genera token a token; suele estar limitado por ancho de banda de memoria y condiciona la fluidez del streaming.

Por tanto, `tokens_per_second` por sí solo no describe una configuración completa.

Para futuras evaluaciones Atlas/LEONES deben conservarse, cuando estén disponibles:

- TTFT;
- TPOT;
- tokens/s;
- memoria utilizada;
- concurrencia;
- longitud de entrada/salida;
- modelo + cuantización + runtime + versión.

## 4. Runtime como parte del modelo ejecutable

La fuente insiste en que un formato de pesos no implica un consumo universal de memoria ni el mismo rendimiento en todos los runtimes.

Mapa de decisión de la fuente:

| Escenario | Runtime orientativo |
|---|---|
| CPU, edge, hardware heterogéneo, GGUF | llama.cpp |
| Apple Silicon | MLX / MLX-LM |
| GPU NVIDIA de consumo, una GPU | ExLlamaV2 / llama.cpp |
| 2–4+ NVIDIA | ExLlamaV3 / vLLM / SGLang |
| Servicio general | vLLM |
| Contexto largo / MoE / routing complejo | SGLang |
| Máximo rendimiento NVIDIA datacenter | TensorRT-LLM |
| Intel | OpenVINO / ONNX Runtime GenAI |
| Navegador/móvil | MLC / WebLLM / ONNX Runtime GenAI |

Esto no constituye una recomendación absoluta de LEONES. Es un mapa de hipótesis para seleccionar el backend correcto antes de comparar resultados.

## 5. MoE: parámetros totales frente a parámetros activos

En modelos MoE:

- los **parámetros totales** condicionan la huella de memoria;
- los **parámetros activos** condicionan en mayor medida el coste de cómputo por token.

Atlas no debe tratar una etiqueta como `8x7B` como si fuera automáticamente equivalente a un modelo denso de 56B en todas las dimensiones.

## 6. Cuantización

La fuente propone como regla práctica de 2026:

- FP16/BF16: máxima calidad base;
- Q8/INT8: pérdidas generalmente pequeñas con mayor coste de memoria;
- Q6/Q5: buena relación calidad/ahorro;
- Q4: equilibrio predeterminado para consumo;
- Q3/Q2: solo cuando sea necesario para hacer CABE un modelo mayor.

Debe distinguirse **cuantización de pesos** de **cuantización de KV cache**.

Una cuantización agresiva no debe convertirse automáticamente en una ventaja del recomendador: debe comprobarse la pérdida de calidad en la carga de trabajo real.

## 7. Selección: modelo que gana la carga real

La regla central aportada por la fuente es:

> No elegir «el mejor modelo» en abstracto, sino el modelo más pequeño que gana la carga de trabajo real en el hardware real.

La metodología propuesta es:

1. filtrar por memoria/CABE;
2. filtrar por compatibilidad de runtime;
3. ejecutar una batería representativa de 20–50 prompts o tareas;
4. medir calidad, latencia, memoria y fiabilidad;
5. conservar los fallos, no solo la media.

Esto encaja directamente con la separación LEONES entre benchmark de inferencia y evaluación agentiva.

## 8. Evaluación limpia

La sexta pieza de la serie establece una regla metodológica crítica: un conjunto de prueba deja de ser un conjunto de prueba si se optimiza repetidamente contra él.

Para Atlas/LEONES:

- benchmarks públicos → evidencia externa / hipótesis;
- evaluación de desarrollo → instrumento de iteración;
- evaluación final/auditoría → protocolo congelado;
- resultados LEONES → deben registrar modelo, versión, hardware, cuantización, backend, parámetros y protocolo.

Debe evitarse presentar una puntuación externa como resultado propio.

## 9. Consecuencia para el recomendador JGB

El JGB debe seguir siendo un criterio independiente de la velocidad y del ranking económico.

La información de esta fuente se incorpora como **evidencia técnica de soporte**, no como sustitución del criterio JGB ni como una nueva puntuación opaca.

En particular:

- JGB responde a la dimensión de libertad/apertura definida por LEONES.
- CABE responde a la posibilidad material de ejecutar.
- RULA responde a la ejecución real.
- rendimiento observado responde a la medición experimental.
- precio observado responde al coste económico documentado.
- evidencia externa sirve para priorizar candidatos y diseñar pruebas.

La recomendación final debe conservar estas dimensiones separadas y trazables.

## 10. Regla de oro para Atlas

`modelo × cuantización × runtime × hardware × carga de trabajo × protocolo`

es la unidad correcta de comparación experimental.

Un nombre de modelo aislado no es una configuración reproducible.

---

**Nota de procedencia:** el contenido técnico anterior es una síntesis del material aportado por el usuario. No se han convertido en hechos propios de LEONES las cifras de rendimiento o compatibilidad que no hayan sido medidas por el proyecto.
