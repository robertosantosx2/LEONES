# Inventario comparativo de pruebas locales de Qwen3.5 — actualizado 2026-10-21

**Equipo de referencia:** Ubuntu nativo; Intel Core i7-12650H; 14 GiB RAM; NVIDIA GeForce RTX 3050 Laptop (4 GiB VRAM); driver 580.178.04; CUDA indicado por `nvidia-smi` 13.0.

## Criterio de registro

- **MEASURED / completada:** el motor cargó el modelo en el equipo físico y produjo salida de inferencia.
- Los intentos fallidos se conservan como incidencias y no invalidan pruebas posteriores completadas.
- VRAM del proceso y memoria total de GPU son métricas distintas.
- Las velocidades proceden de muestras cortas. Los resultados entre motores son orientativos salvo que compartan artefacto, protocolo y medición.
- En el benchmark secuencial del 2026-10-21 se usaron 3 repeticiones medidas por motor, contexto 256, temperatura 0, 30 tokens de prompt y 32 tokens de salida; todos los requests medidos devolvieron HTTP 200.
- TensorFold usa MLX-4bit; llama.cpp, RustingStrata y Mistral.rs usan GGUF Q4_K_M. No es una comparación de cuantizaciones ni artefactos idénticos.

## Comparativa más reciente: Qwen3.5-4B, benchmark secuencial 2026-10-21

| Motor | Modelo / formato | Mediana de latencia total de request | Mediana de generación | TTFT mediano | Carga del modelo registrada | Estado |
|---|---|---:|---:|---:|---|---|
| TensorFold native | Qwen3.5-4B MLX-4bit | 0,707 s | 54,74 tok/s | 0,131 s | 8,6 s en log del runtime | Completado |
| llama.cpp CUDA | Qwen3.5-4B GGUF Q4_K_M | 0,834 s | 47,50 tok/s | n/d | El log registra «loading model» y «model loaded», pero el benchmark no separa de forma fiable una duración pura de carga | Completado |
| RustingStrata | Qwen3.5-4B GGUF Q4_K_M | 0,839 s | n/d | n/d | n/d; el log registra el plan de memoria y el inicio de escucha, no una duración de carga | Completado |
| Mistral.rs | Qwen3.5-4B GGUF Q4_K_M | 6,175 s | 6,19 tok/s | n/d | 2,68 s entre «Loading model weights» y «Model loaded»; no equivale al arranque total del servicio | Completado |

TensorFold obtuvo la menor latencia mediana y aproximadamente un **15,2 % más de velocidad de generación** que llama.cpp en esta configuración. RustingStrata tuvo latencia total cercana a llama.cpp, pero no se obtuvo una métrica de generación compatible y no debe inferirse su tok/s a partir de 32 tokens divididos por la latencia. Mistral.rs fue considerablemente más lento en esta prueba.

### Valores por repetición (resumen)

| Motor | Latencia total por repetición (s) | Generación por repetición (tok/s) | TTFT por repetición (s) |
|---|---|---|---|
| TensorFold | 0,7065; 0,7068; 0,7128 | 54,751; 54,714; 54,743 | 0,1306; 0,1310; 0,1296 |
| llama.cpp CUDA | 0,8337; 0,8074; 0,8638 | 47,472; 47,500; 47,568 | n/d |
| RustingStrata | 0,8713; 0,8383; 0,8392 | n/d | n/d |
| Mistral.rs | 6,1753; 6,2918; 6,1406 | 6,124; 6,194; 6,234 | n/d |

Los tiempos anteriores son métricas de request del benchmark, no tiempos de carga del modelo. Consulte el informe dedicado para configuración, detalles de arranque y limitaciones.

## Resultados anteriores conservados

| Fecha | Motor / versión | Modelo y formato | Contexto | Prefill | Generación medida | TTFT | VRAM de proceso | Resultado |
|---|---|---|---:|---|---:|---:|---:|---|
| 2026-10-19 | TensorFold native 1.1.1, CUDA | Qwen3.5-2B MLX-4bit, group 64 | 1.024 | No registrada | 95,08 tok/s (32 tokens); 105,71 tok/s (128 tokens) | 88,2 ms; 94,1 ms | aprox. 2.388 MiB | Inferencia real en español |
| 2026-10-19 | TensorFold native 1.1.1, CUDA | Qwen3.5-4B MLX-4bit, group 64 | 512 | Latencia 190 ms y 209 ms; tok/s no registrado | 53,64 tok/s (64 tokens); 53,42 tok/s (128 tokens) | 193 ms; 212 ms | aprox. 3.120 MiB | Inferencia real en español |
| 2026-10-20 | llama.cpp CUDA, build `b11740-6fa4f6cd3` | Qwen3.5-4B GGUF Q4_K_M | 512 | 141,2 tok/s | 42,4 tok/s | No registrado | 2.808 MiB | Respuesta coherente en español; SHA-256 del GGUF verificado |
| 2026-10-20 | RustingStrata CUDA | Qwen3.5-4B GGUF Q4_K_M | contexto 1.024; pruebas PP 128/512, TG 64, 3 repeticiones | 915,3–986,5 tok/s según tamaño de prompt | decode 46,1–46,7 tok/s | No registrado | No se registró un pico comparable | Benchmark de motor separado; no es el protocolo API del 21-10 |

### Datos históricos adicionales

- TensorFold Qwen3.5-2B: generación reportada 0,326 s para 32 tokens y 1,201 s para 128 tokens; VRAM total observada 2.411 / 4.096 MiB.
- TensorFold Qwen3.5-4B: carga 6,4 s en una ejecución anterior; API local `http://127.0.0.1:18084/v1`; VRAM total observada 3.143 / 4.096 MiB.
- llama.cpp Qwen3.5-4B: SHA-256 del GGUF `c3c2cf023efdbd913c2363a14d5c7266db5e05c4602f1c0790eaed567d8aff23`.
- El intento inicial de TensorFold con presupuesto CUDA insuficiente (límite 3,4 GB y reserva de 0,5 GiB) se conserva como incidencia; una ejecución posterior de Qwen3.5-4B sí completó.

## Conclusiones

1. En Ubuntu y la RTX 3050 Laptop se ha ejecutado Qwen3.5-4B con TensorFold, llama.cpp CUDA, RustingStrata y Mistral.rs; el benchmark secuencial del 21-10 obtuvo HTTP 200 en los cuatro.
2. En el protocolo corto del 21-10, TensorFold lideró la velocidad de generación medida y la latencia de request.
3. RustingStrata queda sin tok/s comparable en ese protocolo; su benchmark de motor independiente del 20-10 sí reporta decode 46,1–46,7 tok/s bajo otra carga, y no debe mezclarse directamente con el dato de latencia API.
4. Los datos históricos no son directamente intercambiables: varían contexto, tamaño de salida, endpoint, protocolo y métricas capturadas.
5. Estas son pruebas de inferencia de cada motor, no una prueba E2E de integración con ODS, Magnitude u ODS/LEONES Runtime.

## Informes relacionados

- [Benchmark secuencial de cuatro motores — 2026-10-21](../benchmarks/qwen35-4b-four-runtimes-2026-10-21.md)
- [CSV de resultados — 2026-10-21](../benchmarks/qwen35-4b-four-runtimes-2026-10-21.csv)
- [Informe cronológico del hilo «Verificación modelo CUDA»](../reports/informe-verificacion-modelo-cuda-2026-10-21.md)
- [Inventario anterior — 2026-10-20](inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md)
- [llama.cpp: Qwen3.5-4B GGUF con RTX 3050](qwen3.5-4b-llama-cpp-rtx3050.md)
