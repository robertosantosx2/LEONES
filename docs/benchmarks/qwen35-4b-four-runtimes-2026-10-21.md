# Benchmark secuencial Qwen3.5-4B: cuatro runtimes — 2026-10-21

## Resumen

Ejecución local en Ubuntu sobre Intel Core i7-12650H, 14 GiB RAM y NVIDIA RTX 3050 Laptop de 4 GiB VRAM (driver 580.178.04; CUDA reportado 13.0). Se compararon TensorFold MLX-4bit, llama.cpp CUDA GGUF Q4_K_M, RustingStrata GGUF Q4_K_M y Mistral.rs GGUF Q4_K_M.

El protocolo fue secuencial: mismo prompt, temperatura 0, contexto 256, 30 tokens de prompt y límite de 32 tokens generados; tres requests medidos por motor, aparte del warm-up. Los doce requests medidos devolvieron HTTP 200. Los tiempos de carga se registraron por separado solo cuando el log daba una señal explícita y no deben confundirse con latencia de inferencia.

## Resultados agregados

| Motor | Latencia request mediana | Generación mediana | TTFT mediano | Carga registrada |
|---|---:|---:|---:|---|
| TensorFold MLX-4bit | 0,7068 s (aprox. 0,707 s) | 54,743 tok/s (aprox. 54,74) | 0,1306 s (aprox. 0,131 s) | 8,6 s según el log de TensorFold |
| llama.cpp CUDA GGUF Q4_K_M | 0,8337 s (aprox. 0,834 s) | 47,500 tok/s (aprox. 47,50) | n/d | El log contiene «loading model» y «model loaded», pero no una métrica de carga aislada y validada por el script |
| RustingStrata GGUF Q4_K_M | 0,8392 s (aprox. 0,839 s) | n/d | n/d | n/d |
| Mistral.rs GGUF Q4_K_M | 6,1753 s (aprox. 6,175 s) | 6,194 tok/s (aprox. 6,19) | n/d | 2,682 s desde «Loading model weights» hasta «Model loaded»; no incluye necesariamente todo el arranque |

## Datos por repetición

| Motor | Prueba | Latencia request (s) | Generación (tok/s) | TTFT (s) | Prefill (tok/s) |
|---|---:|---:|---:|---:|---:|
| TensorFold | 1 | 0,7065 | 54,751 | 0,1306 | n/d |
| TensorFold | 2 | 0,7068 | 54,714 | 0,1310 | n/d |
| TensorFold | 3 | 0,7128 | 54,743 | 0,1296 | n/d |
| llama.cpp CUDA | 1 | 0,8337 | 47,472 | n/d | n/d |
| llama.cpp CUDA | 2 | 0,8074 | 47,500 | n/d | n/d |
| llama.cpp CUDA | 3 | 0,8638 | 47,568 | n/d | n/d |
| RustingStrata | 1 | 0,8713 | n/d | n/d | n/d |
| RustingStrata | 2 | 0,8383 | n/d | n/d | n/d |
| RustingStrata | 3 | 0,8392 | n/d | n/d | n/d |
| Mistral.rs | 1 | 6,1753 | 6,124 | n/d | 40,107 |
| Mistral.rs | 2 | 6,2918 | 6,194 | n/d | 31,746 |
| Mistral.rs | 3 | 6,1406 | 6,234 | n/d | 36,946 |

Las mediciones del cliente y las métricas internas del servidor pueden diferir ligeramente por los límites de la solicitud, el recuento de tokens y el tiempo de procesamiento. No mezclar latencia total con velocidad de decode.

## Registro de carga y arranque

- **TensorFold:** el log reporta «loaded in 8.6s» para Qwen3.5-4B-MLX-4bit. El benchmark principal registra que el servicio quedó listo aproximadamente a los 9 segundos desde el inicio del bloque de arranque; ese intervalo redondeado no reemplaza el dato interno de carga.
- **llama.cpp CUDA:** el log registra la carga del GGUF y después «model loaded». El extracto disponible no proporciona una métrica normalizada de tiempo de carga; por eso se deja n/d y no se extrapola el tiempo de readiness del proceso.
- **RustingStrata:** el log disponible informa el plan de memoria (weights+state+scratch 2656 MB; KV 8 MB para 256 tokens; prefill 29 MB) y que empezó a escuchar en `127.0.0.1:18086`. No informa explícitamente el tiempo de carga.
- **Mistral.rs:** entre `Loading model weights.` a `2026-10-20T22:35:58.892824Z` y `Model loaded.` a `2026-10-20T22:36:01.575175Z` transcurren aproximadamente 2,682 s. El servicio siguió inicializando funciones PTX de CUDA y no respondió a `/v1/models` hasta más tarde; 2,682 s es solo esa fase de carga de pesos.

## Interpretación

TensorFold es el más rápido en esta configuración. Frente a llama.cpp, la mediana de generación es aproximadamente un 15,2 % superior. RustingStrata queda cerca de llama.cpp en latencia de request, pero el endpoint no aportó una métrica interna comparable de tok/s. Mistral.rs es el más lento de los cuatro en esta carga breve.

No se debe concluir que el runtime por sí solo explica la diferencia: TensorFold utiliza MLX-4bit, mientras los otros tres usan GGUF Q4_K_M. La prueba compara la experiencia práctica de estos despliegues concretos, no el mismo archivo de pesos con implementaciones distintas. Tampoco representa rendimiento sostenido, concurrencia, calidad de salida o integración con ODS.

## Alcance y limitaciones

- Una GPU local RTX 3050 Laptop con 4 GiB VRAM; no extrapolar a otras GPUs.
- Tres solicitudes medidas por motor y una fase de warm-up separada.
- Contexto 256, 30 tokens de prompt y límite de 32 tokens de salida.
- Los cuatro runtimes devolvieron HTTP 200.
- No se dispone de TTFT para llama.cpp, RustingStrata o Mistral.rs en el CSV; se registra n/d.
- No se infiere throughput de RustingStrata dividiendo tokens por la latencia de request.
- El tiempo de carga de pesos de Mistral.rs no equivale al tiempo total hasta que el servidor acepta requests.
- Los logs completos permanecen en el directorio local del usuario; este documento publica métricas y detalles disponibles, no afirma que los logs brutos estén incluidos en Git.

## Artefactos locales de origen

Directorio de ejecución: `~/qwen35-4b-benchmark-fixed-20261021-003555/`

Contiene `results.csv`, `summary.md`, `benchmark.log`, logs de servidor, `results.jsonl`, `warmup.jsonl` y metadatos de entorno. El CSV publicado junto a este informe es una transcripción de las métricas conocidas de las tres repeticiones; no sustituye los JSONL originales.
