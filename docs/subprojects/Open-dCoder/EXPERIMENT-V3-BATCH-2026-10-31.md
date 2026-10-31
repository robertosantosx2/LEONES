# Open-dCoder — experimento V3: batching real en RTX 3050

**Fecha local:** 2026-10-31.  
**Identificador de ejecución:** `20261031T110532Z` (timestamp UTC generado por el script).  
**Estado:** MEASURED — nueve configuraciones ejecutadas, tres repeticiones medidas por configuración y un warmup excluido.  
**Modelo:** `fredzzp/open-dcoder-0.5B`, snapshot HF `d0d86d5b99960c05258bb1f8265dd91564dbac67`.  
**Equipo:** Ubuntu, MSI Thin 15 B12UC, Intel Core i7-12650H (16 hilos), 14.8 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM), driver 580.178.04, CUDA 13.0.

Este documento registra el experimento V3 y complementa el [cuaderno V1/V2](EXPERIMENT-2026-10-31.md), que contiene el detalle del entorno, los parches de compatibilidad, el validador y las primeras mediciones.

## 1. Objetivo

Medir el escalado de Open-dCoder al procesar varias secuencias simultáneamente mediante **batch real** en la GPU, y cuantificar el compromiso entre throughput, latencia, validez funcional y memoria.

V3 no es una evaluación general de inteligencia. La única tarea evaluada es la generación de una función factorial recursiva en Python.

## 2. Entorno y modelo

Se conserva el entorno descrito en el cuaderno V1/V2:

- Ubuntu; MSI Thin 15 B12UC.
- Intel Core i7-12650H, 16 hilos lógicos; 14.8 GiB RAM.
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM.
- NVIDIA driver 580.178.04; CUDA 13.0.
- Python 3.12.15; PyTorch 2.11.0+cu128; Transformers 4.54.1; huggingface-hub 0.36.2; psutil 7.2.2.
- Modelo `fredzzp/open-dcoder-0.5B`, BF16, 494,032,768 parámetros.
- Snapshot Hugging Face: `d0d86d5b99960c05258bb1f8265dd91564dbac67`.

Se empleó el mismo camino de inferencia local `Qwen2ForCausalLM` + `model.diffusion_generate`. Los parches locales de inicializadores descritos en V1/V2 seguían presentes. El aviso single-process de VeOmni es esperado en esta ejecución de una sola GPU.

## 3. Protocolo V3

| Parámetro | Valor |
|---|---|
| Batch sizes | 1, 2, 4 |
| Pasos de difusión | 16, 32, 64 |
| Posiciones solicitadas por secuencia | 64 |
| Warmup | 1 por configuración, excluido |
| Repeticiones medidas | 3 por configuración |
| Total | 9 configuraciones; 27 batches medidos |
| Semilla base | 20261101 |
| Algoritmo | `p2` |
| `temperature` | 0.2 |
| `top_k` | 200 |
| `alg_temp` | 0.5 |
| `num_return_sequences` | 1 |
| Historial de generación | desactivado |

**Batch real:** el tensor de entrada se construyó repitiendo el prompt en B filas (`base_ids.repeat(batch, 1)`). No se utilizó `num_return_sequences > 1`. El script comprobó que la salida contuviera B filas y que cada secuencia tuviera exactamente 64 posiciones antes de decodificarla.

Las semillas se asignaron por llamada de batch. Las trayectorias aleatorias de secuencias individuales no están emparejadas entre diferentes tamaños de batch; por ello, la comparación de calidad entre batch sizes es descriptiva, no un diseño de semillas emparejadas.

### Métricas

- **Latencia batch:** tiempo CUDA sincronizado para producir las B secuencias.
- **Coste amortizado por secuencia:** latencia batch / B. Es un coste agregado repartido, no la latencia real de una petición individual.
- **Secuencias/s:** B / latencia batch.
- **Posiciones/s:** (64 × B) / latencia batch. No equivale a tokens/s autoregresivos.
- **VRAM:** máximos de memoria asignada y reservada por PyTorch.
- **RAM:** RSS del proceso y RAM disponible observadas antes/después de cada repetición; son instantáneas, no máximos muestreados.
- **Validez sintáctica y funcional:** validador AST/funcional de V2.

El validador comprueba sintaxis, localización de función independiente o método `Solution.factorial`, y los casos `factorial(5) == 120` y `factorial(-1)` que debe lanzar `ValueError`. No ejecuta el módulo completo, no verifica por separado el `print(factorial(5))` y no es un sandbox general. Los detalles están en [V1/V2, sección de evolución del validador](EXPERIMENT-2026-10-31.md#3-evolución-del-validador).

## 4. Resultados consolidados

Los tiempos son medianas de tres repeticiones. Las tasas son throughput agregado.

| Batch | Pasos | Mediana batch (s) | Coste amortizado/seq. (s) | Secuencias/s | Posiciones/s | Sintaxis | Funcional | VRAM asignada (GiB) | VRAM reservada (GiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 0.460 | 0.460 | 2.17 | 139.15 | 100 % | 100 % | 1.184 | 1.332 |
| 1 | 32 | 0.949 | 0.949 | 1.05 | 67.45 | 100 % | 33.3 % | 1.184 | 1.332 |
| 1 | 64 | 1.811 | 1.811 | 0.55 | 35.33 | 100 % | 100 % | 1.184 | 1.334 |
| 2 | 16 | 0.765 | 0.382 | 2.62 | 167.37 | 100 % | 100 % | 1.427 | 1.668 |
| 2 | 32 | 1.532 | 0.766 | 1.31 | 83.53 | 100 % | 100 % | 1.427 | 1.668 |
| 2 | 64 | 3.064 | 1.532 | 0.65 | 41.78 | 100 % | 100 % | 1.427 | 1.668 |
| 4 | 16 | 1.292 | 0.323 | 3.10 | 198.22 | 100 % | 100 % | 1.910 | 2.338 |
| 4 | 32 | 2.583 | 0.646 | 1.55 | 99.12 | 91.7 % | 66.7 % | 1.910 | 2.338 |
| 4 | 64 | 5.167 | 1.292 | 0.77 | 49.55 | 100 % | 100 % | 1.910 | 2.338 |

### 4.1 Repeticiones y dispersión

**Batch 1**

| Pasos | Repetición 1 (s) | Repetición 2 (s) | Repetición 3 (s) | Funcionales |
|---:|---:|---:|---:|---:|
| 16 | 0.454 | 0.460 | 0.469 | 3/3 |
| 32 | 0.973 | 0.949 | 0.904 | 1/3 |
| 64 | 1.811 | 1.816 | 1.749 | 3/3 |

**Batch 2**

| Pasos | Repetición 1 (s) | Repetición 2 (s) | Repetición 3 (s) | Funcionales |
|---:|---:|---:|---:|---:|
| 16 | 0.781 | 0.765 | 0.765 | 6/6 |
| 32 | 1.533 | 1.531 | 1.532 | 6/6 |
| 64 | 3.064 | 3.176 | 3.063 | 6/6 |

**Batch 4**

| Pasos | Repetición 1 (s) | Repetición 2 (s) | Repetición 3 (s) | Funcionales |
|---:|---:|---:|---:|---:|
| 16 | 1.367 | 1.292 | 1.291 | 12/12 |
| 32 | 2.583 | 2.595 | 2.582 | 8/12 |
| 64 | 5.167 | 5.164 | 5.169 | 12/12 |

## 5. Auditoría de batch 4 / 32 pasos

La consola resumida no reflejó adecuadamente el detalle de la validación. Se auditaron posteriormente el CSV y el JSONL originales locales. Los recuentos confirmados son:

| Repetición | Sintaxis | Funcionalidad |
|---:|---:|---:|
| 1 | 3/4 | 3/4 |
| 2 | 4/4 | 2/4 |
| 3 | 4/4 | 3/4 |
| **Total** | **11/12 (91.7 %)** | **8/12 (66.7 %)** |

El JSONL identifica una salida con error de sintaxis y tres salidas sintácticamente válidas que fallaron con `NameError` durante la ejecución aislada. Por tanto, el resumen agregado 91.7 % / 66.7 % es correcto; no debe sustituirse por el recuento visual de la consola.

## 6. Escalado de throughput

A 16 pasos:

| Batch | Posiciones/s | Mejora frente a batch 1 | VRAM asignada |
|---:|---:|---:|---:|
| 1 | 139.15 | referencia | 1.184 GiB |
| 2 | 167.37 | +20.3 % | 1.427 GiB |
| 4 | 198.22 | +42.5 % | 1.910 GiB |

El batching aumenta el throughput agregado, pero no de forma lineal. Batch 4 procesa más posiciones por segundo a cambio de más memoria y una latencia de batch superior. El coste amortizado no debe confundirse con la latencia percibida por una sola petición.

No hubo errores CUDA OOM en ninguna de las nueve configuraciones. En batch 4 se registraron 1.910 GiB asignados y 2.338 GiB reservados. El RSS del proceso observado durante las repeticiones fue aproximadamente 1.559–1.578 GiB. La RAM disponible se registró en el CSV, pero no se reproduce aquí porque no se ha incorporado su valor numérico a este informe.

## 7. Comparación V2 frente a V3

La comparación equivalente es V2 (batch 1, 16 pasos) frente a V3 (batch 1, 16 pasos):

| Experimento | Mediana | Posiciones/s | VRAM asignada | Funcional |
|---|---:|---:|---:|---:|
| V2, batch 1, 16 pasos | 0.456 s | 140.30 | 1.184 GiB | 3/3 |
| V3, batch 1, 16 pasos | 0.460 s | 139.15 | 1.184 GiB | 3/3 |

La diferencia de throughput es aproximadamente -0.8 %. V3 reproduce razonablemente el baseline V2 antes de medir batching.

## 8. Conclusiones

1. El batch real funciona y mejora el throughput agregado en la RTX 3050 Laptop.
2. La configuración más rápida observada fue **batch 4 / 16 pasos: 198.22 posiciones/s**, 3.10 secuencias/s, 1.292 s por batch y 100 % de éxito funcional en 12 salidas medidas.
3. Batch 2 / 16 pasos es una alternativa con menor latencia de batch (0.765 s) y 167.37 posiciones/s.
4. Batch 1 / 16 pasos conserva la menor latencia de respuesta individual medida (mediana 0.460 s).
5. El rendimiento disminuye al aumentar los pasos de difusión; 32 pasos mostró resultados funcionales variables en batch 1 y batch 4.
6. Batch 4 / 64 pasos logró 12/12 funcionales, pero solo 49.55 posiciones/s.
7. No se produjo OOM; la VRAM asignada máxima entre estas configuraciones fue 1.910 GiB.
8. La mejor configuración depende del objetivo: baja latencia individual (batch 1), equilibrio de latencia y throughput (batch 2), o throughput agregado (batch 4).
9. Una tarea factorial no permite inferir capacidad general ni establecer un ranking de inteligencia.
10. Posiciones/s no debe compararse sin matices con tokens/s autoregresivos.

## 9. Avisos y limitaciones

- Transformers 4.54.1 siguió mostrando: `The following generation flags are not valid and may be ignored: ['temperature', 'top_k']`. La inspección de código del cuaderno V1/V2 encontró rutas que consumen estos parámetros, pero no se ha realizado una prueba A/B controlada que confirme su efecto efectivo. Se mantiene como limitación abierta.
- El warning de VeOmni sobre estado distribuido single-process es esperado.
- Una semilla se aplica por batch; no hay emparejamiento de trayectoria RNG por secuencia entre batch sizes.
- RSS y RAM disponible son lecturas instantáneas antes/después, no perfiles de máximos.
- El validador AST no es un sandbox general y no verifica por separado el print solicitado.
- No se midieron energía, potencia sostenida ni temperatura bajo carga durante todo el benchmark.
- No se dispone en esta publicación del contenido bruto completo de las salidas JSONL; el detalle de batch 4 / 32 se auditó en el equipo local. Los artefactos locales se enumeran a continuación para su posterior incorporación íntegra.

## 10. Artefactos locales de esta ejecución

En el equipo Ubuntu, el script generó:

- `~/open-dcoder/benchmark-v3-results/opendcoder_v3_20261031T110532Z.csv`
- `~/open-dcoder/benchmark-v3-results/opendcoder_v3_20261031T110532Z_outputs.jsonl`
- `~/open-dcoder/benchmark-v3-results/opendcoder_v3_20261031T110532Z_summary.json`
- `~/open-dcoder/benchmark-v3-console.log`

El script ejecutado fue `~/open-dcoder/benchmark_opendcoder_v3_batch.py`. Los ficheros originales siguen siendo la fuente primaria de los registros por repetición. **No se afirma que estos ficheros binarios/locales estén subidos a GitHub en este commit**; esta página conserva los datos numéricos y el análisis que constan en el registro de ejecución compartido.

## 11. Relación con el resto de la documentación

- [Resumen ejecutivo y mapa de experimentos](EXECUTIVE-SUMMARY.md)
- [Informe principal Open-dCoder](README.md)
- [Cuaderno V1/V2: entorno, validador, resultados y auditoría de parámetros](EXPERIMENT-2026-10-31.md)
- [Índice de subproyectos LEONES](../README.md)
- [Open-dLLM upstream](https://github.com/zhangsheng93/Open-dLLM)
- [Modelo en Hugging Face](https://huggingface.co/fredzzp/open-dcoder-0.5B)
