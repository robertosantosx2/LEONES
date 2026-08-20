# Evidencia real de LLMFit — Intel i5-1035G1 / 8 GB / Intel Iris Plus

**Fecha de observación:** 20 de agosto de 2026

## Fuente

Captura textual proporcionada desde una ejecución real de LLMFit en una máquina Debian de referencia de LEONES.

## Hardware observado

| Campo | Valor observado |
|---|---|
| CPU | Intel Core i5-1035G1 @ 1.00 GHz |
| CPU cores | 8 |
| RAM total | 7.0 GB |
| RAM disponible durante la captura | 0.7 GB |
| GPU | Intel Iris Plus Graphics G1 (Ice Lake), integrada |
| Memoria GPU | 7.0 GB compartida |
| Backend GPU detectado | SYCL |
| Ollama | no disponible |
| MLX | no disponible |
| llama.cpp | no disponible en PATH |
| Docker | no disponible |
| LM Studio | no disponible |
| vLLM | no disponible |
| RamaLama | no disponible |
| Modelos ocultos por backend incompatible | 2.413 |

## Observación del ranking

La ejecución mostró, entre otros, los siguientes candidatos con `Perfect` bajo la estimación de LLMFit:

| Modelo mostrado | Parámetros | Estimación tok/s | Cuantización | Memoria de modelo | Uso |
|---|---:|---:|---|---:|---|
| khazarai/Qwen3-4B-Qwen3.6-plus-Reasoning | 3.1B | 28.2 | Q8_0 | 3.3 GB | Reasoning |
| khazarai/Qwen3-4B-Kimi2.5-Reasoning | 3.1B | 28.2 | Q8_0 | 3.3 GB | Reasoning |
| taobao-mnn/Qwen3-VL-8B-Instruct-Easy | 1.4B | 61.2 | Q8_0 | 1.5 GB | Chat |
| hyeonq3/Qwen3-1.7B-base-MED-ChatVe | 1.7B | 51.1 | Q8_0 | 1.8 GB | Chat |
| taide/embeddinggemma-GTAIDE-300m-2 | 303M | 291 | Q8_0 | 0.3 GB | Embedding |
| argilla/Llama-3.2-1B-Instruct-APIGen-FC | 1.1B | 82.4 | Q8_0 | 1.1 GB | Chat |
| microsoft/Phi-4-mini-flash-reasoning | 3.9B | 22.8 | Q8_0 | 4.0 GB | Reasoning |
| meta-llama/Llama-3.2-1B-Instruct | 1.2B | 71.2 | Q8_0 | 1.3 GB | Chat |

## Interpretación LEONES

Esta observación es útil, pero **no constituye todavía un benchmark**.

La cifra más importante para la primera decisión no es el `Score`, sino la combinación:

```text
memoria libre real
+ memoria requerida
+ backend disponible
+ fit
+ caso de uso
+ estimación tok/s
```

En esta captura la máquina dispone de solo **0,7 GB de RAM libre**. Por tanto, aunque LLMFit marque determinados modelos como `Perfect`, no se debe presentar esa etiqueta como garantía de ejecución estable en el estado actual del sistema.

Además, LLMFit informa de que `llama.cpp` no está en PATH y no hay Ollama, vLLM ni LM Studio disponibles. Por ello, antes de convertir cualquiera de las estimaciones en recomendación operativa, LEONES debe instalar/activar un runtime compatible y medir.

## Decisión inicial

Para esta máquina, LEONES utilizará LLMFit como **preselector** y reservará la validación final para una medición real. La campaña inicial debe priorizar modelos pequeños y cuantizados, empezando por una familia alrededor de 1B y escalando hacia 3–4B solo si la memoria libre y el runtime lo permiten.

La comparación que interesa registrar es:

```text
LLMFIT estimated_tps
        vs
LEONES measured_tps
        ↓
error / ratio de calibración
```

Una medición real debe conservar el hardware, runtime, versión, cuantización, contexto, TTFT si está disponible, tok/s y resultado de estabilidad.

## Próximo ensayo

1. Capturar `llmfit --json system`.
2. Capturar `llmfit recommend --json --limit 10` para `chat`, `reasoning`, `coding` y `embedding`.
3. Instalar un runtime compatible con esta plataforma.
4. Ejecutar una inferencia mínima y reproducible.
5. Comparar `estimated_tps` con `measured_tps`.
6. Guardar la desviación como evidencia de calibración de hardware.
7. Repetir con un segundo modelo de tamaño superior.

Esta evidencia no debe mezclarse con las mediciones de otras máquinas: el hardware es parte de la identidad de la observación.
