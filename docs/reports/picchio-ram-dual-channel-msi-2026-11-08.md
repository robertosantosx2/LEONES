# Picchio en MSI Thin 15: memoria DDR4, dual channel y escalado CPU

**Fecha de actualización:** 2026-11-08  
**Estado:** investigación en curso; resultados STREAM recibidos, repetición controlada de Picchio pendiente.  
**Repositorio:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Proyecto evaluado:** [Picchio](https://github.com/robertosantosx2/picchio)

## 1. Objetivo

Investigar si el rendimiento de inferencia CPU de Picchio sobre Qwen3-30B-A3B INT4 está limitado por el ancho de banda de memoria y cómo escala al aumentar los hilos. La hipótesis inicial es que el ancho de banda de RAM puede importar más que añadir núcleos, especialmente en una arquitectura Mixture of Experts (MoE), donde se accede a distintos expertos.

No se presupone que dual channel duplique los tokens/s: debe demostrarse con medidas comparables.

## 2. Plataforma de pruebas

| Componente | Configuración observada |
|---|---|
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H, 12.ª generación |
| CPU lógicas | 16 (CPU 0–15) |
| NUMA | 1 nodo |
| RAM instalada | 16 GB, 2 × 8 GB |
| Tipo/velocidad | DDR4-3200, configurados ambos módulos a 3200 MT/s |
| Localizadores SMBIOS | Controller0-ChannelA-DIMM0 y Controller1-ChannelA-DIMM0 |
| Sistema | Ubuntu |
| Memoria visible | 14 GiB |
| GPU | NVIDIA RTX 3050 Laptop, 4 GiB VRAM |
| Modelo | Qwen3-30B-A3B INT4, safetensors |
| Directorio del modelo | ~/picchio-data/qwen3-30b-a3b-int4 |
| Motor | Picchio v0.8.0, modo streaming |

La salida de `dmidecode -t 17` identifica dos módulos de 8 GB a 3200 MT/s en controladores/canales distintos. Esta topología es consistente con dual channel y hace muy probable que esté habilitado. No obstante, SMBIOS no demuestra por sí solo el modo efectivo del controlador de memoria; se debe confirmar con firmware/herramienta de plataforma si se necesita certeza absoluta.

Memoria disponible durante la inspección: 9,7 GiB; swap total 31 GiB, con 7,7 GiB usados en ese momento.

## 3. Resultados Picchio CPU-only anteriores

Modelo Qwen3-30B-A3B INT4, contexto 512, 128 tokens, mismo prompt en español, sin reasoning, presupuesto de caché de expertos CPU de 4 GB, I/O threads 4. Rutas GPU desactivadas mediante `GPU=0 GPU_EXPERTS=0 GPU_ROUTER=0 GPU_PREFETCH=0 GPU_DENSE=0 GPU_LMHEAD=0`.

| Métrica | CPU 4 hilos | CPU 8 hilos |
|---|---:|---:|
| Tokens generados | 128 | 128 |
| Tiempo total | 76,0 s | 81,1 s |
| Velocidad calculada | 1,684 tok/s | 1,578 tok/s |
| Cache hit expertos CPU | 41.293 / 52.300 (79,0%) | 41.563 / 52.300 (79,5%) |
| Lecturas de disco | 11.007 | 10.737 |
| Tiempo acumulado de lecturas | 40,07 s | 33,92 s |
| Atención | 16,63 s | 22,05 s |
| MoE | 55,50 s | 55,05 s |
| LM head | 1,52 s | 1,93 s |
| RSS | 9,22 GB | 9,24 GB |
| Dense residente | 4,30 GB | 4,30 GB |
| GPU | Desactivada; 16 MiB de Xorg, 0% | Desactivada; 16 MiB de Xorg, 0% |

En esta pareja de ejecuciones, 8 hilos tardaron un 6,7% más que 4 hilos. El tiempo MoE fue prácticamente igual; la atención empeoró en la ejecución de 8 hilos, mientras el tiempo acumulado de lectura de disco mejoró.

**Interpretación provisional:** añadir hilos no mejoró el rendimiento global de esta prueba. Esto no demuestra saturación del ancho de banda de RAM. Las ejecuciones todavía no estaban controladas de forma estricta respecto al estado persistente de uso de expertos, semilla y caché de páginas del sistema.

### 3.1 Ejecuciones previas con GPU de expertos activada (no comparables directamente)

Se registraron también ejecuciones con GPU de expertos activada, 128 tokens y el mismo modelo/prompt:

| Métrica | GPU expertos + 4 hilos | GPU expertos + 8 hilos |
|---|---:|---:|
| Tiempo | 92,3 s | 100,5 s |
| Velocidad aproximada | 1,4 tok/s | 1,3 tok/s |
| Cache hit CPU | 77,9% | 77,6% |
| Tiempo atención | 23,74 s | 23,32 s |
| Tiempo MoE | 63,13 s | 72,62 s |
| Tiempo LM head | 2,51 s | 1,95 s |
| RSS | 9,44 GB | 9,18 GB |
| Caché de expertos GPU | 3,24 GB | 3,24 GB |
| Hit rate caché GPU | 69,0% | 69,5% |

No se debe concluir que GPU offload es más lento que CPU: el estado persistente de rutas de expertos cambió entre ejecuciones y no se fijaron todas las condiciones experimentales.

## 4. STREAM: medición sintética de ancho de banda

Se compiló una prueba C con GCC, `-O3 -march=native -fopenmp`, usando tres vectores de 32 × 1024 × 1024 elementos `double` (256 MiB cada uno; 768 MiB en total) y diez repeticiones por operación. Se ejecutó con 1, 2, 4, 8, 12 y 16 hilos, `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=spread`, `OMP_PLACES=cores`.

Los valores registrados son el mejor ancho de banda calculado por operación, no la media:

| Hilos | Copy (GB/s) | Scale (GB/s) | Add (GB/s) | Triad (GB/s) |
|---:|---:|---:|---:|---:|
| 1 | 20,79 | 20,42 | 24,96 | 24,77 |
| 2 | 24,13 | 24,37 | 28,45 | 28,66 |
| 4 | 29,55 | 29,22 | 31,96 | 32,24 |
| 8 | 28,81 | 28,51 | 30,83 | 31,00 |
| 12 | 30,61 | 30,43 | 32,75 | 32,92 |
| 16 | **33,00** | **32,35** | **34,47** | **34,60** |

La operación Triad subió de 24,77 GB/s con un hilo a 34,60 GB/s con 16 hilos. Con cuatro hilos ya alcanzó 32,24 GB/s; pasar a ocho redujo el resultado a 31,00 GB/s. El máximo medido fue con 16 hilos.

Para DDR4-3200 de dos canales de 64 bits, el techo teórico agregado habitual es 51,2 GB/s (no una promesa de rendimiento sostenido). Los 34,6 GB/s medidos en Triad equivalen aproximadamente al 67,6% de ese techo teórico. Esta comparación es orientativa: STREAM local no sustituye una medición validada de controlador y canales.

### 4.1 Limitaciones de la prueba STREAM

- Se registró el máximo de diez repeticiones, lo que puede sobreestimar el rendimiento típico.
- La frecuencia de CPU, temperatura, planificación, afinidad y otros procesos pueden afectar los resultados.
- Los resultados sintéticos no se trasladan linealmente a la inferencia MoE.
- La salida SMBIOS no certifica por sí sola el modo dual channel efectivo.
- No se ha medido la misma máquina en single channel; por tanto, todavía no hay comparación experimental dual vs single channel.

## 5. Conclusiones que sí están respaldadas

1. Hay dos módulos DDR4-3200 de 8 GB instalados en controladores/canales distintos; la configuración es consistente con dual channel.
2. STREAM registró hasta 34,60 GB/s en Triad con 16 hilos y 32,24 GB/s con cuatro hilos.
3. El resultado STREAM de ocho hilos fue inferior al de cuatro hilos en esta ejecución.
4. Picchio CPU-only obtuvo 1,684 tok/s con cuatro hilos y 1,578 tok/s con ocho hilos en las ejecuciones disponibles.
5. No se ha demostrado que la RAM sea el cuello de botella de Picchio ni que dual channel duplique tokens/s.
6. La selección de expertos, caché persistente, lecturas, atención, núcleos híbridos y planificación pueden explicar parte de las diferencias.

## 6. Siguiente experimento: Picchio controlado

Se ha preparado una repetición con:
- `GPU=0` y todas las rutas GPU desactivadas.
- `FLAT=0`, `IO_THREADS=4`, contexto 512, `PIN_GB=4`.
- 128 tokens y el mismo prompt.
- `SEED=12345`.
- Restauración del mismo `.picchio_usage` de referencia antes de cada ejecución.
- Orden alternado: 4, 8, 8, 4 hilos.
- Registro de cada salida en `results/dual-channel/`.

El comando se ha entregado al operador local, pero **todavía no se han recibido los cuatro logs**. No considerar el experimento completado hasta archivarlos y revisar que cada ejecución partió de la misma referencia.

Tras esa pareja controlada, ampliar a 12 y 16 hilos si procede, y probar afinidad separando núcleos P/E del i7-12650H. También conviene medir por separado latencia/throughput de lectura de expertos y presión de memoria.

## 7. Propuestas técnicas para Picchio

1. **Afinidad consciente de arquitectura híbrida:** identificar núcleos P/E y comparar `OMP_PROC_BIND`, `OMP_PLACES` y `taskset` con configuraciones reproducibles.
2. **Escalado de hilos medido por fase:** separar atención, MoE, I/O y LM head; no asumir que más hilos mejoran todas las fases.
3. **Prefetch de expertos:** evaluar anticipación de lecturas y solapamiento I/O/cómputo, midiendo aciertos, misses y esperas.
4. **Caché de expertos reproducible:** permitir exportar/restaurar estado de uso y registrar la semilla para comparar ejecuciones.
5. **Instrumentación de memoria:** registrar RSS, memoria disponible, swap, fallos de página, lecturas y, cuando sea posible, contadores de memoria del hardware.
6. **Benchmark reproducible:** repetir cada configuración varias veces, informar mediana y dispersión, controlar temperatura/frecuencia y conservar logs completos.
7. **Dual vs single channel:** solo afirmar una mejora atribuible a dual channel si se mide en ambos modos con el mismo equipo, frecuencia, modelo, datos y configuración.

## 8. Evidencias y reproducibilidad

El operador ejecutó la prueba STREAM en `~/picchio-lab/ram-benchmark`, con fuente `stream.c`, binario `stream` y salida `stream-results.txt`. Los logs detallados de Picchio anteriores se registraron en:

- `/tmp/picchio-cpu-4threads.log`
- `/tmp/picchio-cpu-8threads.log`
- `/tmp/picchio-cpu-4threads.log` y `/tmp/picchio-cpu-8threads.log` son los nombres informados en las ejecuciones CPU-only; deben copiarse al directorio de evidencias para preservación duradera.

Los datos de esta sección proceden de las salidas de terminal facilitadas por el operador en la conversación. Los archivos originales aún no se han subido al repositorio. La siguiente actualización debe adjuntar `stream.c`, `stream-results.txt` y los logs originales de Picchio, además de los logs de la repetición controlada.

## 9. Referencias

- [Repositorio Picchio](https://github.com/robertosantosx2/picchio)
- [Repositorio LEONES](https://github.com/robertosantosx2/LEONES)
- [REDIL-IA distribuida en LEONES](https://github.com/robertosantosx2/LEONES/tree/main/docs/subprojects/REDIL-IA-distribuida)

---
*Informe incremental. Separar siempre mediciones observadas, hipótesis y resultados pendientes; no presentar estimaciones como hechos medidos.*
