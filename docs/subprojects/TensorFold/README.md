# TensorFold — auditoría e integración de inferencia local

**Estado:** subproyecto documental; auditoría estática de regresión CUDA completada, reproducción física pendiente.  
**Equipo de referencia:** Ubuntu, MSI Thin 15 B12UC, Intel Core i7-12650H, 16 hilos lógicos, 14.8 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB VRAM.

## Documentación y experimentos

- [Auditoría profunda de la regresión de memoria CUDA en Qwen3.5-4B (2026-11-01)](CUDA-MEMORY-REGRESSION-2026-11-01.md) — commit causal, reconstrucción detallada del scratch, geometría, arena, tablas, tap ring, KV/paging, rutas opcionales, diagnóstico de admisión y plan de reproducción.
- [Issue upstream #1827](https://github.com/ashhart/TensorFold/issues/1827) — seguimiento con mantenedores.
- [Commit upstream que introduce chunks de 4096 filas](https://github.com/ashhart/TensorFold/commit/c50b59a23418c3f8436db68827ab8fe45ea5c603).

## Resumen técnico

La capacidad máxima de filas del prompt pasó de 128 a 4096. El motor usa esa capacidad para dimensionar el scratch del arena CUDA, aunque el prompt configurado sea mucho menor.

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
- No se han repetido pruebas GPU para este informe.
- No se ha modificado código ni preparado un parche.
- La reducción de scratch es una hipótesis de diseño pendiente de auditoría de lifetimes, kernels, streams y CUDA Graphs.

## Regla LEONES

Las cifras derivadas de fórmulas se etiquetan como cálculos; solo las ejecuciones instrumentadas sobre el equipo real producen nuevas mediciones LEONES. No se declara resuelto el incidente hasta reproducir y aislar ambos caminos de fallo.
