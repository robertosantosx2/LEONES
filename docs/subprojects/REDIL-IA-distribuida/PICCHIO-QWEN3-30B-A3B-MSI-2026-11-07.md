# Picchio + Qwen3-30B-A3B en MSI Thin 15 — primera ejecución real

**Fecha:** 2026-11-07  
**Estado:** **LOCAL-MEASURED-USER / primera inferencia completada**  
**Equipo:** MSI Thin 15 B12UC · Intel Core i7-12650H (16 CPU lógicas) · 14 GiB RAM · NVIDIA RTX 3050 Laptop 4 GiB · NVMe ext4 · Ubuntu  
**Repositorio del motor:** https://github.com/benmaster82/picchio  
**Runtime:** Picchio v0.8.0, compilación x86-64 AVX2/FMA  
**Modelo:** Qwen/Qwen3-30B-A3B-Instruct-2507, conversión Picchio INT4 local  
**Artefacto local:** `~/picchio-data/qwen3-30b-a3b-int4` (16 shards, aproximadamente 20.6 GB)

> Este documento conserva una ejecución comunicada por el usuario en su equipo real. No es un benchmark independiente ni permite extrapolar el resultado a otros sistemas.

## 1. Preparación y validación

- Autotest de Picchio: **PASSED**. Incluyó forward sintético, RMSNorm, softmax, matmul F32, SiLU, reducción MoE asíncrona canónica, RoPE, cuantización/matmul INT4 e INT3 y prueba de identidad del pipeline.
- Tokenizer cargado desde el directorio local: `Qwen2Tokenizer`, vocabulario informado por Transformers de 151.669 tokens y chat template presente.
- La configuración del modelo detectada por Picchio: Qwen3-MoE, D=2048, 48 capas, 32 cabezas, 4 KV heads, head_dim=128, 128 expertos y top-8; moe_inter=1536, vocabulario del modelo=151.936.
- El conversor streaming terminó correctamente: 16/16 shards, aproximadamente 20.6 GB de salida, sin archivos `.pending` residuales y con `pending=0` al completar el último shard.
- El runtime reconoció **25.013 tensores en 16 archivos**.

## 2. Configuración de la primera inferencia

Comando ejecutado:

```bash
FLAT=0 .venv/bin/python -u chat_qwen.py \
  "Responde en español: explica brevemente qué es un modelo Mixture of Experts y cómo selecciona los expertos que utiliza." \
  --model /home/ssantos/picchio-data/qwen3-30b-a3b-int4 \
  --ctx 512 --pin-gb 2 --threads 4 --io-threads 4 \
  --max-tokens 128 --no-reasoning
```

Perfil efectivo: CPU streaming, 4 hilos CPU, 4 hilos de E/S, caché experta de 2 GiB, 16 slots por capa × 48 capas, contexto de sesión 512. No se habilitaron GPU experts, GPU router, async MoE ni direct mode. La RTX no participó en la inferencia.

## 3. Resultado medido

| Métrica | Resultado |
|---|---:|
| Tiempo de carga | 2.8 s |
| Pesos densos residentes | 4.30 GB |
| RSS del proceso al finalizar | 6.32 GB |
| Caché de expertos configurada | 2.0 GB |
| Tokens generados | 128 |
| Tiempo de generación informado | 79.1 s |
| **Velocidad total informada** | **1.6 tok/s** |
| Contexto informado | 164 / 512 |
| Cache hit | 31,228 / 52,300 = 59.7% |
| Lecturas de disco | 21,072 |
| Tiempo acumulado de lecturas | 42.62 s |
| Tiempo atención | 18.52 s |
| Tiempo MoE | 55.81 s |
| Tiempo head | 2.46 s |

La respuesta fue coherente y en español, pero quedó truncada al alcanzar el límite de 128 tokens. Por tanto, esta prueba acredita carga e inferencia end-to-end, no una evaluación de calidad completa.

## 4. Estado del equipo tras la ejecución

Medición posterior:

- RAM: 14 GiB total, 9.4 GiB disponibles.
- NVMe: `/dev/nvme0n1p2`, ext4; 361 GB disponibles en el sistema de archivos.
- GPU: 16 MiB ocupados de 4096 MiB; Xorg era el proceso listado.
- CPU: Intel Core i7-12650H, 16 CPU lógicas.
- Carga del sistema: load average 1.13, 1.47, 0.88.
- Archivo `.picchio_usage` creado en el directorio del modelo, tamaño aproximado 25 KB.

La lectura posterior no muestra saturación persistente de RAM ni uso de VRAM por la inferencia.

## 5. Revisión del mecanismo hot-store

Se inspeccionó `picchio.c` en Picchio v0.8.0.

Hallazgos observados en el código consultado:

1. `hotstore_save()` escribe el magic `PICC`, versión 1, dimensiones (capas y expertos) y contadores `eusage` por capa en `.picchio_usage`.
2. `hotstore_load()` valida magic y dimensiones y restaura esos contadores.
3. Los contadores `eusage` se incrementan durante el routing y se guardan/recuperan entre sesiones.
4. `eheat` se incrementa en rutas de ejecución, pero en las referencias inspeccionadas no se encontró lectura que afecte a la política de caché.
5. La búsqueda de escrituras sobre `npin` y `pin` no devolvió coincidencias. La inicialización reserva las estructuras `pin`, `npin`, `eusage` y `eheat`, pero no mostró una rutina de promoción o precarga.
6. La inicialización de caché observada dimensiona `ecap` y crea el pool LRU; posteriormente llama a `hotstore_load()`.

**Conclusión acotada:** la persistencia y recuperación de estadísticas de routing están implementadas. En el código inspeccionado no se ha encontrado evidencia de que esas estadísticas seleccionen y precarguen expertos calientes ni de que se promuevan a la caché pinned. El comentario del código que anuncia esa precarga no queda respaldado por los fragmentos revisados. Conviene verificar el archivo completo y las rutas de carga antes de abrir una incidencia definitiva.

No se debe afirmar que el hot-store haya acelerado una segunda sesión: aún no se ha realizado esa comparación.

## 6. Próximos experimentos

Mantener el mismo modelo, prompt, contexto y límites para aislar variables:

### A. Repetición con caché de 2 GiB
- Repetir el prompt con los mismos parámetros.
- Registrar velocidad, cache hit, lecturas, tiempos MoE/atención y RSS.
- Determinar si hay beneficio de caché del sistema operativo o de estado persistente. No atribuirlo al hot-store sin evidencia.

### B. Caché de expertos de 3 GiB
- Solo después de conservar el baseline repetido.
- Cambiar exclusivamente `--pin-gb 2` por `--pin-gb 3`.
- Vigilar RAM disponible y RSS; no iniciar procesos concurrentes.
- Comparar tokens/s, cache hit, lecturas y tiempo MoE.

### C. Perfil de CPU
- Una vez fijada la caché, comparar 4 frente a 8 hilos CPU, sin variar simultáneamente otros parámetros.
- Medir si aumenta el throughput o si la E/S y el ancho de banda de memoria limitan la ganancia.

### D. Investigación del hot-store
- Revisar todas las rutas de inserción/evicción de expertos y las funciones de inicialización de caché.
- Si se confirma que no hay consumidor de `eusage/eheat`, documentar el comportamiento como funcionalidad parcial y proponer implementación o corrección de comentarios/documentación upstream.

## 7. Interpretación para REDIL

Esta ejecución demuestra que un MoE de 30B parámetros totales y 3B activos puede cargarse y generar texto en un portátil con 14 GiB de RAM mediante conversión INT4 y streaming de expertos desde NVMe, con un resultado medido de 1.6 tok/s bajo esta configuración concreta.

No demuestra que sea adecuado para un servicio interactivo multiusuario, ni que la RTX 3050 acelere Picchio, ni que una caché mayor mejore el rendimiento. Para REDIL es una prueba de viabilidad experimental de inferencia local CPU con MoE, con latencia modesta y margen de optimización pendiente.

**Clasificación:** LOCAL-MEASURED-USER para la ejecución descrita; las mejoras futuras son PENDING. Mantener separados los resultados medidos, las hipótesis y las estimaciones.

## 8. Afinado de caché y paralelismo — 7 de noviembre de 2026

Se mantuvieron constantes el modelo, prompt, contexto 512, 128 tokens, modo sin reasoning y caché experta de 4 GiB. Se variaron los hilos de CPU y, después, los hilos de E/S. Todas las cifras siguientes proceden de logs comunicados por el usuario en el MSI.

### 8.1 Comparación de hilos CPU (E/S fija en 4)

| Hilos CPU | Tiempo | Velocidad informada | Cache hit | Lecturas disco | t_attn | t_moe | RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 81,4 s | 1,6 tok/s | 79,1 % | 10.918 | 18,35 s | 58,54 s | 8,83 GB |
| 4 — prueba 1 | 57,0 s | 2,2 tok/s | 79,2 % | 10.873 | 15,89 s | 37,18 s | 9,35 GB |
| 4 — prueba 2 | 65,2 s | 2,0 tok/s | 78,7 % | 11.116 | 15,78 s | 45,47 s | 9,38 GB |
| 4 — prueba 3 | 70,3 s | 1,8 tok/s | 79,2 % | 10.856 | 15,83 s | 50,66 s | 9,37 GB |
| 8 | 85,7 s | 1,5 tok/s | 79,1 % | 10.921 | 22,61 s | 59,26 s | 9,36 GB |

La configuración de 4 hilos CPU es la mejor de las probadas. Las tres ejecuciones de 4 hilos dieron una media de 64,2 s y mediana de 65,2 s; existe variabilidad apreciable (57,0–70,3 s). Ocho hilos CPU fueron claramente más lentos. Dos hilos redujeron el RSS, pero también el rendimiento.

### 8.2 Comparación de hilos de E/S (CPU fija en 4)

| Hilos E/S | Tiempo | Velocidad informada | Cache hit | Lecturas disco | Tiempo lecturas | t_attn | t_moe | RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 73,5 s | 1,7 tok/s | 78,6 % | 11.217 | 36,68 s | 16,21 s | 53,57 s | 8,64 GB |
| 4 — prueba 1 | 57,0 s | 2,2 tok/s | 79,2 % | 10.873 | 24,55 s | 15,89 s | 37,18 s | 9,35 GB |
| 4 — prueba 2 | 65,2 s | 2,0 tok/s | 78,7 % | 11.116 | 32,59 s | 15,78 s | 45,47 s | 9,38 GB |
| 4 — prueba 3 | 70,3 s | 1,8 tok/s | 79,2 % | 10.856 | 37,42 s | 15,83 s | 50,66 s | 9,37 GB |
| 8 — prueba 1 | 66,4 s | 1,9 tok/s | 79,2 % | 10.902 | 32,77 s | 15,79 s | 46,73 s | 9,34 GB |
| 8 — prueba 2 | 72,6 s | 1,8 tok/s | 79,2 % | 10.867 | 35,38 s | 17,87 s | 50,25 s | 9,17 GB |

Con 8 hilos de E/S no se confirma una mejora: la media de las dos pruebas es 69,5 s, frente a 64,2 s en las tres pruebas con 4 hilos. Dos hilos de E/S tampoco mejoraron el resultado. Las tasas de acierto de caché permanecen alrededor del 79 % en todas estas pruebas; no hay evidencia de que aumentar los hilos cambie sustancialmente la reutilización de expertos.

### 8.3 Configuración recomendada y límites

**Configuración candidata de referencia para este equipo y este modelo:**

- `--threads 4`
- `--io-threads 4`
- `--pin-gb 4` (33 slots por capa × 48 capas; aproximadamente 4,2 GB de caché experta según el log)
- `--ctx 512`
- `FLAT=0`, `--max-tokens 128`, `--no-reasoning`

La velocidad observada en las tres ejecuciones de referencia de 4+4 fue 1,8–2,2 tok/s (media aproximada 2,0 tok/s). No presentar 2,2 tok/s como rendimiento garantizado. La prueba con caché de 5 GB fue más lenta que la de 4 GB pese a lograr más aciertos; no se recomienda ampliarla basándose solo en el hit ratio.

**Interpretación prudente:** el mejor resultado individual de 8 hilos E/S (66,4 s) no se reprodujo (72,6 s). El conjunto actual favorece 4+4, pero el número de repeticiones sigue siendo pequeño y hay variación entre ejecuciones. No se ha aislado todavía la influencia de temperatura, frecuencia, caché del sistema operativo ni estado del almacenamiento. Los tiempos internos de lectura, atención y MoE son métricas del runtime y no deben sumarse como si fueran intervalos necesariamente disjuntos.

La inferencia continúa siendo CPU streaming. La RTX 3050 no participó. No se demuestra aceleración GPU, escalabilidad multiusuario ni mejora causal por el hot-store; el contador de routings cargado solo confirma restauración de estadísticas.

**Estado:** LOCAL-MEASURED-USER. La configuración 4 CPU + 4 E/S + 4 GiB queda como baseline experimental provisional para próximas comparaciones.
