# TensorFold — auditoría e integración de inferencia local

**Estado:** auditoría estática inicial completada; corrección de scratch diferido implementada y validada en GPU real; PR upstream #1879 abierto y pendiente de revisión/fusión.  
**Equipo de referencia:** Ubuntu, MSI Thin 15 B12UC, Intel Core i7-12650H, 16 hilos lógicos, 14.8 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB VRAM.

## Documentación y experimentos

- [Corrección CUDA con scratch diferido — implementación, validación, instalación local y PR #1879 (2026-11-02)](CUDA-LAZY-SCRATCH-FIX-PR1879-2026-11-02.md) — cinco archivos modificados, 230 inserciones/28 eliminaciones, build CUDA 114/114, tests host 43/43 y ejecución en RTX 3050 4 GiB. Incluye inventario del checkout, binario 1.1.6, toolchain, checkpoint, recursos del sistema, servicios/puertos y comandos para capturar recibos reproducibles; PR abierto y pendiente de revisión/fusión.

- [Auditoría profunda de la regresión de memoria CUDA en Qwen3.5-4B (2026-11-01)](CUDA-MEMORY-REGRESSION-2026-11-01.md) — commit causal, reconstrucción detallada del scratch, geometría, arena, tablas, tap ring, KV/paging, rutas opcionales, diagnóstico de admisión y plan de reproducción.
- [Issue upstream #1827](https://github.com/ashhart/TensorFold/issues/1827) — seguimiento con mantenedores.
- [Commit upstream que introduce chunks de 4096 filas](https://github.com/ashhart/TensorFold/commit/c50b59a23418c3f8436db68827ab8fe45ea5c603).

## Resumen técnico

La auditoría inicial identificó que la capacidad máxima de filas del prompt (4096 frente a 128) inflaba la reserva anticipada de scratch. El parche posterior separa el scratch del arena de pesos y lo asigna de forma diferida según las filas requeridas, con crecimiento controlado y gestión segura de CUDA Graphs.

Para el checkpoint denso `mlx-community/Qwen3.5-4B-MLX-4bit`, la reconstrucción por fórmulas estima:

| Concepto | 128 filas | 4096 filas |
|---|---:|---:|
| Scratch escalado por filas | 19.484 MiB | 623.500 MiB |
| Scratch total aproximado | 209.169 MiB | 814.185 MiB |

Incremento total aproximado: **605.016 MiB**. Cálculo derivado de fuentes, no medición física.

La auditoría separa esta regresión posterior a la admisión del motor del rechazo temprano de pesos (aprox. 2.8 GiB frente a 2.6 GiB de presupuesto), que debe investigarse comparando estado GPU, procesos, checkpoint y variables de entorno.

## Evidencia y estado

- TensorFold 1.1.2 ejecutó históricamente Qwen3.5-4B en la RTX 3050: carga ~7.2 s, ~54.2 tok/s, prefill ~0.195 s y TTFT ~0.198 s.
- Versiones posteriores 1.1.5, 1.1.6 y 1.2.0 presentaron rechazos OOM durante la investigación.
- Parche implementado en cinco archivos y publicado en PR #1879.
- Build CUDA: 114/114 pasos correctos para sm_86 ReleaseFast.
- Tests host: 43/43 correctos.
- GPU real RTX 3050: ejecución hasta 512 filas; step/window byte-identical en los tamaños comparados 64/256/512; decode ≈56.5 tok/s.
- Workspace INT8: crecimiento probado hasta 128 filas.
- Pendiente benchmark A/B idéntico, draft:false, prompts reanudados, concurrencia y backends no CUDA.

## Regla LEONES

Las cifras derivadas de fórmulas se etiquetan como cálculos; solo las ejecuciones instrumentadas sobre el equipo real producen nuevas mediciones LEONES. No se declara resuelto el incidente hasta reproducir y aislar ambos caminos de fallo.
