# Picchio en MSI Thin 15: memoria DDR4, dual channel y escalado CPU

**Fecha de actualización:** 2026-11-08  
**Estado:** investigación en curso; STREAM y primera repetición controlada de Picchio CPU-only recibidos. Comparación de afinidad P/E y temperaturas/frecuencias aún pendiente.  
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


### 3.2 Repetición controlada 4–8–8–4 (2026-11-08)

Se completaron cuatro ejecuciones en modo CPU-only con Qwen3-30B-A3B INT4, contexto 512, 128 tokens, `PIN_GB=4`, cuatro hilos de I/O, mismo prompt, `SEED=12345` y rutas GPU desactivadas. Antes de cada ejecución se restauró la misma copia del hot-store persistente del modelo, ubicada en `$MODEL/.picchio_usage` (no en la raíz del repositorio). La copia de referencia quedó identificada por SHA-256:

`ae2ae0bc78853f3c0d9847f187a310c67660c4ea8de7970de779cc7963902efe`

Las cuatro ejecuciones informaron el mismo estado inicial: 1.182.336 rutas registradas, 41.453 aciertos de caché de 52.300 (79,3%) y 10.847 lecturas de disco. El checksum de la copia baseline se mantuvo idéntico al finalizar.

| Ejecución | Hilos | Tiempo total | Rendimiento calculado | MoE | Atención | LM head | Lectura de disco |
|---|---:|---:|---:|---:|---:|---:|---:|
| run1 | 4 | 100,9 s | 1,269 tok/s | 70,52 s | 24,66 s | 3,28 s | 39,09 s |
| run1 | 8 | 105,3 s | 1,216 tok/s | 74,53 s | 25,75 s | 2,83 s | 40,75 s |
| run2 | 8 | 108,7 s | 1,178 tok/s | 76,93 s | 26,73 s | 2,87 s | 42,08 s |
| run2 | 4 | 109,0 s | 1,174 tok/s | 75,17 s | 28,75 s | 2,86 s | 42,09 s |
| **Media 4 hilos** | **4** | **104,95 s** | **1,220 tok/s** | **72,85 s** | **26,71 s** | **3,07 s** | **40,59 s** |
| **Media 8 hilos** | **8** | **107,00 s** | **1,196 tok/s** | **75,73 s** | **26,24 s** | **2,85 s** | **41,42 s** |

El rendimiento calculado de cada fila es 128 tokens dividido por el tiempo total; las medias de rendimiento se calculan a partir del tiempo medio, no promediando cifras redondeadas de la interfaz. Con esta metodología, 8 hilos tardaron un 1,95% más que 4 hilos. La fase MoE fue un 3,96% más larga con 8 hilos; atención y LM head muestran diferencias pequeñas y de sentido distinto. RSS medio fue aproximadamente 8,76 GB en ambas configuraciones.

**Advertencia térmica y variabilidad:** antes de la tercera ejecución (la segunda de 8 hilos), `sensors` registró 96 °C en el paquete de CPU, después de la ejecución anterior de 8 hilos. No se registraron frecuencias ni temperaturas continuamente durante cada generación. La última ejecución de 4 hilos duró 109,0 s frente a 100,9 s en la primera. Por ello, el orden alternado no eliminó los efectos térmicos ni la variabilidad temporal. La diferencia media de 1,95% es pequeña y no debe considerarse una victoria estadísticamente sólida de 4 hilos; sí confirma que 8 hilos no produjo una mejora en esta tanda.

Los logs completos se guardaron localmente en `~/picchio-lab/results/dual-channel/`: `run1-4threads.log`, `run1-8threads.log`, `run2-8threads.log`, `run2-4threads.log` y `picchio_usage.baseline`. Los archivos originales todavía no se han incorporado al repositorio.

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
4. En la repetición controlada 4–8–8–4, las medias fueron 1,220 tok/s con cuatro hilos y 1,196 tok/s con ocho; ocho hilos tardaron un 1,95% más, una diferencia pequeña y potencialmente afectada por temperatura y variabilidad.
5. La repetición controló semilla y hot-store (mismo checksum de referencia), pero no la caché de páginas del sistema ni la temperatura/frecuencia durante cada ejecución.
6. No se ha demostrado que la RAM sea el cuello de botella de Picchio ni que dual channel duplique tokens/s. La selección de expertos, caché persistente, lecturas, atención, núcleos híbridos y planificación pueden explicar parte de las diferencias.

## 6. Siguiente experimento

La primera repetición controlada 4–8–8–4 ya está completada y resumida en §3.2. Próximos pasos:

1. Preservar los cuatro logs originales y la copia baseline en el repositorio como evidencia adjunta (actualmente solo están en el equipo local).
2. Repetir el benchmark con telemetría continua de temperatura, frecuencia efectiva, potencia y throttling durante la generación; registrar además `vmstat`/fallos de página y actividad de disco.
3. Ejecutar varias rondas con orden aleatorio o contrabalanceado y enfriamiento suficiente, informando mediana y dispersión.
4. Probar 12 y 16 hilos solo después de estabilizar las condiciones térmicas.
5. Identificar núcleos P/E del i7-12650H y comparar afinidad P-only, E-only y combinada.
6. Separar el coste de lectura física de expertos del coste de cómputo y atención.

No atribuir ninguna diferencia a dual channel sin una comparación single-channel controlada en el mismo equipo.

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

Los datos de STREAM y Picchio proceden de las salidas de terminal facilitadas por el operador. Los logs controlados están localmente en `~/picchio-lab/results/dual-channel/` y aún no se han subido. El operador generó el paquete local `~/picchio-dual-channel-evidence-20261108.tar.gz` (13 KiB, 2026-11-08 01:38) con `results/dual-channel/`. Verificó que el SHA-256 de `picchio_usage.baseline` y el hot-store restaurado en `~/picchio-data/qwen3-30b-a3b-int4/.picchio_usage` coincide exactamente: `ae2ae0bc78853f3c0d9847f187a310c67660c4ea8de7970de779cc7963902efe`. El paquete aún no está disponible en el repositorio; debe adjuntarse a la conversación o subirse por el operador para poder archivarlo. La siguiente actualización debe adjuntar `stream.c`, `stream-results.txt`, los logs originales de Picchio y los cuatro logs de esta repetición, además de la copia baseline. La ubicación del hot-store es el directorio del modelo (`~/picchio-data/qwen3-30b-a3b-int4/.picchio_usage`), no la raíz de `picchio-lab`.

## 9. Referencias

- [Repositorio Picchio](https://github.com/robertosantosx2/picchio)
- [Repositorio LEONES](https://github.com/robertosantosx2/LEONES)
- [REDIL-IA distribuida en LEONES](https://github.com/robertosantosx2/LEONES/tree/main/docs/subprojects/REDIL-IA-distribuida)

---
*Informe incremental. Separar siempre mediciones observadas, hipótesis y resultados pendientes; no presentar estimaciones como hechos medidos.*
