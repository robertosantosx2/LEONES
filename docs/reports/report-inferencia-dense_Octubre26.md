# Informe de inferencia denso — Octubre de 2026

**Fecha de pruebas:** 22 de octubre de 2026  
**Estado:** benchmark inicial documentado; resultados locales aún no adjuntos a este commit.  
**Equipo:** Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM), CUDA 13.0, driver 580.178.04, compute capability sm_86.

## Resumen ejecutivo

Se midieron dos configuraciones distintas en el mismo equipo:

1. **llama.cpp + Qwen3-30B-A3B-Instruct-2507 IQ3_XXS**, mediante `llama-bench`, variando `--n-gpu-layers` entre 0, 1 y 8 con tres repeticiones por ajuste.
2. **TensorFold 1.1.1 + Qwen3.5-2B-MLX-4bit**, mediante cinco peticiones HTTP secuenciales a la API compatible con OpenAI.

No son modelos equivalentes ni usan el mismo protocolo; sus velocidades brutas no deben interpretarse como una clasificación directa de motores.

## Hardware y entorno

- CPU: Intel Core i7-12650H.
- Memoria del sistema: aproximadamente 14 GiB.
- GPU: NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- Driver NVIDIA: 580.178.04; CUDA reportada: 13.0.
- Compute capability: sm_86.
- Sistema: Ubuntu/Linux.
- En pruebas previas se observó un Xid 31 con llama-server; por prudencia, conviene repetir las pruebas críticas y registrar los errores de kernel/GPU.

## Experimento A — llama.cpp

### Configuración

- Modelo: `Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XXS.gguf`.
- SHA-256 del modelo: `292daa2b66aec59d075532d0bcf05010bf4a3b012a4216c28dc021b73d1e9ab4`.
- Tamaño informado por `llama-bench`: 11.37 GiB.
- Build: `6fa4f6cd3 (11740)`.
- Hilos: 8.
- Prefill: `pp128`; generación: `tg32`.
- Capas GPU: 0, 1 y 8.
- Repeticiones: 3 por configuración; nueve ejecuciones, todas con código de salida 0.
- `--repetitions 1` por invocación de benchmark; se repitió la invocación tres veces por configuración.

### Resultados por repetición

| Capas GPU | Repetición | pp128 (tok/s) | tg32 (tok/s) |
|---:|---:|---:|---:|
| 0 | 1 | 13.69 | 1.45 |
| 0 | 2 | 24.42 | 1.41 |
| 0 | 3 | 29.55 | 1.60 |
| 1 | 1 | 57.28 | 1.44 |
| 1 | 2 | 76.25 | 1.40 |
| 1 | 3 | 89.89 | 2.14 |
| 8 | 1 | 69.08 | 1.88 |
| 8 | 2 | 26.38 | 1.65 |
| 8 | 3 | 9.41 | 1.95 |

### Estadísticas

| Capas GPU | Prueba | Media tok/s | Mediana tok/s | Desv. estándar | Mín. | Máx. |
|---:|---|---:|---:|---:|---:|---:|
| 0 | pp128 | 22.553 | 24.420 | 8.093 | 13.69 | 29.55 |
| 0 | tg32 | 1.487 | 1.450 | 0.100 | 1.41 | 1.60 |
| 1 | pp128 | 74.473 | 76.250 | 16.377 | 57.28 | 89.89 |
| 1 | tg32 | 1.660 | 1.440 | 0.416 | 1.40 | 2.14 |
| 8 | pp128 | 34.957 | 26.380 | 30.746 | 9.41 | 69.08 |
| 8 | tg32 | 1.827 | 1.880 | 0.157 | 1.65 | 1.95 |

### Interpretación

- En esta muestra, `ngl=1` obtuvo la mayor mediana de prefill.
- `ngl=8` mostró una dispersión muy elevada en prefill (9.41–69.08 tok/s); no debe atribuirse una causa sin repetir bajo condiciones controladas.
- La generación `tg32` se mantuvo aproximadamente entre 1.40 y 2.14 tok/s.
- La instantánea de `nvidia-smi` se recogió después de la ejecución, no durante ella. No representa utilización máxima ni permite concluir que no hubiera offload.
- Las nueve ejecuciones finalizaron con código 0, pero esto no sustituye la comprobación de estabilidad, errores del driver y memoria durante la prueba.

## Experimento B — TensorFold

### Configuración

- Motor: TensorFold 1.1.1, backend CUDA.
- Modelo: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- Nombre servido: `qwen35-2b-4bit`.
- Contexto del servidor: 2048 tokens; paralelismo 1.
- Thinking desactivado; temperatura 0; límite de salida 128 tokens.
- Cinco peticiones HTTP secuenciales con el mismo prompt.
- Entrada reportada por petición: 66 tokens; salida: 128 tokens.
- Cinco respuestas HTTP 200.

### Resultados por repetición

| Run | HTTP | Velocidad reportada (tok/s) | Tiempo cliente (s) | TTFT (s) | Prefill (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 200 | 107.068 | 1.249233 | 0.051058 | 0.048931 |
| 2 | 200 | 103.407 | 1.317400 | 0.084446 | 0.080437 |
| 3 | 200 | 106.496 | 1.280382 | 0.084646 | 0.080489 |
| 4 | 200 | 103.677 | 1.312622 | 0.084926 | 0.080445 |
| 5 | 200 | 106.455 | 1.280760 | 0.084702 | 0.080406 |

### Estadísticas

| Métrica | Media | Mediana | Mínimo | Máximo |
|---|---:|---:|---:|---:|
| Velocidad reportada (tok/s) | 105.421 | 106.455 | 103.407 | 107.068 |
| Tiempo HTTP cliente (s) | 1.288079 | 1.280760 | 1.249233 | 1.317400 |
| TTFT reportado (s) | 0.077956 | 0.084646 | 0.051058 | 0.084926 |
| Prefill reportado (s) | 0.074142 | 0.080437 | 0.048931 | 0.080489 |

Las cinco salidas tienen el mismo SHA-256: `942ca6d9de584e12bd4f207d8cafddcffb594924f5d781501b267b7a1ca9ddad`.

### Interpretación y limitaciones

- Todas las peticiones generaron exactamente 128 tokens, alcanzando el máximo configurado; las respuestas podrían estar truncadas por ese límite.
- La latencia del cliente mide la petición HTTP completa; no es equivalente al tiempo interno de generación.
- La tasa de aceptación especulativa reportada fue baja (1 token aceptado de 56 propuestos en cada petición, aceptación 0.01786). Debe investigarse en pruebas específicas y no extrapolarse a otras cargas.
- El hash idéntico indica salida textual idéntica para este prompt y configuración, no una validación general de calidad.
- La captura de GPU al final no mide el pico durante cada petición.

## Comparabilidad

Estos experimentos responden a preguntas distintas:

- `llama-bench` separa prefill (`pp128`) y generación (`tg32`) para un modelo MoE de 30B en formato IQ3_XXS.
- TensorFold mide solicitudes API de un modelo de 2B en formato MLX 4-bit, con 66 tokens de entrada y 128 de salida.

Por tanto, **no es válido concluir que TensorFold sea más rápido que llama.cpp comparando directamente sus tok/s**. Difieren el modelo, la cuantización, la longitud de generación, el motor, la instrumentación y el protocolo.

## Archivos de resultados locales

Los siguientes artefactos quedaron guardados en el equipo local durante la sesión; no están incluidos en este documento de GitHub salvo que se añadan explícitamente:

- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/benchmark-report.md`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/summary.tsv`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/measurements.csv`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/layer-sweep-20261022-115737/statistics.csv`
- Logs `ngl0-rep1.log` a `ngl8-rep3.log` dentro del directorio del barrido.
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705/benchmark-report.md`
- `~/benchmarks/qwen3-30b-a3b-iq3-xxs/tensorfold-qwen35-2b-4bit-20261022-121705/measurements.csv`
- JSON originales `responses/run-01.json` a `run-05.json`, junto con `environment.txt`, `config.txt` y `after.txt`.

## Siguientes pruebas recomendadas

1. Repetir el barrido llama.cpp con más repeticiones y condiciones de sistema estables.
2. Muestrear GPU/VRAM y RAM durante cada ejecución, no solo después.
3. Repetir TensorFold con varios límites de salida y prompts controlados, incluyendo salidas que no terminen exactamente en el límite.
4. Registrar errores de kernel/driver, swap y presión de memoria.
5. Evaluar calidad de respuesta separadamente de rendimiento.
6. Añadir al repositorio los logs/CSV/JSON como artefactos o paquete comprimido si se necesita auditoría completa.
