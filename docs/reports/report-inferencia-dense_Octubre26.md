# Inferencia en RTX 3050 4Gb oct26 — informe reproducible

**Fecha de pruebas:** 22 de octubre de 2026  
**Estado:** benchmark inicial documentado; paquete de evidencias locales adjunto en la rama de esta PR.  
**Equipo:** Intel Core i7-12650H, 14 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM), CUDA 13.0, driver 580.178.04, compute capability sm_86.

> **Paquete de evidencias:** [descargar colección de resultados (tar.gz)](artifacts/inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz). Tamaño informado por GitHub: 25,853 bytes. SHA del blob de GitHub: `546f6c75bb449489ce6996047701ab08ca72c0a8`. El SHA-256 del archivo local está en `inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz.sha256` en el equipo que generó el paquete; no se ha publicado un archivo lateral de checksum independiente. Verifica el SHA-256 tras descargarlo usando el valor de origen local.

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
- `ngl=8` mostró una dispersión muy elevada en prefill; no debe atribuirse una causa sin repetir bajo condiciones controladas.
- La generación `tg32` se mantuvo aproximadamente entre 1.40 y 2.14 tok/s.
- La instantánea de `nvidia-smi` se recogió después de la ejecución, no durante ella; no representa utilización máxima.
- Un código de salida 0 no sustituye la comprobación de estabilidad, errores del driver y memoria durante la prueba.

## Experimento B — TensorFold

### Configuración y resultados

- Motor: TensorFold 1.1.1, backend CUDA.
- Modelo: `mlx-community/Qwen3.5-2B-MLX-4bit`.
- Contexto: 2048 tokens; paralelismo 1; thinking desactivado; temperatura 0; salida máxima 128 tokens.
- Cinco peticiones HTTP secuenciales; 66 tokens de entrada y 128 de salida reportados por petición; todas HTTP 200.

| Run | HTTP | Velocidad reportada (tok/s) | Tiempo cliente (s) | TTFT (s) | Prefill (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 200 | 107.068 | 1.249233 | 0.051058 | 0.048931 |
| 2 | 200 | 103.407 | 1.317400 | 0.084446 | 0.080437 |
| 3 | 200 | 106.496 | 1.280382 | 0.084646 | 0.080489 |
| 4 | 200 | 103.677 | 1.312622 | 0.084926 | 0.080445 |
| 5 | 200 | 106.455 | 1.280760 | 0.084702 | 0.080406 |

| Métrica | Media | Mediana | Mínimo | Máximo |
|---|---:|---:|---:|---:|
| Velocidad reportada (tok/s) | 105.421 | 106.455 | 103.407 | 107.068 |
| Tiempo HTTP cliente (s) | 1.288079 | 1.280760 | 1.249233 | 1.317400 |
| TTFT reportado (s) | 0.077956 | 0.084646 | 0.051058 | 0.084926 |
| Prefill reportado (s) | 0.074142 | 0.080437 | 0.048931 | 0.080489 |

Las cinco salidas tienen el mismo SHA-256: `942ca6d9de584e12bd4f207d8cafddcffb594924f5d781501b267b7a1ca9ddad`.

### Interpretación y limitaciones

- Todas las respuestas alcanzaron el máximo de 128 tokens; podrían estar truncadas.
- La latencia del cliente mide la petición HTTP completa y no equivale al tiempo interno de generación.
- La aceptación especulativa reportada fue de 1 token aceptado de 56 propuestos por petición (1.7857%).
- El hash idéntico solo confirma salida textual idéntica para este prompt/configuración.
- La captura de GPU al final no mide el pico durante cada petición.

## Ensayos anteriores: Qwen3.5-4B, tres motores

Resultados de ensayos previos documentados en conversaciones/salidas de terminal; no revalidados en esta actualización. El microbenchmark inicial de Strata usó contexto 1024 y salida tg64; el protocolo API posterior pretendía contexto 256 y máximo 32 tokens.

| Motor | Modelo/formato | Prefill | Decode | VRAM aprox. | Observaciones |
|---|---|---:|---:|---:|---|
| TensorFold | Qwen3.5-4B MLX-4bit | No registrado | 53.42–53.64 tok/s | 3120 MiB | Carga ~6.4 s; TTFT 0.193–0.212 s. |
| llama.cpp CUDA | Qwen3.5-4B GGUF Q4_K_M | 141.2 tok/s | 42.4 tok/s | 2808 MiB | `--n-gpu-layers 99`. |
| Rusting Strata 1.0.1 | Qwen3.5-4B GGUF Q4_K_M | 915.3 tok/s pp128; 986.5 pp512 | 46.6/46.1 tok/s tg64 | 2928 MiB | ctx=1024, 3 repeticiones. |

Comando de Strata registrado:

~~~bash
cd "$HOME/rusting-strata-test"
./target/release/strata bench --gpu \
  --model "$HOME/llama.cpp-cuda/models/qwen3.5-4b-Q4_K_M.gguf" \
  --pp 128,512 --tg 64 --reps 3 --ctx 1024
~~~

Advertencia: un intento anterior de TensorFold produjo 64 y 128 tokens aunque se configuró máximo 32. Hay que verificar los tokens reales en cada JSON.

## Qwen3.5-35B-A3B IQ2_XXS y errores no concluyentes

- Archivo: `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf`, 10,676,139,840 bytes.
- SHA-256 registrado: `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`.
- Strata identificó arquitectura qwen35moe, 40 capas, 256 expertos, 8 activos, embedding 2048.
- TensorFold MLX se estimó en unos 20.4 GB y se consideró inviable para el equipo de 14 GiB RAM / 4 GiB VRAM.
- No hay medición validada de TTFT/tok/s para el 35B; debe considerarse ensayo incompleto.
- Error de Strata observado en pruebas anteriores: `CUDA_ERROR_UNSUPPORTED_PTX_VERSION`. Cambiar cudarc de `cuda-13010` a `cuda-13000` permitió compilar, pero no resolvió el fallo de ejecución. GPU sm_86, driver 580.178.04, CUDA 13.0 y NVRTC 13.4.92.

## Estado de cobertura de motores

| Motor | Estado disponible | Pendiente |
|---|---|---|
| mistral.rs | Instalación CUDA 0.9.5 registrada; sin resultados comparables consolidados | Carga, versión, VRAM, TTFT, prefill/decode y repeticiones |
| vLLM | Propuesto, sin mediciones validadas | Verificar soporte de modelo/cuanti­zación y memoria |
| SGLang | Propuesto, sin mediciones validadas | Verificar soporte y capturar fallos |
| KTransformers | Propuesto, sin mediciones validadas | Verificar modelo, backend y memoria |
| TensorFold | Medido con Qwen3.5-2B y ensayo previo de 4B MLX | Homogeneizar protocolo y validar límites de salida |
| llama.cpp CUDA | Medido con Qwen3.5-4B y Qwen3-30B-A3B | Repetir con telemetría durante la ejecución |
| Rusting Strata | Medido con Qwen3.5-4B; inspección 35B y diagnóstico PTX | Sin rendimiento 35B validado |

No tratar motores sin medición como velocidad cero. Etiquetar como «no medido», «no compatible» o «falló al iniciar» según la evidencia.

## Reproducibilidad y artefactos

El paquete adjunto reúne scripts, registros disponibles, CSV/JSON, información del sistema y hashes. No incluye pesos de modelos ni cachés. El manifiesto de archivos ausentes debe leerse junto con el inventario: la ausencia de rutas explícitas no demuestra que la recopilación sea exhaustiva.

- [Recolector](https://github.com/robertosantosx2/LEONES/blob/docs/report-inferencia-denso-octubre-2026/scripts/benchmarks/collect-inferencia-rtx3050-oct26.sh)
- [Paquete de evidencias](artifacts/inferencia-rtx3050-4gb-oct26-collection-20261022-123939.tar.gz)
- [PR #112](https://github.com/robertosantosx2/LEONES/pull/112)

Para futuras comparaciones, fijar modelo/formato común, prompt/tokenizer, contexto, salida real, temperatura y repeticiones; medir TTFT, prefill/decode, tiempo total, tokens reales, VRAM/RAM pico, swap, temperatura/potencia GPU, códigos de salida y errores. Separar microbenchmarks nativos, pruebas API, intentos fallidos y evaluación de calidad.


## Seguimiento de pruebas MoE en TensorFold — 23/10/2026 (pruebas de carga, no benchmarks de generación)

Esta sección recoge pruebas adicionales realizadas con TensorFold en el mismo portátil Ubuntu tras el informe inicial. Los comandos y resultados proceden de las salidas de terminal compartidas durante la investigación; todavía no se ha adjuntado un paquete independiente con los logs brutos de estos intentos. Deben clasificarse como **resultados observados de inspección/carga**, no como benchmarks de generación satisfactorios.

### Hardware y versiones

- Equipo: Intel Core i7-12650H, aproximadamente 14,8 GiB de RAM física y NVIDIA RTX 3050 Laptop con 4 GiB de VRAM.
- Driver/CUDA: NVIDIA 580.178.04, CUDA 13.0; TensorFold identifica el chip como `nvidia-sm86`.
- Binarios inspeccionados: TensorFold 1.1.1, 1.1.2 y 1.1.3.
- Las tres versiones muestran `--backend {auto,mlx,cuda}`, `--device` y `--segments` en `serve --help`; las capacidades de 1.1.3 en este equipo solo declaran `cuda`. Ninguna muestra una opción explícita `--cpu-offload`. Esto no demuestra que no exista ningún mecanismo interno de descarga, pero no se verificó uno en estas pruebas.

### Prueba A — referencia funcional Qwen3.5-4B

El informe anterior registra TensorFold 1.1.1 con Qwen3.5-4B MLX-4bit a 53,42–53,64 tok/s en un protocolo previo. Notas de benchmarks locales posteriores informan de aproximadamente 54,4–54,8 tok/s de generación con TensorFold. Son ejecuciones y configuraciones diferentes y no deben combinarse en una sola estadística. El intervalo reciente es un resultado local comunicado; el log bruto completo no se ha adjuntado a esta actualización.

### Prueba B — inspección del checkpoint Qwen3.6-35B-A3B MLX-4bit

- Checkpoint: `TensorFold/Qwen3.6-35B-A3B-MLX-4bit-MTP`.
- TensorFold: 1.1.3.
- `info` reconoce la familia `qwen3_5_moe` y la arquitectura `Qwen3_5MoeForConditionalGeneration`.
- Cuantización: 4 bits, grupo 64.
- Pesos indicados: 19,47 GiB; memoria mínima estimada: 21,47 GiB (pesos más 2 GiB de margen de ejecución).
- El checkpoint se descargó y se inspeccionó. **No se completó ninguna ejecución de `serve` ni generación**, por lo que no hay mediciones de tok/s, TTFT ni de carga satisfactoria.
- Evaluación en este equipo: el mínimo estimado supera la memoria física disponible para el proceso; se clasifica como candidato inspeccionado pero no ejecutado, no como benchmark de generación fallido.

### Prueba C — Nemotron 3.5 Lightning 30B-A3B con TensorFold 1.1.3

- Checkpoint: `TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit`.
- `info` reconoce la familia `nemotron_h`, formato 4 bits/grupo 64, pesos de 17,27 GiB (18.544.232.887 bytes) y memoria mínima de 19,27 GiB.
- `capabilities --json` indicó motor `zig`, versión 1.1.3, chip `nvidia-sm86` y backend `["cuda"]`. La familia enumera los formatos `mlx-q4g64`, `modelopt-nvfp4` y `modelopt-ggml`.
- Se intentó ejecutar `serve` con `--backend auto --parallel 1 --context 512 --temperature 0 --no-thinking`, host `127.0.0.1`, puerto `18089`.
- Resultado: rechazo antes de inferencia. El error informó de 16,6 GiB de pesos frente a un presupuesto CUDA efectivo de 2,6 GiB (3,6 GiB libres menos una reserva de 1 GiB). Una consulta posterior con `info` indicó el tamaño más preciso de 17,27 GiB.
- El backend `auto` produjo el mismo rechazo; el servidor HTTP no arrancó y no se generaron tokens. No hay mediciones de tok/s ni TTFT.
- La captura de `nvidia-smi` durante el diagnóstico mostró 15 MiB usados de 4096 MiB, con 4 MiB correspondientes a Xorg; esto respalda que el rechazo se debió al tamaño del modelo respecto al presupuesto CUDA disponible, no a otro proceso grande usando la GPU.
- Reducir el contexto a 512 no reduce suficientemente el tamaño de los pesos. No se identificó una configuración funcional de descarga a CPU/RAM entre las opciones públicas de CLI inspeccionadas.

### Resumen del estado de pruebas MoE con TensorFold

| Modelo | Versión | Resultado | Pesos / mínimo estimado | Métricas de generación |
|---|---|---|---|---|
| Qwen3.5-4B MLX-4bit | 1.1.1 / pruebas locales posteriores | Inferencia satisfactoria en pruebas previas | Modelo más pequeño; ver secciones/logs anteriores | Anterior: 53,42–53,64 tok/s; posterior comunicado: 54,4–54,8 tok/s; protocolos distintos |
| Qwen3.6-35B-A3B MLX-4bit-MTP | 1.1.3 | Descargado e inspeccionado; no ejecutado con `serve` | 19,47 / 21,47 GiB | No medido |
| Nemotron 3.5 Lightning 30B-A3B MLX-4bit | 1.1.3 | `serve` rechazado por presupuesto de memoria CUDA | 17,27 / 19,27 GiB | No medido; cero tokens generados |

**Clasificación de evidencias:** Qwen3.5-4B es la referencia medida con inferencia satisfactoria. Qwen3.6-35B-A3B está inspeccionado pero no ejecutado. Nemotron 30B-A3B es un intento de carga fallido, no un benchmark de inferencia. No se debe registrar ninguno de los dos intentos con modelos grandes como 0 tok/s: su velocidad de generación está **sin medir**.
