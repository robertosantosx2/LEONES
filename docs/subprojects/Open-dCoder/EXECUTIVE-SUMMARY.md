# Open-dCoder — resumen ejecutivo y mapa de experimentos

**Actualizado:** 2026-10-31.  
**Plataforma medida:** Ubuntu, MSI Thin 15 B12UC, Intel Core i7-12650H (16 hilos), 14.8 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM).  
**Modelo:** `fredzzp/open-dcoder-0.5B`, snapshot `d0d86d5b99960c05258bb1f8265dd91564dbac67`.

## 1. Resumen ejecutivo

Se ha ejecutado Open-dCoder-0.5B localmente en la RTX 3050 de 4 GiB con PyTorch CUDA. La evaluación ha evolucionado desde una primera prueba funcional hasta un protocolo repetido con validador corregido y una prueba de batching real.

**Resultado principal actual:** V3 midió un máximo de **198.22 posiciones/s agregadas** con batch 4 y 16 pasos de difusión, manteniendo 12/12 salidas funcionales en la tarea factorial. La latencia de ese batch fue 1.292 s; el coste amortizado fue 0.323 s por secuencia. Para una sola petición, batch 1 / 16 pasos midió 0.460 s de mediana y 139.15 posiciones/s.

Estas métricas describen posiciones de salida procesadas por el algoritmo de difusión. **No son directamente equivalentes a tokens/s autoregresivos** de llama.cpp, TensorFold u otros motores LLM.

La conclusión es específica de una tarea de generación de código factorial. No constituye una puntuación general de inteligencia, coding benchmark ni ranking comparable con Artificial Analysis.

## 2. Mapa de experimentos y documentación

| Experimento / documento | Qué contiene | Resultado o estado |
|---|---|---|
| [Informe principal](README.md) | Contexto del proyecto, entorno, modelo, instalación, primera prueba y limitaciones | Registro introductorio |
| [Cuaderno V1/V2](EXPERIMENT-2026-10-31.md) | Metodología, parches locales, corrección del validador, resultados por repetición/configuración, auditoría temperature/top-k | V2 es la referencia single-sequence |
| [Experimento V3 — batching](EXPERIMENT-V3-BATCH-2026-10-31.md) | Batch real 1/2/4, 16/32/64 pasos, latencia, throughput, VRAM, auditoría de salidas | Nueve configuraciones completadas |
| [Índice de subproyectos LEONES](../README.md) | Navegación global de subproyectos | Índice general |

### Artefactos de ejecución V3 conservados en el equipo local

Identificador `20261031T110532Z`:

- `benchmark_opendcoder_v3_batch.py` — runner.
- `benchmark-v3-console.log` — consola completa.
- `benchmark-v3-results/opendcoder_v3_20261031T110532Z.csv` — medidas por repetición.
- `benchmark-v3-results/opendcoder_v3_20261031T110532Z_outputs.jsonl` — salidas y validación por secuencia.
- `benchmark-v3-results/opendcoder_v3_20261031T110532Z_summary.json` — resumen estructurado.

Estos nombres y ubicaciones corresponden al entorno local Ubuntu. El contenido binario completo de CSV/JSONL/runner no se incluye en este commit; el informe V3 publica las métricas visibles y la auditoría confirmada. Se podrán añadir los artefactos originales como siguiente paso de archivado.

## 3. Comparativa consolidada de referencias

| Versión | Diseño | Configuración de referencia | Mediana | Throughput | Funcionalidad | VRAM asignada |
|---|---|---|---:|---:|---:|---:|
| V1 | Secuencia única; validador con falsos negativos | 16 pasos | 0.446 s | 143.34 pos/s | validador no fiable | 1.184 GiB |
| V2 | Secuencia única; validador corregido | 16 pasos | 0.456 s | 140.30 pos/s | 3/3 | 1.184 GiB |
| V3 | Batch real | batch 1, 16 pasos | 0.460 s | 139.15 pos/s | 3/3 | 1.184 GiB |
| V3 | Batch real | batch 2, 16 pasos | 0.765 s | 167.37 pos/s agregadas | 6/6 | 1.427 GiB |
| V3 | Batch real | batch 4, 16 pasos | 1.292 s | **198.22 pos/s agregadas** | 12/12 | 1.910 GiB |

V1 se conserva como histórico de rendimiento, pero su validador no permite utilizar sus etiquetas funcionales. V2 corrigió el extractor y constituye el baseline fiable para una secuencia. V3 reproduce ese baseline con una diferencia de throughput de aproximadamente -0.8 % en batch 1 y añade el escalado por lotes.

## 4. Matriz completa V3

| Batch | Pasos | Posiciones/s | Sintaxis | Funcionalidad | VRAM asignada |
|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 139.15 | 100 % | 100 % | 1.184 GiB |
| 1 | 32 | 67.45 | 100 % | 33.3 % | 1.184 GiB |
| 1 | 64 | 35.33 | 100 % | 100 % | 1.184 GiB |
| 2 | 16 | 167.37 | 100 % | 100 % | 1.427 GiB |
| 2 | 32 | 83.53 | 100 % | 100 % | 1.427 GiB |
| 2 | 64 | 41.78 | 100 % | 100 % | 1.427 GiB |
| 4 | 16 | **198.22** | 100 % | 100 % | 1.910 GiB |
| 4 | 32 | 99.12 | 91.7 % | 66.7 % | 1.910 GiB |
| 4 | 64 | 49.55 | 100 % | 100 % | 1.910 GiB |

En batch 4 / 32 pasos, el CSV/JSONL local se auditó: 11/12 sintácticas y 8/12 funcionales. Hubo una salida con error de sintaxis y tres errores funcionales `NameError`.

## 5. Recomendaciones por objetivo

- **Menor latencia de una petición:** batch 1 / 16 pasos (0.460 s de mediana).
- **Equilibrio entre latencia de batch y throughput:** batch 2 / 16 pasos (0.765 s por batch, 167.37 posiciones/s agregadas).
- **Máximo throughput agregado medido:** batch 4 / 16 pasos (198.22 posiciones/s agregadas, 1.910 GiB VRAM asignada).

No se recomienda 32 pasos para esta tarea con la evidencia actual: presentó fallos funcionales en batch 1 y batch 4. 64 pasos obtuvo alta validez, pero es considerablemente más lento.

## 6. Límites compartidos y cuestiones abiertas

1. Una única tarea factorial; no permite inferir inteligencia general ni rendimiento de programación amplio.
2. El validador AST no es un sandbox y no comprueba por separado el requisito de impresión.
3. Transformers 4.54.1 avisa de que `temperature` y `top_k` pueden ignorarse. La inspección del código de difusión encuentra rutas que los leen, pero falta una ablación A/B que mida su efecto.
4. No se han medido energía, consumo sostenido ni rendimiento térmico a largo plazo.
5. Las posiciones/s de difusión no son equivalentes a tokens/s autoregresivos.
6. Faltan por subir al repositorio los ficheros binarios originales de resultados V3 (CSV, JSONL, JSON), el log y el script de ejecución; se identifican por sus nombres en el informe V3.
7. Debe añadirse hash de commit Open-dLLM, hash de los scripts y manifiesto exacto de dependencias en una repetición cerrada.

## 7. Próximas pruebas

- Incorporar los artefactos originales locales a GitHub.
- Repetir con más semillas y más tareas (Fibonacci, búsqueda binaria, ordenación, cadenas y estructuras de datos).
- Separar cumplimiento del prompt, sintaxis, funcionalidad y calidad de solución.
- Medir carga, TTFT/latencia inicial, energía, temperatura y potencia.
- Hacer ablaciones controladas de temperature/top-k y algoritmo.
- Explorar batch 8 solo si el presupuesto de VRAM y la estabilidad lo permiten.

## 8. Fuentes externas del proyecto

- [Open-dLLM upstream](https://github.com/zhangsheng93/Open-dLLM)
- [Modelo fredzzp/open-dcoder-0.5B en Hugging Face](https://huggingface.co/fredzzp/open-dcoder-0.5B)
