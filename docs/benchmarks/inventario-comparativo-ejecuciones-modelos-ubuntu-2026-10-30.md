# Inventario comparativo de ejecuciones locales de modelos — Ubuntu / LEONES (2026-10-30)

## Alcance y criterio

Consolidación de las ejecuciones físicas documentadas en LEONES hasta el 30-10-2026. Se incluyen inferencias funcionales y benchmarks sintéticos/API. No se mezclan como equivalentes las métricas de llama-bench, las métricas internas del CLI, las velocidades reportadas por una API ni las estimaciones derivadas del tiempo total.

**Equipo de referencia principal:** MSI Thin 15 B12UC, Intel Core i7-12650H (16 CPU lógicas), 14–14,8 GiB RAM, NVIDIA RTX 3050 Laptop 4 GiB, Ubuntu, driver 580.178.04, CUDA 13.0. Algunas ejecuciones se hicieron en otro equipo y se identifican por separado.

## 1. Cuadro comparativo principal

| Modelo | Equipo / motor | Artefacto / cuantización | Prefill | Generación | Artificial Analysis Intelligence Index | Estado / alcance |
|---|---|---|---:|---:|---|
| Qwen3.5-2B | MSI RTX 3050 · TensorFold 1.1.1 CUDA · API, 5 peticiones | MLX-4bit | 105,421 tok/s reportados (media); mediana 106,455 | 128 tokens por petición | **7*** (estimado; AA v4.3.2) | 5/5 HTTP 200; TTFT mediana 84,646 ms; 1,280760 s mediana de petición |
| Qwen3.5-2B | MSI RTX 3050 · TensorFold 1.1.1 CUDA · prueba previa | MLX-4bit | No registrado | 95,08 tok/s (32 tokens); 105,71 tok/s (128 tokens) | **7*** (estimado; AA v4.3.2) | Inferencias completadas; TTFT 88,2 / 94,1 ms |
| Qwen3.5-4B | MSI RTX 3050 · TensorFold CUDA · ejecución local | MLX-4bit | Prefill tok/s no registrado; latencia 190–209 ms | 53,64 (64 tokens); 53,42 (128 tokens) | **N/D v5.0** (13 histórico, v4.3) | Funcional; carga ~6,4 s; TTFT 193–212 ms |
| Qwen3.5-4B | MSI RTX 3050 · TensorFold CUDA · API, 3 peticiones | MLX-4bit | ~228–232 tok/s | Mediana 54,708 tok/s | **N/D v5.0** (13 histórico, v4.3) | 3/3 HTTP 200; 0,7066 s mediana petición; TTFT 130,3 ms |
| Qwen3.5-4B | MSI RTX 3050 · llama.cpp CUDA · CLI | GGUF Q4_K_M | 141,2 tok/s (prueba individual) | 42,4 tok/s | **N/D v5.0** (13 histórico, v4.3) | Respuesta coherente; VRAM observada después: 2.808 MiB |
| Qwen3.5-4B | MSI RTX 3050 · llama.cpp CUDA · API, 3 peticiones | GGUF Q4_K_M | No comparable disponible | Mediana 47,646 tok/s | **N/D v5.0** (13 histórico, v4.3) | 3/3 HTTP 200; 0,8680 s mediana petición; TTFT cliente no disponible |
| Qwen3.5-4B | MSI RTX 3050 · RustingStrata 1.0.1 CUDA · API, 3 peticiones | GGUF Q4_K_M | No comparable en API | No expuesta por API | **N/D v5.0** (13 histórico, v4.3) | 3/3 HTTP 200; 0,8384 s mediana petición; no convertir 32 tokens/tiempo en tok/s interno |
| Qwen3.5-4B | MSI RTX 3050 · RustingStrata bench | GGUF Q4_K_M | 915,3 tok/s PP128; 986,5 PP512 | 46,6 / 46,1 tok/s TG64 | **N/D v5.0** (13 histórico, v4.3) | Harness nativo; 3 repeticiones; ctx1024 |
| Qwen3-30B-A3B-Instruct-2507 | MSI RTX 3050 · llama.cpp CUDA · llama-bench | GGUF IQ3_XXS | Mediana PP128: 24,42 / 76,25 / 26,38 tok/s con 0 / 1 / 8 capas GPU | Mediana TG32: 1,45 / 1,44 / 1,88 tok/s | **N/D v5.0** (modelo 2507 marcado obsoleto) | 3 repeticiones por configuración; nueve ejecuciones, exit 0 |
| Qwen3-30B-A3B-Instruct-2507 | MSI RTX 3050 · llama.cpp CUDA · CLI, 6 ejecuciones | GGUF IQ3_XXS | 5,04–10,97 tok/s por ejecución en CSV head-to-head | Mediana calculada: 1,985 tok/s | **N/D v5.0** (modelo 2507 marcado obsoleto) | 6/6 exit 0; RSS máx. ~11,2–11,7 GiB en los registros resumidos; offload documentado |
| Qwen3-30B-A3B-Instruct-2507 | MSI RTX 3050 · RustingStrata 1.0.1 CUDA · CLI, 6 ejecuciones | GGUF IQ3_XXS | 11,71–20,03 tok/s en CSV head-to-head | Mediana calculada: 30,01 tok/s | **N/D v5.0** (modelo 2507 marcado obsoleto) | 6/6 exit 0; RSS ~7,0–8,0 GiB; variación entre ejecuciones |
| Qwen3-30B-A3B-Instruct-2507 | MSI RTX 3050 · RustingStrata CUDA · prueba individual anterior | GGUF IQ3_XXS | 7,74 tok/s (prompt observado) | 7,74 tok/s (generación registrada en ese ensayo) | **N/D v5.0** (modelo 2507 marcado obsoleto) | Ejecución real separada; no combinar con head-to-head de seis repeticiones |
| LFM3-1.7B Uncensored | MSI RTX 3050 · llama.cpp CUDA · llama-bench | GGUF AD-Q4_K_M | 4.326,68 tok/s PP512 | 117,29 tok/s TG128 | **Sin ficha/índice localizado** | 3 repeticiones; ±254,02 y ±0,27 respectivamente |
| LFM3-1.7B Uncensored | MSI RTX 3050 · llama.cpp CUDA · CLI interactivo | GGUF AD-Q4_K_M | 163,5–1.797,1 tok/s, según interacción | 99,8–104,4 tok/s | **Sin ficha/índice localizado** | Tres interacciones; no equiparar prefill posterior con PP512 |
| Ling-3.0-Tiny | MSI RTX 3050 · llama.cpp CUDA · CLI | GGUF IQ2_M | 62,5 tok/s en reintento funcional | 5,4 tok/s | **N/D v5.0** (12 histórico, v4.3) | Código Python factorial validado con 7 comprobaciones; prueba individual |
| Ling-3.0-Tiny | MSI RTX 3050 · llama.cpp CUDA · primera ejecución | GGUF IQ2_M | 68,7 tok/s | 8,3 tok/s | **N/D v5.0** (12 histórico, v4.3) | Salida truncada; 83,83 s; RSS máximo 2,89 GiB; no es prueba funcional completa |
| Ling-3.0-Tiny | GB-BXi7-5500 · llama.cpp CPU (4 hilos) | GGUF Q4_K_M | 41,0 tok/s | 15,5 tok/s | **N/D v5.0** (12 histórico, v4.3) | 16,72 s; RSS máximo 7,86 GiB; código factorial validado; equipo y cuantización distintos |
| Spark-X2.6-4B-abliterated | MSI RTX 3050 · llama.cpp CUDA b11740 · CLI | GGUF Q4_K_M | 36,9 tok/s (prueba funcional) | **7,2 tok/s** | **Sin ficha/índice localizado** | Respuesta completa; 256 tokens máximos solicitados; código 0 |
| Spark-X2.6-4B-abliterated | MSI RTX 3050 · llama.cpp CUDA b11740 · CLI, pruebas preliminares | GGUF Q4_K_M | 66,2 / 37,3 tok/s | 5,9 / 7,9 tok/s | **Sin ficha/índice localizado** | Salidas truncadas con límites de 32 y 128 tokens |

**Notas sobre el cuadro:**
- Las filas con distintas cuantizaciones, versiones del motor, prompts, límites de salida o protocolos no forman un ranking científico de modelos.
- Qwen3.5-4B TensorFold usa MLX-4bit; llama.cpp y RustingStrata usan GGUF Q4_K_M. No son exactamente el mismo artefacto.
- Para Qwen3-30B, la mediana de generación del head-to-head (1,985 tok/s llama.cpp y 30,01 tok/s RustingStrata) se ha calculado a partir de las seis filas de `results-summary.csv`; las longitudes generadas varían entre motores y ejecuciones. No presentarlo como comparación perfectamente equivalente.
- RustingStrata API Qwen3.5-4B no expone tok/s interno. El valor derivado de tokens/tiempo de petición (~38,17 tok/s) queda excluido de la columna de generación.
- Las métricas de generación de Spark y Ling son ejecuciones individuales, no medianas.

## 2. Comparación controlada por motor / modelo

### Qwen3.5-4B — tres runtimes (3 peticiones por runtime)

| Runtime | Artefacto | Mediana tok/s de salida | Mediana de petición | TTFT mediano |
|---|---|---:|---:|---:|
| TensorFold CUDA | MLX-4bit | **54,708** | **0,7066 s** | **0,1303 s** |
| llama.cpp CUDA | GGUF Q4_K_M | 47,646 | 0,8680 s | N/D |
| RustingStrata CUDA | GGUF Q4_K_M | N/D | 0,8384 s | N/D |

TensorFold fue el más rápido en esta prueba breve de API. La diferencia de cuantización impide atribuir toda la diferencia al motor. La salida se limitó a 32 tokens; sirve como instantánea de latencia, no como prueba de generación larga.

### Qwen3-30B-A3B — seis ejecuciones por motor

| Motor | Generación mediana calculada | RSS máximo observado en CSV | Ejecuciones |
|---|---:|---:|---:|
| llama.cpp CUDA | 1,985 tok/s | ~11,2–11,7 GiB | 6/6 código 0 |
| RustingStrata CUDA | 30,01 tok/s | ~7,0–8,0 GiB | 6/6 código 0 |

La prueba es evidencia de que ambos motores ejecutaron el modelo en el equipo. Sin embargo, las salidas generadas y tiempos de pared no fueron idénticos; revisar los logs brutos antes de usarla como afirmación comparativa definitiva.

## 3. Modelos examinados sin ejecución local validada

| Modelo / runtime | Qué se hizo | Estado correcto |
|---|---|---|
| Qwen3.5-4B en Magnitude 0.2.10 | Pesos y proyector descargados y hashes verificados; CLI no reconoció ID del modelo | No hubo inferencia ni métricas |
| Qwen3.5-35B-A3B IQ2_XXS | Descarga/inspección y diagnóstico de arquitectura; errores PTX en Strata; TensorFold estimado ~20,4 GB | Experimento inconcluso; sin tok/s validado |
| Clover-35B-A3B-Preview | Investigación documental de arquitectura y requisitos | No descargado ni ejecutado localmente |
| Mistral.rs | Instalación CUDA 0.9.5 documentada en la investigación | Sin resultados consolidados atribuibles a una inferencia medida |
| vLLM / SGLang / KTransformers | Evaluación de soporte y planificación | Sin benchmark local validado en este inventario |
| Qwen3.5-4B AWQ W4A16 | Inspección de ficha del candidato | No ejecutado; no tratar como prueba |
| Modelos de difusión de texto | Investigación de arquitecturas y compatibilidad | La investigación no equivale a ejecución ni rendimiento medido |

## 4. Lecturas principales

1. **LFM3-1.7B Q4_K_M** registra la mayor velocidad de generación sintética entre las pruebas con medición interna homogénea de `llama-bench` incluidas aquí: 117,29 tok/s. No implica superioridad de calidad.
2. **Qwen3.5-4B** tiene la comparación de tres runtimes más completa: TensorFold 54,708 tok/s, llama.cpp 47,646 tok/s y RustingStrata sin tok/s interno expuesto por API.
3. **Qwen3-30B-A3B IQ3_XXS** es ejecutable en la RTX 3050 con offload; el coste de generación es elevado en llama.cpp, mientras que RustingStrata registró cifras mayores en la tanda head-to-head. Requiere interpretar con cautela la distinta longitud de salida.
4. **Ling-3.0-Tiny** ejecutó y superó una prueba sencilla de código en dos equipos; las velocidades dependen fuertemente de la cuantización, CPU/GPU y configuración.
5. **Spark-X2.6-4B-abliterated** ha superado una prueba funcional de generación con 7,2 tok/s; aún falta repetirla con protocolo fijo y capturar memoria máxima.
6. **Qwen3.5-2B TensorFold** produjo alrededor de 105 tok/s en la prueba de API de cinco peticiones.
7. Los datos no justifican todavía un ranking de inteligencia/calidad: hacen falta prompts idénticos, tareas comunes, evaluación automática y varias repeticiones.

## 5. Pendientes para normalizar la matriz

- Fijar un protocolo común (mismo prompt, contexto, temperatura, tokens realmente generados y al menos 3–5 repeticiones).
- Registrar TTFT, prefill, decode, tiempo total, tiempo de carga, RSS máximo, pico VRAM, swap, temperatura y potencia.
- Confirmar capas efectivamente offloaded en cada runtime, no solo el parámetro solicitado.
- Mantener separados microbenchmarks nativos, API de servidor e inferencia CLI.
- Añadir pruebas de calidad comunes en español, razonamiento, código y factualidad.
- No rellenar huecos con estimaciones ni con resultados publicados por desarrolladores.

## 6. Fuentes LEONES

- [Informe de inferencia densa (ES)](report-inferencia-dense_Octubre26.md)
- [Qwen3.5-4B: benchmark de tres runtimes](../benchmarks/qwen35-4b-three-runtimes-2026-10-20.md)
- [Artefactos head-to-head Qwen3-30B-A3B](../benchmarks/artifacts/qwen3-30b-a3b-iq3-xxs/head-to-head-20261021/README.md)
- [LFM3-1.7B Uncensored](../subprojects/LFM3/README.md)
- [Ling 3.0 Tiny — MSI RTX 3050](ling-3.0-tiny-ubuntu-msi-rtx3050-2026-10-29.md)
- [Ling 3.0 Tiny — GB-BXi7-5500](ling-3.0-tiny-ubuntu-gb-bxi7-5500-2026-10-29.md)
- [Spark-X2.6-4B-abliterated — RTX 3050](../benchmarks/spark-x26-4b-abliterated-rtx3050-2026-10-30.md)
- [Magnitude + Qwen3.5-4B (fallo de catálogo, sin inferencia)](../benchmarks/magnitude-qwen35-4b-2026-10-21.md)
- [Clover-35B-A3B-Preview — investigación, no ejecutado](../../research/clover-35b-a3b-preview-experimental-2026-10.md)


## Artificial Analysis Intelligence Index — referencia externa

Se añade el Intelligence Index de Artificial Analysis como columna externa de referencia de capacidad. No es una medida de velocidad local y no se debe confundir con los tok/s medidos en el MSI. Los valores pueden ser estimados (marcados con *) y la versión del índice cambia.

| Modelo | Índice / estado en Artificial Analysis | Referencia |
|---|---:|---|
| Qwen3.5-2B (Reasoning) | **7***, estimado (v4.3.2) | [Artificial Analysis](https://artificialanalysis.ai/models/qwen3-5-2b/) |
| Qwen3.5-4B (Reasoning) | **N/D en v5.0**; 13 en la ficha histórica v4.3 | [Artificial Analysis](https://artificialanalysis.ai/models/qwen3-5-4b) |
| Qwen3-30B-A3B Instruct 2507 (no reasoning) | **N/D en v5.0**; la ficha 2507 aparece como obsoleta. La familia Qwen3 30B A3B tenía valores históricos estimados 9 (reasoning) / 7 (non-reasoning) en la ficha de lanzamiento anterior, no deben atribuirse sin matiz al GGUF 2507 | [Ficha 2507](https://artificialanalysis.ai/models/qwen3-30b-a3b-2507) · [ficha de lanzamiento de la familia](https://artificialanalysis.ai/es/models/releases/qwen3-30b-a3b-instruct) |
| Ling 3.0 Tiny (Reasoning) | **N/D en v5.0**; 12 en ficha histórica v4.3 | [Artificial Analysis](https://artificialanalysis.ai/models/ling-3-0-tiny) |
| LFM3-1.7B Uncensored | Sin ficha/índice exacto localizado | — |
| Spark-X2.6-4B-abliterated | Sin ficha/índice exacto localizado | — |

**Importante:** Artificial Analysis v5.0 es la versión actual del índice consultada para esta actualización. En Qwen3.5-4B y Ling 3.0 Tiny, las fichas actuales muestran N/A para el índice; las puntuaciones 13 y 12 son referencias históricas de v4.3 y se conservan solo para contexto. Qwen3.5-2B muestra una estimación de 7 en la ficha consultada (v4.3.2). No existe un valor oficial AA que podamos asignar a un modelo por similitud de tamaño, arquitectura o nombre. La ausencia de ficha no equivale a cero.
