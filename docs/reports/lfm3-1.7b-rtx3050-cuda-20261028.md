# LFM3-1.7B Q4_K_M en RTX 3050 Laptop: benchmark CUDA

- **Fecha:** 2026-10-28
- **Proyecto:** LEONES
- **Modelo:** LiquidAI/LFM3-1.7B-GGUF, `LFM3-1.7B-Q4_K_M.gguf`
- **Tamaño informado por llama-bench:** 1,02 GiB
- **Parámetros:** 1,73 B
- **Motor:** llama.cpp con backend CUDA
- **Revisión de compilación:** `c3df4b7`
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU, compute capability 8.6
- **VRAM detectada por llama.cpp:** 3768 MiB
- **Capas GPU solicitadas:** 99
- **Hilos CPU:** 6
- **Repeticiones:** 3
- **Pruebas:** procesamiento de prompt de 512 tokens (`pp512`) y generación de 128 tokens (`tg128`)

## Resultados

| Métrica | Resultado |
|---|---:|
| Procesamiento del prompt (`pp512`) | 4411,27 ± 116,24 tokens/s |
| Generación (`tg128`) | 117,98 ± 1,17 tokens/s |
| Pico de VRAM observado | 1433 MiB |
| Temperatura máxima observada | 56 °C |
| Muestras del monitor GPU | 35 |

Los valores de velocidad y dispersión proceden de la salida de `llama-bench`.
El pico de VRAM y la temperatura proceden de las muestras de `nvidia-smi`
registradas durante la ejecución.

## Interpretación y límites

La prueba confirma la ejecución con el backend CUDA y la configuración
indicada. La velocidad de procesamiento del prompt no equivale a la velocidad
de generación de tokens.

La monitorización de GPU se muestreó aproximadamente cada 200 ms. Por tanto,
1433 MiB es el máximo observado en las muestras y no garantiza capturar
picos transitorios entre lecturas. Las cifras corresponden a esta ejecución
y no deben generalizarse a otros contextos, longitudes o configuraciones.

## Evidencias reproducibles

- [Salida original de llama-bench](artifacts/lfm3-1.7b-rtx3050-cuda-20261028/llama-bench.md)
- [Muestras de monitorización GPU](artifacts/lfm3-1.7b-rtx3050-cuda-20261028/gpu-monitor.csv)
- [Sumas SHA-256](artifacts/lfm3-1.7b-rtx3050-cuda-20261028/SHA256SUMS.txt)

Las sumas permiten comprobar la integridad de los archivos archivados.
