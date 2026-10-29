# Ling-3.0-Tiny Q4_K_M en Ubuntu — GB-BXi7-5500

**Fecha de ejecución:** 2026-10-29  
**Estado:** evaluación experimental; prueba funcional de código superada, calidad factual aún no validada como fiable.  
**Repositorio:** [LEONES](https://github.com/robertosantosx2/LEONES)

## Equipo y entorno

- Equipo: GB-BXi7-5500.
- Sistema: Ubuntu 26.04.1 LTS, kernel `7.0.0-38-generic`.
- CPU: Intel Core i7-5500U, 2 núcleos / 4 hilos, AVX2.
- RAM instalada: 14 GiB; swap: 4 GiB.
- Motor: `llama.cpp`, versión `0.8.0-dev`, commit `0893ec9`.
- Modelo: `bloomer010/Ling-3.0-tiny-GGUF:Q4_K_M`.
- Inferencia: CPU, 4 hilos; contexto de 1024 tokens.
- El servidor LFM3 que ocupa `127.0.0.1:8080` se mantuvo intacto.

## Ejecución de referencia: generación de código

Configuración utilizada: `--ctx-size 1024 --threads 4 --threads-batch 4 --n-predict 512 --reasoning off --reasoning-format none --reasoning-budget 0 --temp 0.1 --jinja --single-turn --simple-io`.

| Métrica | Resultado observado |
|---|---:|
| Prefill | 41,0 tokens/s |
| Generación | 15,5 tokens/s |
| Tiempo total | 16,72 s |
| Pico RSS del proceso | 8.240.880 KiB (≈ 7,86 GiB) |
| Fallos mayores de página | 0 |
| Swaps registrados por `/usr/bin/time -v` para el proceso | 0 |
| Código de salida | 0 |

Estas cifras corresponden a una sola ejecución, con un prompt de generación de código; no son una media estadística ni una comparación perfectamente controlada con otros modelos.

## Prueba funcional de Python

Se pidió una función `factorial(n)` que rechazase negativos con `ValueError`, devolviese 1 para cero e incluyese tres pruebas. El código generado se extrajo del registro local, se ejecutó con Python 3 y pasó estas aserciones:

- `factorial(0) == 1`
- `factorial(5) == 120`
- `factorial(10) == 3628800`
- `factorial(-1)` lanza `ValueError`

**Resultado: PASS.** El artefacto de código validado está archivado en [factorial.py](./artifacts/ling3-memory-20261029-213059-factorial.py).

## Otras observaciones de la sesión

En pruebas previas de esta misma sesión, la generación observada estuvo aproximadamente entre 15,2 y 17,0 tokens/s, y el prefill entre 26,9 y 41,6 tokens/s, dependiendo del prompt y la configuración. También se observaron límites de calidad:

- Una respuesta sobre si un GGUF de 5 GiB cabe en 14 GiB de RAM fue demasiado categórica y no consideró suficientemente el sistema operativo, la caché, los buffers ni la memoria de contexto.
- Algunas respuestas sobre memoria de modelos MoE fueron imprecisas.
- Una primera salida de código quedó incompleta al limitar la generación; la prueba final con 512 tokens sí produjo el código completo.

Por tanto, el resultado demuestra que el modelo puede ejecutar correctamente una tarea de código sencilla, pero **no demuestra fiabilidad factual general ni superioridad frente a LFM3-1.7B**.

## Registros en el equipo

Los registros completos siguen en el equipo de pruebas y no se han subido como logs brutos en este commit:

- `~/ling3-memory-20261029-213059/test.log`
- `~/ling3-memory-20261029-213059/factorial.py`

El registro contiene la salida de la ejecución y las métricas de `/usr/bin/time -v`. Para una comparación reproducible posterior, repetir cada prompt varias veces bajo las mismas condiciones y comparar exactitud, tokens/s, tiempo, RSS y resultados de pruebas automáticas.
