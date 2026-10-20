# Qwen3.5-4B: benchmark de cuatro motores — 2026-10-20

## Estado y alcance

Ejecución física en Ubuntu sobre el mismo equipo, con cuatro servidores de inferencia iniciados y detenidos secuencialmente. Cada motor completó tres peticiones medidas y una petición de calentamiento no contabilizada.

- **Equipo:** Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop GPU con 4 GiB VRAM, driver 580.178.04, CUDA 13.0.
- **Contexto configurado:** 256 tokens.
- **Salida:** máximo 32 tokens por petición; 30 tokens de prompt y 32 tokens generados en cada prueba medida.
- **Muestreo:** temperatura 0; mismo prompt y protocolo del script de benchmark.
- **Validación:** las 12 peticiones medidas devolvieron HTTP 200 y `finish_reason=length`; no se contabilizan como errores las métricas que un servidor no expone.
- **Ejecución local:** `~/qwen35-4b-benchmark-fixed-20261020-232655`.
- **Script:** `~/benchmarks/benchmark_qwen35_4b_three_engines_fixed_v2.sh`.
- **Artefactos:** TensorFold usa `mlx-community/Qwen3.5-4B-MLX-4bit`; Mistral.rs, llama.cpp y RustingStrata usan el GGUF Q4_K_M local.

## Resumen de medianas

| Motor | Pruebas válidas | Latencia total mediana | Generación mediana | Prefill mediano reportado | TTFT mediano |
|---|---:|---:|---:|---:|---:|
| TensorFold | 3/3 | 0,7079 s | **54,747 tok/s** | 231,150 tok/s | 0,1308 s |
| llama.cpp CUDA | 3/3 | 0,8860 s | 47,551 tok/s | 362,446 tok/s* | n/d |
| RustingStrata | 3/3 | 0,8416 s | n/d | n/d | n/d |
| Mistral.rs | 3/3 | 6,2367 s | 6,202 tok/s | 30,896 tok/s | n/d |

`n/d` significa que el cliente o la API no proporcionó una métrica comparable. `* ` El prefill de llama.cpp se deriva de los metadatos devueltos por el servidor; sus valores por petición variaron considerablemente (362,446; 175,374; 395,382 tok/s), por lo que no debe interpretarse como una medición independiente de prefill con condiciones idénticas.

## Mediciones por petición

| Motor | Prueba | HTTP | Prompt tokens | Tokens salida | Latencia total (s) | Generación (tok/s) | Prefill reportado (tok/s) | TTFT (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mistral.rs | 1 | 200 | 30 | 32 | 6,4725 | 6,202 | 26,690 | n/d |
| Mistral.rs | 2 | 200 | 30 | 32 | 6,1832 | 6,352 | 30,896 | n/d |
| Mistral.rs | 3 | 200 | 30 | 32 | 6,2367 | 6,119 | 35,587 | n/d |
| TensorFold | 1 | 200 | 30 | 32 | 0,7079 | 54,708 | 230,990 | 0,1308 |
| TensorFold | 2 | 200 | 30 | 32 | 0,7103 | 54,747 | 231,150 | 0,1308 |
| TensorFold | 3 | 200 | 30 | 32 | 0,7016 | 54,781 | 240,506 | 0,1258 |
| llama.cpp CUDA | 1 | 200 | 30 | 32 | 0,9552 | 47,551 | 362,446 | n/d |
| llama.cpp CUDA | 2 | 200 | 30 | 32 | 0,8860 | 46,214 | 175,374 | n/d |
| llama.cpp CUDA | 3 | 200 | 30 | 32 | 0,7589 | 47,651 | 395,382 | n/d |
| RustingStrata | 1 | 200 | 30 | 32 | 0,8516 | n/d | n/d | n/d |
| RustingStrata | 2 | 200 | 30 | 32 | 0,8416 | n/d | n/d | n/d |
| RustingStrata | 3 | 200 | 30 | 32 | 0,8391 | n/d | n/d | n/d |

## Interpretación

- **TensorFold fue el más rápido** en generación medida: mediana de 54,747 tok/s y latencia total de 0,7079 s.
- llama.cpp CUDA registró 47,551 tok/s de generación mediana y 0,8860 s de latencia total mediana.
- RustingStrata respondió correctamente en las tres pruebas, pero la API no expuso velocidad interna de generación, prefill ni TTFT. No se estima su tok/s dividiendo tokens por latencia.
- Mistral.rs registró 6,202 tok/s de generación mediana y 6,2367 s de latencia total mediana en esta configuración.
- No es una comparación estrictamente *apples-to-apples*: TensorFold utiliza MLX-4bit, mientras que los otros motores usan GGUF Q4_K_M. La compatibilidad, el reparto CPU/GPU, las plantillas y la instrumentación también pueden influir.
- Solo hay tres pruebas por motor y una salida máxima de 32 tokens. No se extrapola a generación larga, contextos amplios, carga concurrente, calidad ni eficiencia energética.
- La medición de prefill de llama.cpp es especialmente variable y no debe utilizarse para declarar un ganador de prefill entre motores.

## Incidencia de generación del informe

Las cuatro secuencias de inferencia finalizaron correctamente. La generación automática del informe falló después de las mediciones por un paréntesis sobrante en el bloque Python de resumen. Se reparó el generador y se reconstruyeron CSV y Markdown a partir del JSONL ya existente; **no se repitió el benchmark para corregir el informe**.

## Reproducibilidad y límites del artefacto

El JSONL original y los logs de servidor permanecen en el directorio local indicado arriba. Este informe y el CSV guardan las 12 pruebas medidas; no se afirma que los logs locales ni el JSONL completo se hayan subido a este repositorio.

## Siguiente paso

Evaluar vLLM como quinto motor mediante una prueba de viabilidad aislada antes de incorporarlo al benchmark. La compatibilidad de arquitectura no garantiza que la combinación de versión, formato de pesos y 4 GiB de VRAM pueda arrancar. Registrar cualquier intento fallido como incidencia y no como cero tokens/s.
