# Hardware-performance-MSI

**Informe de rendimiento de almacenamiento — MSI Thin 15 B12UC**  
**Fecha de medición:** 8 de noviembre de 2026  
**Equipo:** Ubuntu · Intel Core i7-12650H · NVIDIA GeForce RTX 3050 Laptop (4 GiB VRAM)  
**Unidad:** Micron 2400, modelo `Micron_2400_MTFDKBA1T0QFM`, firmware `V3MA002`  
**Interfaz:** PCIe 4.0 x4 (`16 GT/s`, anchura x4)  
**Herramienta:** fio 3.41

## 1. Resumen ejecutivo

El Micron 2400 ofrece un rendimiento de lectura secuencial elevado para el equipo: aproximadamente **4.47 GiB/s** en una lectura secuencial de 16 GiB. Cuatro lectores secuenciales concurrentes alcanzaron **4.49 GiB/s agregados**, por lo que la concurrencia aprovechó prácticamente todo el ancho de banda observado, pero no multiplicó la velocidad total.

En lectura aleatoria de bloques de 4 KiB, el rendimiento creció con la profundidad de cola: desde **11.4 kIOPS en QD1** hasta **344.4 kIOPS en QD32**. QD16 ofrece un compromiso interesante entre caudal y latencia: **248.5 kIOPS**, con latencia media total de unos **64 µs**.

La prueba de escritura secuencial alcanzó **2.72 GiB/s**, pero duró menos de seis segundos. No debe interpretarse como velocidad sostenida después de agotar la caché SLC.

**Conclusión operativa:** el almacenamiento no aparece como el primer cuello de botella para experimentar con carga/prefetch de expertos MoE. La siguiente validación debe reproducir lecturas de bloques grandes y accesos dispersos semejantes a los ficheros reales de expertos, midiendo además el tiempo hasta RAM/GPU. Estas pruebas de fio caracterizan el dispositivo; no son por sí mismas una medición de inferencia ni de carga de expertos.

## 2. Identificación y estado térmico

| Parámetro | Resultado |
|---|---:|
| Modelo | Micron 2400 — `Micron_2400_MTFDKBA1T0QFM` |
| Firmware | `V3MA002` |
| Enlace PCIe | Gen 4.0 x4, 16 GT/s |
| Temperatura antes de la batería larga | 34.9 °C (composite) |
| Temperatura tras las pruebas | 46.9 °C (composite) |
| Umbral SMART alto comunicado | 86.8 °C |
| Umbral SMART crítico comunicado | 89.8 °C |

No se obtuvo una lectura verificable del desgaste/vida útil SMART en esta sesión. Por tanto, este informe no certifica el estado de salud NAND ni el porcentaje de vida restante.

## 3. Resultados medidos

Las velocidades se expresan en MiB/s o GiB/s (base binaria), tal como las reporta fio.

### 3.1 Lectura y escritura secuencial

| Prueba | Tamaño | Resultado | Duración |
|---|---:|---:|---:|
| Escritura secuencial | 16 GiB | 2,785 MiB/s (≈2.72 GiB/s) | 5.882 s |
| Lectura secuencial | 16 GiB | 4,470 MiB/s (≈4.37 GiB/s) | 3.665 s |
| Cuatro lecturas secuenciales concurrentes | 132 GiB agregados | 4,493 MiB/s (≈4.39 GiB/s) | 30 s |

La lectura secuencial individual registró latencia total media de 893 µs con bloques de 1 MiB y QD4. La escritura registró 1,435 µs de latencia total media, también con bloques de 1 MiB y QD4.

La prueba concurrente mantuvo prácticamente el caudal de una sola lectura secuencial. El resultado agregado equivale aproximadamente a 1,123 MiB/s por flujo si se reparte uniformemente; esa cifra es una división orientativa, no una medición individual publicada por fio.

### 3.2 Lectura aleatoria 4 KiB

| Profundidad de cola | IOPS medios | Caudal | Latencia total media | Latencia de finalización p99 |
|---:|---:|---:|---:|---:|
| QD1 | 11,416 | 44.6 MiB/s | 85.87 µs | 260 µs |
| QD4 | 69,009 | 270 MiB/s | 57.60 µs | 141 µs |
| QD16 | 248,460 | 970 MiB/s | 64.16 µs | 145 µs |
| QD32 | 344,429 | 1,345 MiB/s | 92.60 µs | 172 µs |

Percentiles adicionales de latencia de finalización:

| QD | p50 | p90 | p95 | p99.9 |
|---:|---:|---:|---:|---:|
| QD1 | 62 µs | 137 µs | 165 µs | 293 µs |
| QD4 | 48 µs | 84 µs | 99 µs | 227 µs |
| QD16 | 55 µs | 87 µs | 100 µs | 245 µs |
| QD32 | 85 µs | 118 µs | 133 µs | 383 µs |

QD32 maximiza los IOPS de esta matriz, pero aumenta la latencia media frente a QD16. Además, el informe de fio mostró una carga elevada de CPU en QD32 (aproximadamente 24.36% de usuario y 72.77% de sistema), por lo que el coste de gestionar la concurrencia también debe considerarse.

## 4. Interpretación para LEONES, ODS y modelos MoE

### Hallazgos respaldados por las mediciones

1. **Lectura secuencial rápida:** se midieron 4,470 MiB/s en una lectura secuencial de 16 GiB.
2. **Concurrencia de lectores:** cuatro flujos concurrentes conservaron prácticamente el ancho de banda agregado de un único flujo secuencial.
3. **Aleatorio pequeño:** aumentar QD mejora mucho el caudal 4K, aunque a partir de QD16 el incremento de rendimiento viene acompañado de mayor latencia.
4. **Temperatura:** el máximo observado tras esta batería fue 46.9 °C composite; no se observó una aproximación a los umbrales SMART comunicados.

### Hipótesis de ingeniería que deben validarse

- Para lectura de expertos MoE, es probable que importen más los bloques de cientos de KiB o varios MiB, el patrón de offsets y la concurrencia real que el resultado 4K aislado.
- Un prefetch asíncrono con varias solicitudes en vuelo podría aprovechar mejor la unidad que una secuencia estrictamente QD1.
- Un caché de expertos calientes en RAM puede reducir lecturas repetidas, pero su beneficio depende de la distribución real de reutilización y de la presión sobre los 14 GiB de RAM del equipo.
- El ancho de banda del SSD no equivale al ancho de banda efectivo hacia la VRAM: deben medirse por separado lectura, copia a RAM, transferencia a GPU y tiempo de disponibilidad del experto.

Estas propuestas son hipótesis, no resultados medidos en Picchio, TensorFold, llama.cpp ni en una inferencia real.

## 5. Limitaciones y cautelas

- La escritura secuencial de 16 GiB duró aproximadamente 5.9 s. Es insuficiente para determinar el rendimiento sostenido tras agotar la caché SLC; no debe publicarse 2,785 MiB/s como velocidad sostenida de larga duración.
- La matriz aleatoria de 4 KiB es útil para caracterizar IOPS y latencia, pero no representa fielmente la lectura de tensores/expertos de gran tamaño.
- La prueba de cuatro lectores fue secuencial; no representa cuatro flujos de offsets aleatorios ni cuatro procesos leyendo expertos distintos.
- No se dispone aquí de un trace real de accesos a expertos. No se puede atribuir a estos resultados una mejora concreta de tokens/s o de tiempo de carga de un modelo.
- No quedó confirmado el estado de desgaste SMART. Debe obtenerse antes de establecer una línea base de salud del SSD.

## 6. Próxima batería recomendada

1. Obtener y archivar SMART completo: porcentaje de uso, unidades escritas/leídas, errores de medios, horas encendido y temperatura.
2. Crear un fichero de prueba temporal de 8 GiB y ejecutar lecturas aleatorias con bloques de 256 KiB, 1 MiB y 4 MiB; comparar QD1, QD4, QD8 y QD16.
3. Repetir con varios lectores concurrentes y distribución sesgada (expertos calientes/fríos), sin confundir el resultado sintético con un trace real.
4. Cuando esté disponible, capturar offsets/tamaños de lectura de un modelo MoE real y reproducirlos con fio o un pequeño replay harness.
5. Medir el pipeline completo: SSD → RAM → VRAM, incluyendo latencia p50/p95/p99, caudal, CPU, RAM, swap, VRAM y temperatura.
6. Realizar una prueba de escritura prolongada solo si hace falta caracterizar el comportamiento sostenido; controlar temperatura, espacio libre y volumen escrito.

## 7. Ficheros de resultados originales

Los informes de fio quedaron en:

`/home/ssantos/micron2400-results-20261108-165653/`

- `write.txt`
- `read.txt`
- `qd1.txt`
- `qd4.txt`
- `qd16.txt`
- `qd32.txt`
- `parallel.txt`

El fichero temporal de datos del benchmark fue eliminado al terminar la batería. Los resultados originales se generaron en el MSI; no se han adjuntado al repositorio en este commit.

## 8. Perfil provisional de almacenamiento del MSI

| Campo | Valor |
|---|---|
| Identificador | `MSI-MICRON2400-2026-11-08` |
| Estado de evidencia | Medido con fio 3.41 |
| Lectura secuencial | 4,470 MiB/s |
| Escritura secuencial corta | 2,785 MiB/s (no sostenida) |
| Lectura secuencial concurrente | 4,493 MiB/s agregados, 4 flujos |
| Lectura 4K aleatoria QD16 | 248,460 IOPS |
| Lectura 4K aleatoria QD32 | 344,429 IOPS |
| Temperatura máxima observada | 46.9 °C composite |
| SMART de desgaste | Pendiente de confirmar |

**Uso recomendado:** emplear este perfil como línea base de almacenamiento del MSI para experimentos LEONES/ODS. Mantener separados los campos `measured`, `estimated`, `recommended` y `configured`; no convertir estimaciones de rendimiento MoE en resultados medidos.
