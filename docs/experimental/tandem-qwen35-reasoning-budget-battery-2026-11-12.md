# Resultados resumidos · Tandem.cpp Qwen3.5-35B-A3B IQ2_XXS · 2026-11-12

## Identidad de la ejecución

- Modelo: Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf, tamaño local comunicado 9.94 GiB.
- Tandem.cpp: commit d684d4de171d8c6413e34c95fb5703492dcd2561.
- llama.cpp submodule: f5222f25c18da062ab2b8a2dbbfbf4feae398566.
- Build: 0.8.0-dev build 11962, fingerprint b11962-f5222f25c.
- Endpoint: 127.0.0.1:18086.
- Parámetros: contexto 2048, batch 128, ubatch 64, threads 8/8, ngl 99, CPU-MoE, caché expertos 512 MiB, un slot.
- Hardware: MSI Thin 15 B12UC; i7-12650H; RTX 3050 Laptop 4 GiB (sm_86); RAM 14 GiB; swap 32 GiB; driver 580.178.04; CUDA runtime 13.0; nvcc 13.4.92; Ubuntu kernel 7.0.0-43-generic.

## Resumen de mediciones

| Caso | Budget | max_tokens | completion | tok/s | finish |
|---|---:|---:|---:|---:|---|
| 17 × 23 | 64 | 256 | 70 | 35.62 | stop |
| 17 × 23 | 128 | 384 | 134 | no registrado aquí | stop |
| 17 × 23 | 256 | 512 | 262–263 | 34.58 / 33.11 | stop |
| two_sum | 128 | 512 | 512 | 33.07 | length |
| two_sum | 128 | 768 | 768 | 32.51 | length |
| two_sum | 256 | 1024 | 1024 | 33.27 | length |
| two_sum | 128 | 1536 | 1165 | 32.58 | stop |
| two_sum | 256 | 1536 | 1201 | 32.32 | stop |
| binary_search | 128 | 1536 | 1435 | 34.79 | stop |
| binary_search | 256 | 1536 | 1536 | 33.20 | length |


## Diagnóstico thinking

Con thinking activado y sin presupuesto explícito, se observaron salidas de razonamiento que consumieron max_tokens enteros sin producir contenido final (finish_reason length). La prueba sin thinking sí produjo una respuesta final. El parser Qwen3-Coder separa el contenido anterior a </think> como reasoning_content; al no aparecer el cierre antes de acabar la generación, content queda vacío. El control reasoning_budget_tokens fuerza el marcador de cierre al agotar el presupuesto.


## Comportamiento de los recursos del MSI

### Qué se midió y qué no

La batería registra métricas de generación por petición (tokens de entrada/salida, duración, velocidad y motivo de finalización). En cambio, el recolector de evidencias ejecutó capturas del sistema y del proceso en un momento concreto; no tomó una serie temporal de CPU/RAM/VRAM/SSD asociada a cada petición. Por tanto, la fotografía siguiente describe el estado del servidor cargado durante la campaña, no picos exactos de cada fila. No se deben interpretar los mismos valores como mediciones independientes de cada prompt.

### Fotografía del equipo con el modelo cargado

| Recurso | Captura disponible | Lectura técnica |
|---|---|---|
| RAM | 14 GiB totales; 3,1 GiB usados; 1,4 GiB libres; 11 GiB en buff/cache; 11 GiB disponibles | No aparece presión de memoria física en esa captura: Linux podía recuperar buena parte de la caché. «Libre» por sí solo infravalora la memoria disponible. |
| Swap | 32 GiB configurados; aproximadamente 1,2 GiB ocupados | Había páginas en swap, pero la ocupación no demuestra actividad de intercambio durante las generaciones ni thrashing. No se guardaron contadores temporales de swap-in/swap-out por petición. |
| VRAM | 1.953 MiB de 4.096 MiB ocupados; proceso del servidor alrededor de 1.930 MiB | El servidor mantenía una huella GPU relativamente contenida, dejando aproximadamente 2,1 GiB sin ocupar en esa captura. Es coherente con la estrategia CPU-MoE; no demuestra por sí sola el hit rate ni la ubicación efectiva de cada experto. |
| GPU | RTX 3050 Laptop, 4 GiB, sm_86; temperatura observada 44 °C | No se conservó una serie temporal de utilización, potencia, reloj o temperatura por petición. |
| CPU | Intel Core i7-12650H; servidor configurado con 8 threads y 8 threads de batch; `--cpu-moe` | La ruta CPU-MoE sitúa el trabajo de expertos en CPU y memoria del host, mientras que otras operaciones usan GPU. No hay porcentaje de uso, frecuencia ni carga por ejecución en la evidencia recopilada. |
| SSD / almacenamiento | El GGUF local ocupa aproximadamente 9,94 GiB y el servidor lo carga desde esa ruta | No hay mediciones de lectura, escritura, latencia, IOPS ni espacio libre tomadas durante la batería. La caché de páginas de Linux puede intervenir en lecturas posteriores, pero no se midió su efecto por prompt. |
| Proceso servidor | PID 12228; puerto 18086; contexto 2048; un slot; caché de expertos configurada en 512 MiB | La caché de expertos de 512 MiB es un parámetro de configuración, no una medición de memoria efectivamente residente ni de tasa de aciertos. El servidor permaneció cargado entre peticiones; no se reinició entre cada caso. |

**Interpretación global.** La señal más clara es que el modelo de 35B se ejecutó con una huella GPU observada de alrededor de 1,9 GiB, apoyándose en CPU-MoE y memoria del host en una RTX 3050 de 4 GiB. La RAM disponible reportada (11 GiB) no indicaba presión severa en el instante de captura. La presencia de 1,2 GiB ocupados en swap merece registrarse, pero sin contadores de actividad no permite afirmar que las generaciones estuvieran paginando activamente. Tampoco hay datos suficientes para afirmar que el SSD fuera cuello de botella o para cuantificar el uso de CPU.

### Recursos por ejecución: alcance de la evidencia

El servidor se mantuvo residente en el puerto 18086 y atendió las peticiones de forma secuencial con un slot. La tabla vincula cada ejecución con su resultado de generación y deja explícito que no existe telemetría de recursos por petición. Los tiempos aproximados se calculan como completion / tok/s cuando ambos datos están disponibles; no son cronometraje independiente.

| Caso | Budget | completion | Velocidad | Tiempo aprox. de generación | RAM / VRAM / CPU / swap / SSD por petición |
|---|---:|---:|---:|---:|---|
| 17 × 23 | 64 | 70 | 35,62 tok/s | 1,97 s | No capturados individualmente; aplica solo la fotografía compartida anterior como contexto del servidor. |
| 17 × 23 | 128 | 134 | No registrado | No calculable | No capturados individualmente. |
| 17 × 23 | 256, repetición A | 262 | 34,58 tok/s | 7,58 s | No capturados individualmente. |
| 17 × 23 | 256, repetición B | 263 | 33,11 tok/s | 7,94 s | No capturados individualmente. |
| two_sum | 128 | 512 | 33,07 tok/s | 15,48 s | No capturados individualmente. |
| two_sum | 128 | 768 | 32,51 tok/s | 23,62 s | No capturados individualmente. |
| two_sum | 256 | 1.024 | 33,27 tok/s | 30,78 s | No capturados individualmente. |
| two_sum | 128 | 1.165 | 32,58 tok/s | 35,76 s | No capturados individualmente. |
| two_sum | 256 | 1.201 | 32,32 tok/s | 37,16 s | No capturados individualmente. |
| binary_search | 128 | 1.435 | 34,79 tok/s | 41,25 s | No capturados individualmente. |
| binary_search | 256 | 1.536 | 33,20 tok/s | 46,27 s | No capturados individualmente. |

Los tiempos son estimaciones aritméticas a partir de la velocidad media informada por el servidor; pueden diferir del tiempo total de pared por prefill, preparación, colas y latencias de la API. La tabla no implica que RAM, VRAM o CPU permanecieran constantes durante cada generación: simplemente no se muestrearon con suficiente resolución para saberlo.

### Qué instrumentar en una siguiente repetición

Para poder comparar el comportamiento físico de cada ejecución, conviene añadir muestreo con marcas de tiempo y correlación con el ID de petición:
- GPU: `nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.free,temperature.gpu,power.draw,clocks.gr --format=csv -l 1`.
- CPU y memoria: muestreo de `/proc/stat`, `/proc/meminfo` y `/proc/<PID>/status` o `pidstat -rud -p <PID> 1`.
- Swap: deltas de `pswpin` y `pswpout` en `/proc/vmstat`, no solo el tamaño ocupado.
- SSD: deltas de `/proc/diskstats` para el dispositivo que contiene el modelo, junto con espacio disponible antes/después.
- Registrar hora de inicio/fin, request ID, budget, completion y métricas de la API en el mismo fichero de eventos.

Así se podrá calcular consumo máximo y medio por petición y detectar si las generaciones largas elevan CPU, RAM, VRAM, swap o I/O. En esta batería, esas relaciones quedan como hipótesis de trabajo y no como resultados medidos.


## Instrumentación para próximas ejecuciones

Se han añadido scripts para registrar recursos durante **cada petición**, con una ventana de muestreo independiente y un identificador local de caso:

- [Runner de batería instrumentado](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_battery.py)
- [Monitor Linux/NVIDIA](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py)
- [Guía de uso y límites de medición](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/RESOURCE_MONITORING.md)

El runner genera `resource_metrics` dentro de cada JSON de respuesta y de `summary.jsonl`, además de muestras brutas en `resources/resource_samples.jsonl`. Incluye RAM del host y RSS del servidor, swap, CPU del sistema y del proceso, utilización y VRAM de NVIDIA, temperatura/potencia/reloj GPU y deltas de E/S por dispositivo de bloque. También identifica el montaje que contiene el GGUF.

**Importante:** esta instrumentación queda preparada para las siguientes campañas; no modifica los resultados históricos ni reconstruye telemetría que no se capturó en noviembre. Antes de una batería completa, la guía recomienda validar con `--limit 1`. Los contadores de disco y swap son del sistema y pueden incluir actividad ajena al servidor; se documentan esos límites.

## Evidencias y ficheros reproducibles

El archivo de evidencias generado el 12 de noviembre de 2026 se ha incorporado a esta rama de Git y su checksum SHA-256 se verificó localmente antes de publicarlo.

- [Archivo comprimido de evidencias (TAR.GZ)](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/evidence/tandem-qwen35-evidence-20261112-235030.tar.gz)
- [Checksum SHA-256](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/evidence/tandem-qwen35-evidence-20261112-235030.tar.gz.sha256)
- [Scripts de reproducción](../../artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/)
- [Metodología de la batería](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md)

El archivo contiene los registros y capturas recopilados por el script de evidencias. No incluye los pesos del modelo GGUF.
